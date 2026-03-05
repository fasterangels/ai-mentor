from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .base import Source

_BASE_URL = "https://api.the-odds-api.com/v4/sports/soccer/odds"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class OddsAPISource(Source):
    """Bookmaker odds provider backed by the-odds-api."""

    _PRIORITY = 40

    @property
    def name(self) -> str:
        return "odds_api"

    @property
    def priority(self) -> int:
        return self._PRIORITY

    def supports(self, kind: str) -> bool:
        return kind == "odds"

    def fetch(self, kind: str, query: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch odds for a given fixture.

        Fail-safe behaviour:
        - Missing API key -> empty odds payload
        - Network/HTTP/JSON errors -> empty odds payload
        - Missing required query fields -> empty odds payload
        """
        if kind != "odds":
            return self._empty_payload()

        api_key = os.getenv("ODDS_API_KEY") or ""
        if not api_key:
            return self._empty_payload()

        home_team = (query.get("home_team") or "").strip().lower()
        away_team = (query.get("away_team") or "").strip().lower()
        date_str = (query.get("date") or "").strip()
        if not (home_team and away_team and date_str):
            return self._empty_payload()

        try:
            raw_events = self._request(
                {
                    "apiKey": api_key,
                    "regions": "eu",
                    "markets": "h2h,totals,btts",
                    "oddsFormat": "decimal",
                }
            )
        except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError):
            return self._empty_payload()

        event = self._find_event(raw_events, home_team, away_team, date_str)
        if event is None:
            return self._empty_payload()

        odds = self._normalize_event_odds(event, home_team, away_team)
        if not odds:
            return self._empty_payload()

        data: Dict[str, Any] = {"odds": odds}
        return {
            "data": data,
            "odds": data["odds"],
            "fetched_at_utc": _now_iso(),
            "source_confidence": 0.9,
        }

    # --------------------------------------------------------------------- helpers

    def _empty_payload(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {"odds": {}}
        return {
            "data": data,
            "odds": data["odds"],
            "fetched_at_utc": _now_iso(),
            "source_confidence": 0.0,
        }

    def _request(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Low-level GET returning a list of events."""
        qs = urlencode(params)
        url = f"{_BASE_URL}?{qs}" if qs else _BASE_URL
        req = Request(url)
        req.add_header("Accept", "application/json")
        with urlopen(req, timeout=10) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            body = resp.read().decode(charset)
            data = json.loads(body)
        if isinstance(data, list):
            return data
        return []

    def _find_event(
        self,
        events: List[Dict[str, Any]],
        home_team: str,
        away_team: str,
        date_str: str,
    ) -> Dict[str, Any] | None:
        """Pick the event matching teams and date."""
        for ev in events:
            ev_home = (ev.get("home_team") or "").strip().lower()
            ev_away = (ev.get("away_team") or "").strip().lower()
            if ev_home != home_team or ev_away != away_team:
                continue
            commence = (ev.get("commence_time") or "").strip()
            try:
                # commence_time is ISO8601; compare date part.
                dt = datetime.fromisoformat(commence.replace("Z", "+00:00"))
                ev_date = dt.date().isoformat()
            except Exception:  # pragma: no cover - defensive
                ev_date = ""
            if ev_date == date_str:
                return ev
        return None

    def _normalize_event_odds(
        self,
        event: Dict[str, Any],
        home_team: str,
        away_team: str,
    ) -> Dict[str, Any]:
        """Produce normalized odds with best/average for each outcome."""
        bookmakers = event.get("bookmakers") or []
        # Collect odds per outcome across all bookmakers.
        h2h_home: List[float] = []
        h2h_draw: List[float] = []
        h2h_away: List[float] = []
        ou_over: List[float] = []
        ou_under: List[float] = []
        btts_yes: List[float] = []
        btts_no: List[float] = []

        for b in bookmakers:
            markets = b.get("markets") or []
            for m in markets:
                key = m.get("key")
                outcomes = m.get("outcomes") or []
                if key == "h2h":
                    self._collect_h2h(outcomes, home_team, away_team, h2h_home, h2h_draw, h2h_away)
                elif key == "totals":
                    self._collect_totals(outcomes, ou_over, ou_under)
                elif key == "btts":
                    self._collect_btts(outcomes, btts_yes, btts_no)

        odds: Dict[str, Any] = {}
        if h2h_home or h2h_draw or h2h_away:
            odds["1x2"] = self._best_avg_triplet(h2h_home, h2h_draw, h2h_away)
        if ou_over or ou_under:
            odds["over_under_2_5"] = self._best_avg_pair(ou_over, ou_under)
        if btts_yes or btts_no:
            odds["btts"] = self._best_avg_pair(btts_yes, btts_no, labels=("yes", "no"))
        return odds

    def _collect_h2h(
        self,
        outcomes: List[Dict[str, Any]],
        home_team: str,
        away_team: str,
        home: List[float],
        draw: List[float],
        away: List[float],
    ) -> None:
        for o in outcomes:
            name = (o.get("name") or "").strip()
            try:
                price = float(o.get("price"))
            except (TypeError, ValueError):
                continue
            lname = name.lower()
            if lname == home_team:
                home.append(price)
            elif lname == away_team:
                away.append(price)
            else:
                # Fallback: treat as draw (e.g. "Draw").
                draw.append(price)

    def _collect_totals(
        self,
        outcomes: List[Dict[str, Any]],
        over: List[float],
        under: List[float],
    ) -> None:
        """Collect odds for totals line at 2.5 goals."""
        for o in outcomes:
            try:
                line = float(o.get("point"))
            except (TypeError, ValueError):
                continue
            if abs(line - 2.5) > 1e-6:
                continue
            try:
                price = float(o.get("price"))
            except (TypeError, ValueError):
                continue
            name = (o.get("name") or "").strip().lower()
            if name.startswith("over"):
                over.append(price)
            elif name.startswith("under"):
                under.append(price)

    def _collect_btts(
        self,
        outcomes: List[Dict[str, Any]],
        yes: List[float],
        no: List[float],
    ) -> None:
        for o in outcomes:
            try:
                price = float(o.get("price"))
            except (TypeError, ValueError):
                continue
            name = (o.get("name") or "").strip().lower()
            if name in ("yes", "y"):
                yes.append(price)
            elif name in ("no", "n"):
                no.append(price)

    def _best_avg(self, values: List[float]) -> Tuple[float, float] | None:
        if not values:
            return None
        best = max(values)
        avg = sum(values) / len(values)
        return best, avg

    def _best_avg_triplet(
        self,
        home: List[float],
        draw: List[float],
        away: List[float],
    ) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        bh = self._best_avg(home)
        bd = self._best_avg(draw)
        ba = self._best_avg(away)
        if bh is not None:
            out["home"] = {"best": bh[0], "avg": bh[1]}
        if bd is not None:
            out["draw"] = {"best": bd[0], "avg": bd[1]}
        if ba is not None:
            out["away"] = {"best": ba[0], "avg": ba[1]}
        return out

    def _best_avg_pair(
        self,
        a: List[float],
        b: List[float],
        *,
        labels: Tuple[str, str] = ("over", "under"),
    ) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        ba = self._best_avg(a)
        bb = self._best_avg(b)
        if ba is not None:
            out[labels[0]] = {"best": ba[0], "avg": ba[1]}
        if bb is not None:
            out[labels[1]] = {"best": bb[0], "avg": bb[1]}
        return out

