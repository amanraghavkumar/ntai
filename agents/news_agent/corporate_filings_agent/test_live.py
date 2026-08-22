"""Live test — fails if filings are invented."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sector_news_agent"))

from corporate_filings_agent import CorporateFilingsAgent
from taxonomy import classify_filing

FAKE = ("lorem", "dummy filing", "placeholder", "sample announcement")


def test() -> None:
    kind, score = classify_filing("Board meeting to consider interim dividend", "")
    assert kind == "dividend" or kind == "board_meeting"
    kind, _ = classify_filing("Promoter sold shares under SAST", "")
    assert kind == "insider_trade"
    agent = CorporateFilingsAgent()
    items = agent.run()
    assert items, "No live filings"
    for it in items:
        blob = f"{it['headline']} {it.get('summary','')}".lower()
        assert not any(m in blob for m in FAKE)
        assert it["agent_name"] == "corporate_filings_agent"
        assert it["headline"]
    print(f"OK filings items={len(items)} types={agent.counts}")
    for it in items[:4]:
        print(f"  [{it['filing_type']}] {it['headline'][:100]}")


if __name__ == "__main__":
    test()
    print("ALL FILINGS TESTS PASSED")
