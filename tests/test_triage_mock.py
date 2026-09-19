"""Smoke tests (mock mode, no keys needed). Run: python tests/test_triage_mock.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from jev_triage import JevClient, enough_to_answer, page_has_answer, triage


def test_triage_ranks_relevant_first():
    results = [
        {"title": "Sourdough starter", "snippet": "flour water feeding schedule", "url": "u1"},
        {"title": "Jev pricing $0.042", "snippet": "Jev API input pricing per million tokens", "url": "u2"},
        {"title": "Espresso ratios", "snippet": "1:2 in 25 seconds", "url": "u3"},
    ]
    tr = triage("Jev API pricing", results, top_k=2, client=JevClient(mock=True))
    assert tr.mock, "expected mock mode"
    assert len(tr.ranked) == 3
    assert len(tr.top_k) == 2
    assert tr.ranked[0].url == "u2", f"most relevant should win, got {tr.ranked[0].url}"
    assert tr.latency_ms >= 0
    assert tr.est_cost_usd >= 0
    print("ok: triage ranks relevant first")


def test_gates_return_probabilities():
    c = JevClient(mock=True)
    g1 = page_has_answer("Jev pricing", "Jev charges $0.042 per million tokens", c)
    g2 = page_has_answer("Jev pricing", "flour and water twice daily", c)
    assert 0 <= g1.probability <= 1 and 0 <= g2.probability <= 1
    assert g1.probability > g2.probability, "relevant page should score higher"
    g3 = enough_to_answer("Jev pricing", "Jev charges $0.042 per million tokens", c)
    assert isinstance(g3.decision, bool)
    print("ok: gates return sensible probabilities")


def test_client_stats():
    c = JevClient(mock=True)
    triage("q", [{"title": "t", "snippet": "s", "url": "u"}], client=c)
    s = c.stats()
    assert s["calls"] == 1 and s["mock"] is True
    print("ok: client stats tracked")


if __name__ == "__main__":
    test_triage_ranks_relevant_first()
    test_gates_return_probabilities()
    test_client_stats()
    print("all smoke tests passed")
