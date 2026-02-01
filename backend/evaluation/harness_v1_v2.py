"""v1 vs v2 comparison harness — offline, no network.

BLOCK 12 — Load stored evidence packs (JSON files or list), run both analyzers,
output coverage difference, abstention reasons, decision divergences.

Usage (from backend directory):
  python -m evaluation.harness_v1_v2 [--payloads path/to/payloads.json] [--out summary.json]
  Or: payloads.json = array of { "match_id", "evidence_pack": {...} } or single object.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure backend on path when run as script
_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from analyzer.engine_v1 import analyze as analyze_v1
from analyzer.types import AnalyzerInput, AnalyzerPolicy
from analyzer.v2.engine import analyze_v2
from evaluation.evaluation_v2 import evidence_pack_from_dict
from pipeline.types import EvidencePack

# Market name normalization for comparison: v1 name -> v2 name
V1_TO_V2_MARKET = {"1X2": "1X2", "OU25": "OU_2.5", "GGNG": "BTTS"}


def _normalize_market_v2(m: str) -> str:
    return V1_TO_V2_MARKET.get(m.upper(), m)


def run_v1(evidence_pack: Optional[EvidencePack], match_id: str, markets: List[str]) -> Dict[str, Any]:
    """Run analyzer v1; return analyzer dict (status, decisions)."""
    policy = AnalyzerPolicy(min_confidence=0.62)
    inp = AnalyzerInput(
        analysis_run_id=f"run-{match_id}",
        match_id=match_id,
        mode="PREGAME",
        markets=markets,
        policy=policy,
        evidence_pack=evidence_pack,
    )
    result = analyze_v1(inp)
    decisions = [
        {"market": d.market, "decision": d.decision}
        for d in result.decisions
    ]
    return {"status": result.status, "decisions": decisions}


def run_v2(evidence_pack: Optional[EvidencePack], match_id: str, markets: List[str]) -> Dict[str, Any]:
    """Run analyzer v2 with normalized markets; return analyzer dict."""
    markets_v2 = [_normalize_market_v2(m) for m in markets]
    payload = analyze_v2("RESOLVED", evidence_pack, markets_v2, 0.62)
    decisions = [
        {"market": d.get("market"), "decision": d.get("decision")}
        for d in (payload.get("decisions") or [])
    ]
    return {"status": payload.get("status"), "decisions": decisions}


def load_payloads(path: str) -> List[Dict[str, Any]]:
    """Load payloads from JSON file: single object or array of { match_id, evidence_pack }."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    return [data]


def run_comparison(payloads: List[Dict[str, Any]], markets: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Run v1 and v2 on each payload; aggregate coverage, abstention, divergences.
    No network calls.
    """
    if not markets:
        markets = ["1X2", "OU25", "GGNG"]
    coverage_v1: Dict[str, Dict[str, int]] = defaultdict(lambda: {"PLAY": 0, "NO_BET": 0, "NO_PREDICTION": 0})
    coverage_v2: Dict[str, Dict[str, int]] = defaultdict(lambda: {"PLAY": 0, "NO_BET": 0, "NO_PREDICTION": 0})
    flags_v1: List[str] = []
    flags_v2: List[str] = []
    divergences: List[Dict[str, Any]] = []
    runs: List[Dict[str, Any]] = []

    for i, item in enumerate(payloads):
        match_id = item.get("match_id", f"match-{i}")
        ep_dict = item.get("evidence_pack")
        if ep_dict is None:
            ep = None
        else:
            ep = evidence_pack_from_dict(ep_dict)
        v1_out = run_v1(ep, match_id, markets)
        v2_out = run_v2(ep, match_id, markets)
        runs.append({"match_id": match_id, "v1_status": v1_out["status"], "v2_status": v2_out["status"]})

        # Coverage per market (v1 uses v1 names; v2 uses v2 names)
        for d in v1_out["decisions"]:
            m = d.get("market", "?")
            dec = d.get("decision", "NO_PREDICTION")
            if dec in coverage_v1[m]:
                coverage_v1[m][dec] += 1
        for d in v2_out["decisions"]:
            m = d.get("market", "?")
            dec = d.get("decision", "NO_PREDICTION")
            if dec in coverage_v2[m]:
                coverage_v2[m][dec] += 1

        # Divergence: same market, different decision (normalize market for comparison)
        v1_by_market = {_normalize_market_v2(d.get("market", "")): d.get("decision") for d in v1_out["decisions"]}
        v2_by_market = {d.get("market", ""): d.get("decision") for d in v2_out["decisions"]}
        for m in set(v1_by_market) | set(v2_by_market):
            d1 = v1_by_market.get(m)
            d2 = v2_by_market.get(m)
            if d1 != d2:
                divergences.append({"match_id": match_id, "market": m, "v1": d1, "v2": d2})

    # Top flags (from v2 we don't have per-run flags in run_v2 return; skip unless we extend)
    summary = {
        "n_payloads": len(payloads),
        "coverage_v1": dict(coverage_v1),
        "coverage_v2": dict(coverage_v2),
        "divergences": divergences,
        "divergence_count": len(divergences),
        "runs": runs,
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="v1 vs v2 analyzer comparison (offline)")
    default_payloads = _backend / "evaluation" / "fixtures" / "sample_payloads.json"
    parser.add_argument("--payloads", default=str(default_payloads), help="JSON file with evidence_pack payloads")
    parser.add_argument("--out", default=None, help="Optional output JSON path")
    parser.add_argument("--markets", default="1X2,OU25,GGNG", help="Comma-separated markets")
    args = parser.parse_args()
    path = Path(args.payloads)
    if not path.exists():
        print(f"Payloads file not found: {path}", file=sys.stderr)
        print("Create a JSON file with array of { \"match_id\": \"...\", \"evidence_pack\": { ... } }", file=sys.stderr)
        return 1
    payloads = load_payloads(str(path))
    markets = [m.strip() for m in args.markets.split(",") if m.strip()]
    summary = run_comparison(payloads, markets)
    out_str = json.dumps(summary, indent=2, default=str)
    print(out_str)
    if args.out:
        Path(args.out).write_text(out_str, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
