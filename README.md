# jev-triage

**给 deep research agent 的"分诊台"**:一次并行 Jev 调用，给 N 条搜索结果打相关性分，让昂贵的大模型只读值得读的页面。

**Triage for deep-research agents**: score N search results in one parallel TypeSafe Jev call, so the frontier model only reads what is worth reading.

## 为什么 / Why

Deep research agent 的 loop 里，烧钱的不是"搜"，而是"读"：10 条结果全抓整页、全塞进大模型，又贵又慢。但 10 条里通常只有 3 条值得读。谁来挑？以前只能再调一次大模型来挑，贵上加贵。

Jev 是为这种"快思考"生的：10 条结果的相关性打分，**一次并行调用、70-500ms、约 $0.0001**。分诊护士（triage）就位，抢救室（大模型注意力）只接待真病人。

The expensive part of deep research is not searching, it is *reading*: fetching 10 full pages into a frontier model. Usually only 3 are worth it. Jev scores all candidates in one parallel call, so the frontier model reads the shortlist only.

## 架构 / Architecture

```
query -> [frontier: plan] -> search API -> [jev-triage: 1 call, N scored] -> top-k
      -> fetch -> [gate: page_has_answer?] -> [frontier: extract]
      -> [gate: enough_to_answer?] -> loop | [frontier: synthesize]
```

分工原则 ("快手慢脑"):Jev 负责导航（点哪条、这页有用吗、还要继续吗），大模型负责认知（规划、精读、综合）。

## 快速开始 / Quickstart

```bash
pip install -e .            # no keys needed: mock mode
pip install -e ".[jev]"     # real Jev via official typesafe-sdk
export TYPESAFE_API_KEY=... # required for real mode

python examples/quickstart.py
python tests/test_triage_mock.py
```

```python
from jev_triage import JevClient, triage

tr = triage("Jev API pricing", results, top_k=3)  # results from Tavily/Exa/Brave
for it in tr.top_k:
    print(it.score, it.confidence, it.title)
```

`examples/research_loop.py` 是一个可运行的最小 research loop 骨架（search/fetch 函数自备）。

## 先验证，再信任 / Validate first

整个项目的承重假设：**Jev 选出的 top-k ≈ 大模型选出的 top-k**。先跑评测：

```bash
python -m evals.agreement --data evals/sample_queries.jsonl --judge mock  # 无 key 烟雾测试
python -m evals.agreement --data my_queries.jsonl                        # 真实评测:需 TYPESAFE_API_KEY + judge key
```

绿灯线：top-k 重合度 >= 0.85。详见 `evals/README.md`。

## 诚实声明 / Honest notes

- Jev 处于 early access；官方的性能数字是自测数据，本项目的数字请自己跑 `evals/`。
- Mock 模式是关键词启发式，只用于管道开发，不代表真实质量。
- 本项目不解决搜索索引问题：你仍然需要 Tavily / Exa / Brave 等搜索 API。

## Roadmap

- [x] `triage()` + noul gates + agreement eval harness
- [ ] Adapter: drop-in triage for GPT Researcher / deer-flow
- [ ] Standing research: 7x24 topic watch (Jev as gatekeeper)
- [ ] Hosted triage API (paid convenience layer)
