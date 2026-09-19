"""LLM-as-judge baseline, used ONLY by the eval harness.

This is the thing Jev triage is measured against: the same relevance ranking
done by a frontier model. Any OpenAI-compatible endpoint works.
"""
from __future__ import annotations

import json
import os
import time

import requests


class LLMJudge:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.base_url = (base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.model = model or os.environ.get("JUDGE_MODEL", "gpt-4o-mini")
        self.calls = 0
        self.total_latency_ms = 0.0
        if not self.api_key:
            raise RuntimeError("LLMJudge needs OPENAI_API_KEY (or equivalent)")

    def rank(self, query: str, results: list[dict]) -> list[float]:
        """Return one relevance score (0-100) per result, in input order."""
        numbered = "\n".join(
            f"[{i}] {r.get('title', '')} — {r.get('snippet', '')}"
            for i, r in enumerate(results)
        )
        prompt = (
            "You are a search-result relevance judge. Score each result 0-100 for "
            f"how well it helps answer this query: {query}\n\nResults:\n{numbered}\n\n"
            'Reply with JSON only: {"scores": [<score for result 0>, ...]} '
            "in the same order, one number per result."
        )
        t0 = time.perf_counter()
        resp = requests.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
                "response_format": {"type": "json_object"},
            },
            timeout=120,
        )
        self.total_latency_ms += (time.perf_counter() - t0) * 1000
        self.calls += 1
        resp.raise_for_status()
        data = json.loads(resp.json()["choices"][0]["message"]["content"])
        scores = [float(s) for s in data["scores"]]
        if len(scores) != len(results):
            raise ValueError(f"judge returned {len(scores)} scores for {len(results)} results")
        return scores

    def stats(self) -> dict:
        return {
            "calls": self.calls,
            "total_latency_ms": round(self.total_latency_ms, 1),
            "model": self.model,
        }
