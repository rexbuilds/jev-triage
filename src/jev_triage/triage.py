"""Core triage: score N search results in ONE parallel Jev call.

The whole point: relevance judgments for all candidates cost one Jev call
(~70-500ms, ~$0.0001) instead of one frontier-LLM call per candidate.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .client import JevClient, ScoreQ

DEFAULT_LEVELS = [
    "Not relevant to the query",
    "Slightly related but not useful",
    "Partially answers the query",
    "Directly answers the query",
]

# Rough token estimate for cost reporting (chars / 4). Labeled as estimate.
JEV_INPUT_PER_MTOK_USD = 0.042


@dataclass
class TriageItem:
    id: str
    title: str
    url: str
    score: float  # 0 .. len(levels)-1, higher = more relevant
    confidence: float | None
    needs_review: bool = False  # confidence below threshold -> escalate
    mock: bool = False


@dataclass
class TriageResult:
    query: str
    ranked: list[TriageItem]  # best first
    top_k: list[TriageItem]
    latency_ms: float
    est_input_tokens: int
    est_cost_usd: float
    mock: bool
    client_stats: dict = field(default_factory=dict)


def triage(
    query: str,
    results: list[dict],
    top_k: int = 3,
    client: JevClient | None = None,
    levels: list[str] | None = None,
    min_confidence: float = 0.0,
    context: str = "",
) -> TriageResult:
    """Rank search results by relevance to the query.

    Args:
        query: the research question.
        results: list of {"title": ..., "snippet": ..., "url": ..., "id": ...}.
        top_k: how many to return as the shortlist.
        client: JevClient (mock mode if no API key).
        levels: ordered relevance levels, low -> high (2-10).
        min_confidence: below this, items are flagged needs_review
            ("autonomous until uncertain" escalation).
        context: optional extra state (e.g. findings gathered so far).
    """
    levels = levels or DEFAULT_LEVELS
    client = client or JevClient()
    if not results:
        return TriageResult(query, [], [], 0.0, 0, 0.0, client.mock, client.stats())

    state = f"Research query: {query}"
    if context:
        state += f"\nContext so far:\n{context}"

    questions: dict[str, ScoreQ] = {}
    for i, r in enumerate(results):
        title = r.get("title", "")
        snippet = r.get("snippet", "")
        questions[f"rel_{i}"] = ScoreQ(
            instructions=(
                "How relevant is the following search result to the research query?\n"
                f"Title: {title}\nSnippet: {snippet}\n"
                "Judge only relevance to answering the query, not general quality."
            ),
            levels=levels,
            mock_focus=f"{title} {snippet}",
        )

    import time

    t0 = time.perf_counter()
    answers = client.ask(state, questions, mock_query=query)
    latency_ms = (time.perf_counter() - t0) * 1000

    items: list[TriageItem] = []
    for i, r in enumerate(results):
        a = answers[f"rel_{i}"]
        conf = a.confidence if a.confidence is not None else 1.0
        items.append(
            TriageItem(
                id=str(r.get("id", i)),
                title=r.get("title", ""),
                url=r.get("url", ""),
                score=float(a.value),
                confidence=conf,
                needs_review=conf < min_confidence,
                mock=a.mock,
            )
        )
    items.sort(key=lambda x: x.score, reverse=True)

    est_tokens = max(1, len(state) // 4 + sum(len(q.instructions) for q in questions.values()) // 4)
    est_cost = est_tokens / 1_000_000 * JEV_INPUT_PER_MTOK_USD

    return TriageResult(
        query=query,
        ranked=items,
        top_k=items[:top_k],
        latency_ms=round(latency_ms, 1),
        est_input_tokens=est_tokens,
        est_cost_usd=round(est_cost, 6),
        mock=client.mock,
        client_stats=client.stats(),
    )
