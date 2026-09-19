"""Noul gates for the research loop.

Two yes/no judgments that run the loop's control flow:
- page_has_answer: after fetching, is this page worth the frontier model's time?
- enough_to_answer: do the findings so far answer the query, or keep searching?

Both are single-probability (noul) calls: cheap, fast, and threshold-able.
"""
from __future__ import annotations

from dataclasses import dataclass

from .client import JevClient, NoulQ

# Keep well under Jev's ~32K context window.
MAX_STATE_CHARS = 12_000


@dataclass
class GateResult:
    probability: float
    decision: bool
    mock: bool


def _clip(text: str) -> str:
    return text if len(text) <= MAX_STATE_CHARS else text[:MAX_STATE_CHARS] + "\n…[truncated]"


def page_has_answer(
    query: str,
    page_text: str,
    client: JevClient | None = None,
    threshold: float = 0.5,
) -> GateResult:
    """Does this fetched page plausibly contain (part of) the answer?"""
    client = client or JevClient()
    state = f"Research query: {query}\n\nFetched page content:\n{_clip(page_text)}"
    answers = client.ask(
        state,
        {
            "has_answer": NoulQ(
                instructions=(
                    "The page content above contains information that helps "
                    "answer the research query (even partially)."
                ),
                mock_focus=page_text,
            )
        },
        mock_query=query,
    )
    p = float(answers["has_answer"].value)
    return GateResult(probability=p, decision=p >= threshold, mock=answers["has_answer"].mock)


def enough_to_answer(
    query: str,
    findings: str,
    client: JevClient | None = None,
    threshold: float = 0.7,
) -> GateResult:
    """Do the gathered findings suffice to answer the query? Stop or continue?"""
    client = client or JevClient()
    state = f"Research query: {query}\n\nFindings gathered so far:\n{_clip(findings)}"
    answers = client.ask(
        state,
        {
            "enough": NoulQ(
                instructions=(
                    "The findings above are sufficient to write a complete, "
                    "sourced answer to the research query. No more searching needed."
                ),
                mock_focus=findings,
            )
        },
        mock_query=query,
    )
    p = float(answers["enough"].value)
    return GateResult(probability=p, decision=p >= threshold, mock=answers["enough"].mock)
