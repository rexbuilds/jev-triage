# jev-triage evals

## The one experiment that matters

`triage()` is only useful if **Jev picks the same results an LLM judge would pick**.
`agreement.py` measures exactly that:

```
python -m evals.agreement --data evals/sample_queries.jsonl --judge mock   # zero keys, pipeline smoke test
python -m evals.agreement --data my_queries.jsonl                          # real Jev + real LLM judge
```

Metrics per query: **top-k overlap**, mean rank displacement, Spearman rho,
plus Jev latency and estimated cost. Verdict bar: **top-k overlap >= 0.85** = green light.

## Honest caveats

- `--judge mock` (and Jev mock mode) only validate the **pipeline**, not the
  hypothesis. Both mocks use keyword overlap, so high agreement there proves
  nothing about real Jev quality. The real test needs `TYPESAFE_API_KEY` and an
  LLM judge key.
- `sample_queries.jsonl` is **synthetic** (marked `"synthetic": true`). Build a
  real dataset from your own search API logs: 50+ queries x 10 results is enough
  for a first signal.
- The LLM judge is itself imperfect. Spot-check 10-20 disagreements by hand;
  when Jev and the judge disagree, a human decides who was right.

## Building a real dataset

1. Log queries + raw search results from your research agent (Tavily/Exa/Brave).
2. Convert to JSONL: `{"query": str, "results": [{"id","title","snippet","url"}]}`.
3. Run the eval. If green: ship it. If yellow: tune levels/instructions in
   `triage.py` (`DEFAULT_LEVELS`, question wording) and re-run.
