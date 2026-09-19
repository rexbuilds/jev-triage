"""jev-triage: a Jev-powered triage layer for deep-research agents.

One parallel Jev call scores N search results / pages, so the expensive
frontier model only reads what is worth reading.
"""

from .client import Answer, ChoiceQ, JevClient, NoulQ, ScoreQ
from .triage import TriageItem, TriageResult, triage
from .gates import GateResult, enough_to_answer, page_has_answer

__all__ = [
    "Answer",
    "ChoiceQ",
    "NoulQ",
    "ScoreQ",
    "JevClient",
    "TriageItem",
    "TriageResult",
    "triage",
    "GateResult",
    "enough_to_answer",
    "page_has_answer",
]

__version__ = "0.1.0"
