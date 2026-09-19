"""Triage agreement eval: does Jev pick the same results as an LLM judge?

The load-bearing assumption of jev-triage. For each query:
  1. Jev scores all results in ONE parallel call  -> ranking_jev
  2. LLM-as-judge scores all results              -> ranking_llm
  3. Compare: top-k overlap, mean rank displacement, Spearman correlation.
     Also compare latency and cost.

Usage:
  python -m evals.agreement --data evals/sample_queries.jsonl --top-k 3
  python -m evals.agreement --data my_queries.jsonl --judge-model gpt-4o-mini
  python -m evals.agreement --data evals/sample_queries.jsonl --judge mock   # no keys needed

Input JSONL: {"query": str, "results": [{"title": str, "snippet": str, "url": str}]}
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from jev_triage import JevClient, triage  # noqa: E402


def spearman(a: list[int], b: list[int]) -> float:
    """Spearman rank correlation between two rank assignments."""
    n = len(a)
    if n < 2:
        return 1.0
    ma, mb = sum(a) / n, sum(b) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    da = sum((x - ma) ** 2 for x in a) ** 0.5
    db = sum((y - mb) ** 2 for y in b) ** 0.5
    return round(num / (da * db), 3) if da and db else 0.0


class MockJudge:
    """Keyword-overlap judge so the eval runs with zero keys (labeled synthetic)."""

    calls = 0
    total_latency_ms = 0.0

    def rank(self, query, results):
        import re

        qt = set(re.findall(r"[a-z0-9]+", query.lower()))
        scores = []
        for r in results:
            rt = set(re.findall(r"[a-z0-9]+", (r.get("title", "") + " " + r.get("snippet", "")).lower()))
            scores.append(100.0 * len(qt & rt) / max(1, len(qt)))
        self.calls += 1
        return scores

    def stats(self):
        return {"calls": self.calls, "model": "mock-judge (synthetic)"}


def evaluate(data_path: Path, top_k: int, judge_model: str, jev_mock: bool):
    jev = JevClient(mock=jev_mock)
    judge = MockJudge() if judge_model == "mock" else __import__("jev_triage.llm_judge", fromlist=["LLMJudge"]).LLMJudge(model=judge_model)

    rows = [json.loads(line) for line in data_path.read_text().splitlines() if line.strip()]
    per_query = []
    for row in rows:
        query, results = row["query"], row["results"]
        tr = triage(query, results, top_k=top_k, client=jev)
        jev_order = [it.id for it in tr.ranked]

        llm_scores = judge.rank(query, results)
        llm_order = [str(results[i].get("id", i)) for i in sorted(range(len(results)), key=lambda i: llm_scores[i], reverse=True)]

        k = min(top_k, len(results))
        overlap = len(set(jev_order[:k]) & set(llm_order[:k])) / k
        pos_jev = {rid: r for r, rid in enumerate(jev_order)}
        pos_llm = {rid: r for r, rid in enumerate(llm_order)}
        ids = jev_order
        displacement = sum(abs(pos_jev[i] - pos_llm[i]) for i in ids) / len(ids)
        rho = spearman([pos_jev[i] for i in ids], [pos_llm[i] for i in ids])
        per_query.append(
            {
                "query": query[:60],
                "topk_overlap": round(overlap, 3),
                "mean_rank_displacement": round(displacement, 2),
                "spearman": rho,
                "jev_latency_ms": tr.latency_ms,
                "jev_est_cost_usd": tr.est_cost_usd,
            }
        )

    n = len(per_query)
    summary = {
        "n_queries": n,
        "mean_topk_overlap": round(sum(r["topk_overlap"] for r in per_query) / n, 3),
        "mean_rank_displacement": round(sum(r["mean_rank_displacement"] for r in per_query) / n, 2),
        "mean_spearman": round(sum(r["spearman"] for r in per_query) / n, 3),
        "mean_jev_latency_ms": round(sum(r["jev_latency_ms"] for r in per_query) / n, 1),
        "total_jev_est_cost_usd": round(sum(r["jev_est_cost_usd"] for r in per_query), 6),
        "jev_mock": jev.mock,
        "judge": judge.stats(),
    }
    return summary, per_query


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="JSONL: {query, results[]}")
    ap.add_argument("--top-k", type=int, default=3)
    ap.add_argument("--judge-model", default="gpt-4o-mini",
                    help="'mock' for zero-key synthetic run, else an OpenAI-compatible model")
    ap.add_argument("--jev-mock", action="store_true", help="force Jev mock mode")
    ap.add_argument("--out", default="", help="write markdown report here")
    args = ap.parse_args()

    summary, per_query = evaluate(Path(args.data), args.top_k, args.judge_model, args.jev_mock)

    lines = ["# jev-triage agreement eval", ""]
    lines.append(f"- queries: **{summary['n_queries']}**")
    lines.append(f"- mean top-{args.top_k} overlap (Jev vs LLM judge): **{summary['mean_topk_overlap']}**")
    lines.append(f"- mean rank displacement: {summary['mean_rank_displacement']}")
    lines.append(f"- mean Spearman rho: {summary['mean_spearman']}")
    lines.append(f"- mean Jev triage latency: {summary['mean_jev_latency_ms']} ms")
    lines.append(f"- total Jev est. cost: ${summary['total_jev_est_cost_usd']}")
    lines.append(f"- jev mock mode: {summary['jev_mock']}; judge: {summary['judge']}")
    lines.append("")
    verdict = (
        "GREEN LIGHT" if summary["mean_topk_overlap"] >= 0.85
        else "YELLOW (needs prompt/state tuning)" if summary["mean_topk_overlap"] >= 0.7
        else "RED (Jev triage not matching LLM judgment)"
    )
    lines.append(f"**verdict: {verdict}** (green light bar: top-k overlap >= 0.85)")
    lines.append("")
    lines.append("| query | top-k overlap | displacement | spearman | jev ms |")
    lines.append("|---|---|---|---|---|")
    for r in per_query:
        lines.append(f"| {r['query']} | {r['topk_overlap']} | {r['mean_rank_displacement']} | {r['spearman']} | {r['jev_latency_ms']} |")
    report = "\n".join(lines)

    print(report)
    if args.out:
        Path(args.out).write_text(report)
        print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
