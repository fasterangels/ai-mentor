"""
The Odds API adapter: normalize bookmakers/markets to OddsQuote (1x2 home/draw/away).
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Set

from ..models import OddsQuote


def parse_odds_response(
    json_payload: Dict[str, Any],
    allowed_bookmakers: Set[str] | None = None,
) -> List[OddsQuote]:
    """
    Parse The Odds API style payload (bookmakers with markets/outcomes) into list of OddsQuote.
    Filter market key "h2h"; map outcomes to 1x2 home/draw/away.
    If allowed_bookmakers is set, only include those bookmakers (by key or title).
    """
    out: List[OddsQuote] = []
    bookmakers = json_payload.get("bookmakers") or json_payload.get("bookmaker") or []
    if not isinstance(bookmakers, list):
        return out
    allow_set = allowed_bookmakers or set()

    for bm in bookmakers:
        if not isinstance(bm, dict):
            continue
        key = str(bm.get("key") or bm.get("title") or "")
        title = str(bm.get("title") or key or "Unknown")
        if allow_set and key not in allow_set and title not in allow_set:
            continue
        bookmaker_name = title or key
        markets = bm.get("markets") or []
        for m in markets:
            if not isinstance(m, dict):
                continue
            if str(m.get("key") or "") != "h2h":
                continue
            outcomes = m.get("outcomes") or []
            if not isinstance(outcomes, list) or len(outcomes) < 2:
                continue
            for i, oc in enumerate(outcomes[:3]):
                if not isinstance(oc, dict):
                    continue
                name = str(oc.get("name") or "").lower()
                price_val = oc.get("price")
                try:
                    price = float(price_val) if price_val is not None else 0.0
                except (TypeError, ValueError):
                    price = 0.0
                if len(outcomes) == 3:
                    outcome = ["home", "draw", "away"][i]
                elif "draw" in name:
                    outcome = "draw"
                elif i == 0:
                    outcome = "home"
                else:
                    outcome = "away"
                out.append(
                    OddsQuote(
                        bookmaker=bookmaker_name,
                        market="1x2",
                        outcome=outcome,
                        price=price,
                    )
                )
    return out


class OddsApiProvider:
    """
    Odds provider using The Odds API. Enabled when ODDS_API_KEY is set.
    """

    name: str = "the_odds_api"

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        allowed_bookmakers: str | None = None,
        timeout: int = 10,
    ) -> None:
        self.base_url = (
            (base_url or os.environ.get("ODDS_API_BASE_URL") or "https://api.the-odds-api.com/v4")
            .rstrip("/")
        )
        self.api_key = api_key or os.environ.get("ODDS_API_KEY") or ""
        self.timeout = timeout
        raw = allowed_bookmakers or os.environ.get("ODDS_ALLOWED_BOOKMAKERS") or ""
        self.allowed_bookmakers = {s.strip() for s in raw.split(",") if s.strip()} or None

    def get_odds(self, match_id: str) -> List[OddsQuote]:
        """Fetch odds for match_id. Endpoint configurable via ODDS_API_BASE_URL; on failure return []."""
        if not self.api_key:
            return []
        from urllib.request import Request, urlopen
        from urllib.parse import urlencode
        url = f"{self.base_url.rstrip('/')}/sports/soccer_epl/odds?{urlencode({'apiKey': self.api_key})}"
        req = Request(url, headers={"User-Agent": "ai-mentor-odds-api"})
        try:
            with urlopen(req, timeout=self.timeout) as resp:  # type: ignore[arg-type]
                data = json.loads(resp.read().decode("utf-8"))
        except Exception:
            return []
        if isinstance(data, list) and data:
            event = next((e for e in data if str(e.get("id")) == str(match_id)), data[0])
            return parse_odds_response(event or {}, self.allowed_bookmakers)
        if isinstance(data, dict):
            return parse_odds_response(data, self.allowed_bookmakers)
        return []
