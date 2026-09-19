"""CLI: python -m jev_triage triage --query ... --results results.json [--top-k 3]

results.json: [{"title": ..., "snippet": ..., "url": ...}, ...]
"""
import argparse
import json
import sys
from pathlib import Path

# Allow running straight from a fresh clone without `pip install -e .`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jev_triage import JevClient, triage  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(prog="python -m jev_triage")
    sub = ap.add_subparsers(dest="cmd", required=True)

    t = sub.add_parser("triage", help="rank search results by relevance")
    t.add_argument("--query", required=True)
    t.add_argument("--results", required=True, help="JSON file: [{title, snippet, url}]")
    t.add_argument("--top-k", type=int, default=3)
    t.add_argument("--min-confidence", type=float, default=0.0)
    t.add_argument("--mock", action="store_true", help="force mock mode")

    args = ap.parse_args()
    results = json.loads(Path(args.results).read_text())

    tr = triage(
        args.query,
        results,
        top_k=args.top_k,
        client=JevClient(mock=args.mock),
        min_confidence=args.min_confidence,
    )
    print(f"mock={tr.mock} latency={tr.latency_ms}ms est_cost=${tr.est_cost_usd}")
    for i, it in enumerate(tr.ranked, 1):
        flag = " [NEEDS REVIEW]" if it.needs_review else ""
        star = " *" if it in tr.top_k else ""
        print(f"{i}. {it.score:.2f} (conf {it.confidence}) {it.title}{star}{flag}")
        print(f"   {it.url}")


if __name__ == "__main__":
    main()
