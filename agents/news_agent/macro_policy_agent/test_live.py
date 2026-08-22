from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sector_news_agent"))

from macro_policy_agent import MacroPolicyAgent
from policy_taxonomy import classify_macro

FAKE = ("lorem", "dummy policy", "placeholder")


def test() -> None:
    kind, _ = classify_macro("RBI keeps repo rate unchanged at MPC meet", "")
    assert kind == "monetary"
    kind, _ = classify_macro("Crude oil jumps after OPEC cut", "")
    assert kind == "energy"
    agent = MacroPolicyAgent()
    items = agent.run()
    assert items, "No live macro items"
    for it in items:
        blob = f"{it['headline']} {it.get('summary','')}".lower()
        assert not any(m in blob for m in FAKE)
        assert it["agent_name"] == "macro_policy_agent"
    print(f"OK macro items={len(items)} types={agent.counts}")
    for it in items[:4]:
        print(f"  [{it['sector']}] {it['headline'][:100]}")


if __name__ == "__main__":
    test()
    print("ALL MACRO TESTS PASSED")
