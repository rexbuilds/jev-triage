"""TypeSafe Jev client with a mock fallback.

Real mode: uses the official ``typesafe_sdk`` (``pip install jev-triage[jev]``),
reads ``TYPESAFE_API_KEY`` / ``TYPESAFE_MODEL`` from the environment.

Mock mode: keyword-overlap heuristic, every answer flagged ``mock=True``.
The whole pipeline (and the eval harness) runs end-to-end with no key,
so you can develop the orchestration before / without API access.
"""
from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field

_WORD = re.compile(r"[a-z0-9]+")


@dataclass
class ScoreQ:
    instructions: str
    levels: list[str]  # 2-10 ordered levels, low -> high
    mock_focus: str = ""  # mock mode only: text being judged; ignored by real Jev


@dataclass
class NoulQ:
    instructions: str
    mock_focus: str = ""


@dataclass
class ChoiceQ:
    instructions: str
    options: dict[str, str]  # key -> description; include an "other" option
    mock_focus: str = ""


@dataclass
class Answer:
    kind: str  # "score" | "noul" | "choice"
    value: float | str
    probabilities: dict = field(default_factory=dict)
    confidence: float | None = None
    mock: bool = False


def _tokens(text: str) -> set[str]:
    return set(_WORD.findall(text.lower()))


class JevClient:
    """Thin wrapper over the Jev System One API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        mock: bool = False,
    ) -> None:
        self.api_key = api_key or os.environ.get("TYPESAFE_API_KEY")
        self.model = model or os.environ.get("TYPESAFE_MODEL", "jev-latest")
        self.mock = mock or not self.api_key
        self.calls = 0
        self.total_latency_ms = 0.0
        self._sdk_client = None

        if not self.mock:
            try:
                from typesafe_sdk import TypeSafeClient  # type: ignore

                try:
                    self._sdk_client = TypeSafeClient(api_key=self.api_key)
                except TypeError:
                    self._sdk_client = TypeSafeClient()
            except ImportError:
                print(
                    "[jev-triage] typesafe_sdk not installed "
                    "(pip install jev-triage[jev]); falling back to mock mode."
                )
                self.mock = True

    # ------------------------------------------------------------------ API
    def ask(
        self,
        state: str,
        questions: dict[str, ScoreQ | NoulQ | ChoiceQ],
        mock_query: str = "",
    ) -> dict[str, Answer]:
        """Ask all questions about the same state in ONE parallel Jev call.

        mock_query: mock mode only. Relevance is measured against this text
        (usually the research query) instead of the whole state, because the
        judged text itself often lives inside the state.
        """
        t0 = time.perf_counter()
        if self.mock:
            answers = self._mock_ask(state, questions, mock_query)
        else:
            answers = self._real_ask(state, questions)
        dt_ms = (time.perf_counter() - t0) * 1000
        self.calls += 1
        self.total_latency_ms += dt_ms
        return answers

    def stats(self) -> dict:
        return {
            "calls": self.calls,
            "total_latency_ms": round(self.total_latency_ms, 1),
            "avg_latency_ms": round(self.total_latency_ms / max(1, self.calls), 1),
            "mock": self.mock,
            "model": self.model,
        }

    # ------------------------------------------------------------- real mode
    def _real_ask(self, state, questions) -> dict[str, Answer]:
        from typesafe_sdk import Choice, Noul, Score  # type: ignore

        sdk_questions = {}
        kinds = {}
        for name, q in questions.items():
            if isinstance(q, ScoreQ):
                sdk_questions[name] = Score(
                    instructions=q.instructions, criteria=q.levels
                )
                kinds[name] = "score"
            elif isinstance(q, NoulQ):
                sdk_questions[name] = Noul(instructions=q.instructions)
                kinds[name] = "noul"
            elif isinstance(q, ChoiceQ):
                sdk_questions[name] = Choice(
                    instructions=q.instructions, criteria=q.options
                )
                kinds[name] = "choice"
            else:
                raise TypeError(f"unknown question type: {type(q)}")

        resp = self._sdk_client.system_one(
            state=state, questions=sdk_questions, model=self.model
        )
        out: dict[str, Answer] = {}
        for name, kind in kinds.items():
            a = resp.answers[name]
            if kind == "score":
                out[name] = Answer(
                    kind="score",
                    value=float(a.score),
                    probabilities=dict(a.probabilities),
                    confidence=float(a.confidence),
                )
            elif kind == "noul":
                out[name] = Answer(kind="noul", value=float(a.noul))
            else:
                out[name] = Answer(
                    kind="choice",
                    value=str(a.choice),
                    probabilities=dict(a.probabilities),
                    confidence=float(a.confidence),
                )
        return out

    # ------------------------------------------------------------- mock mode
    def _mock_ask(self, state, questions, mock_query="") -> dict[str, Answer]:
        """Heuristic stand-in. Clearly labeled; for pipeline dev only."""
        ref_toks = _tokens(mock_query) if mock_query else _tokens(state)
        out: dict[str, Answer] = {}
        for name, q in questions.items():
            focus = _tokens(q.mock_focus) if q.mock_focus else _tokens(q.instructions)
            # overlap between the judged text and the reference (query),
            # crude but enough to exercise ranking / gating logic.
            overlap = len(ref_toks & focus) / max(1, len(focus))
            if isinstance(q, ScoreQ):
                n = len(q.levels)
                value = round(overlap * (n - 1), 3)
                probs = {lvl: 0.0 for lvl in q.levels}
                probs[q.levels[min(n - 1, int(round(value)))]] = 1.0
                out[name] = Answer(
                    kind="score",
                    value=value,
                    probabilities=probs,
                    confidence=round(0.5 + overlap * 0.5, 3),
                    mock=True,
                )
            elif isinstance(q, NoulQ):
                out[name] = Answer(
                    kind="noul", value=round(min(1.0, overlap * 1.5), 3), mock=True
                )
            else:
                keys = list(q.options)
                pick = keys[0] if overlap > 0.1 else keys[-1]
                out[name] = Answer(
                    kind="choice",
                    value=pick,
                    probabilities={k: (1.0 if k == pick else 0.0) for k in keys},
                    confidence=round(0.5 + overlap * 0.5, 3),
                    mock=True,
                )
        return out
