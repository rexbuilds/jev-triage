"""Minimal deep-research loop wired with jev-triage.

Bring your own search_fn(query) -> [{"title","snippet","url"}]
and fetch_fn(url) -> page text. The frontier model does planning,
extraction and synthesis; Jev does triage + loop control.

    query -> [frontier: plan] -> search -> [jev: triage] -> top-k
          -> fetch -> [jev gate: has_answer?] -> [frontier: extract]
          -> [jev gate: enough?] -> loop or [frontier: synthesize]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from jev_triage import JevClient, enough_to_answer, page_has_answer, triage


def research_loop(query, search_fn, fetch_fn, extract_fn, synthesize_fn,
                  max_rounds=4, top_k=3, client=None,
                  page_threshold=0.5, enough_threshold=0.7):
    client = client or JevClient()
    findings: list[str] = []

    for round_i in range(max_rounds):
        # 1. search (your search API: Tavily / Exa / Brave ...)
        results = search_fn(query)
        if not results:
            break

        # 2. JEV: triage all results in ONE parallel call
        tr = triage(query, results, top_k=top_k, client=client,
                    context="\n".join(findings[-3:]))
        print(f"[round {round_i}] triage: {len(results)} -> top-{top_k} "
              f"in {tr.latency_ms}ms (~${tr.est_cost_usd}) mock={tr.mock}")

        # 3. fetch only the shortlist; gate each page before spending frontier tokens
        for item in tr.top_k:
            if item.needs_review:
                print(f"  ! low confidence on: {item.title} -> escalate / skip")
                continue
            page = fetch_fn(item.url)
            gate = page_has_answer(query, page, client, threshold=page_threshold)
            if not gate.decision:
                print(f"  x page judged not useful (p={gate.probability:.2f}): {item.title}")
                continue
            # 4. FRONTIER: extract what matters from this page
            findings.append(extract_fn(query, page, item.url))

        # 5. JEV: enough to stop?
        done = enough_to_answer(query, "\n".join(findings), client,
                                threshold=enough_threshold)
        print(f"  enough_to_answer p={done.probability:.2f}")
        if done.decision:
            break

    # 6. FRONTIER: final synthesis from findings
    return synthesize_fn(query, findings)


if __name__ == "__main__":
    # Toy demo with canned data; wire real fns for actual research.
    demo_results = [
        {"title": "Jev pricing", "snippet": "Jev input costs $0.042 per million tokens.", "url": "u1"},
        {"title": "Sourdough guide", "snippet": "Feed starter twice daily.", "url": "u2"},
    ]
    report = research_loop(
        query="Jev API pricing",
        search_fn=lambda q: demo_results,
        fetch_fn=lambda url: "Jev charges $0.042 per million input tokens, output free." if url == "u1" else "Flour and water.",
        extract_fn=lambda q, page, url: f"[{url}] {page[:120]}",
        synthesize_fn=lambda q, findings: "SYNTHESIS:\n" + "\n".join(findings),
        page_threshold=0.1,  # mock mode is crude; relax for the toy demo
    )
    print("\n" + report)
