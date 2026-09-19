---
name: jev-triage
description: >
  Score N search results / pages for relevance in ONE parallel TypeSafe Jev
  call, so the expensive frontier model only reads what is worth reading.
  Use when a research agent must pick which links to fetch, whether a fetched
  page is useful, or whether gathered findings are enough to stop searching.
---

# jev-triage

Triage = 急诊分诊: decide who gets into the ER (frontier model attention)
and who goes home. One Jev call judges all candidates in parallel.

## Install

```bash
pip install -e .            # mock mode works with no keys
pip install -e ".[jev]"     # real Jev via official typesafe-sdk
export TYPESAFE_API_KEY=... # required for real mode
```

## API

```python
from jev_triage import JevClient, triage, page_has_answer, enough_to_answer

client = JevClient()  # mock unless TYPESAFE_API_KEY is set

# 1. Triage: N results -> ranked shortlist, ONE Jev call
tr = triage(
    query="Jev API pricing",
    results=[{"title": ..., "snippet": ..., "url": ...}],  # from Tavily/Exa/Brave
    top_k=3,
    client=client,
    min_confidence=0.6,   # below this -> item.needs_review (escalate, don't silently drop)
    context="...",        # optional: findings gathered so far
)
for it in tr.top_k:
    print(it.score, it.confidence, it.title, it.url)

# 2. Gate a fetched page before spending frontier tokens on it
gate = page_has_answer(query, page_text, client, threshold=0.5)
if not gate.decision:
    continue  # skip extraction

# 3. Loop control: stop searching when findings suffice
done = enough_to_answer(query, "\n".join(findings), client, threshold=0.7)
```

## The research-loop pattern

```
query -> [frontier: plan] -> search API -> [jev-triage: 1 call, N scored] -> top-k
      -> fetch -> [gate: has_answer?] -> [frontier: extract]
      -> [gate: enough?] -> loop | [frontier: synthesize]
```

Jev owns **navigation** (which link, is this page useful, keep going?).
The frontier model owns **cognition** (planning, extraction, synthesis).
See `examples/research_loop.py` for a runnable skeleton.

## Division of labor (the "快手慢脑" rule)

| Jev (hands, fast) | Frontier model (brain, slow) |
|---|---|
| score / rank candidates | write queries, plans |
| has_answer? / enough? gates | read pages, extract, synthesize |
| ~70-500ms, ~$0.0001/call | seconds, ~$0.01+/call |

If a step needs a calibrated yes/no, a ranking, or a loop decision -> Jev.
If it needs prose, judgment over long context, or creativity -> frontier model.

## Validate before you trust

`triage()` is only useful if Jev's picks match an LLM judge's picks.
Run the agreement eval before production use:

```bash
python -m evals.agreement --data evals/sample_queries.jsonl --judge mock  # smoke test, no keys
python -m evals.agreement --data my_queries.jsonl                        # real: needs TYPESAFE_API_KEY + judge key
```

Green-light bar: top-k overlap >= 0.85. See `evals/README.md`.
