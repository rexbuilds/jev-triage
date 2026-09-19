"""Quickstart: triage 5 search results with one Jev call.

Runs in mock mode with no API keys. Set TYPESAFE_API_KEY for real Jev.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from jev_triage import JevClient, triage

results = [
    {"title": "TypeSafe Jev pricing", "snippet": "Jev charges $0.042 per million input tokens, output free.", "url": "https://example.com/a"},
    {"title": "TypeSafe raises $40M", "snippet": "Seed round led by DCVC for the System One model.", "url": "https://example.com/b"},
    {"title": "Sourdough starter guide", "snippet": "Feed twice daily with flour and water.", "url": "https://example.com/c"},
    {"title": "Jev API reference", "snippet": "POST /v1/systemone with state and typed questions.", "url": "https://example.com/d"},
    {"title": "Espresso ratios", "snippet": "1:2 ratio in 25-30 seconds.", "url": "https://example.com/e"},
]

client = JevClient()  # mock mode unless TYPESAFE_API_KEY is set
tr = triage("Jev API pricing per million tokens", results, top_k=2, client=client)

print(f"mock={tr.mock}  latency={tr.latency_ms}ms  est_cost=${tr.est_cost_usd}")
for it in tr.ranked:
    flag = " [NEEDS REVIEW]" if it.needs_review else ""
    print(f"  {it.score:.2f} (conf {it.confidence})  {it.title}{flag}")
