from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sector_news_agent"))

from historical_correlation_agent import HistoricalCorrelationAgent
from tickers import companies_in_text


def test() -> None:
    assert companies_in_text("Infosys and HDFC Bank rally today")
    agent = HistoricalCorrelationAgent()
    items = agent.run()
    assert items, "No correlation notes"
    for it in items:
        assert it["agent_name"] == "historical_correlation_agent"
        assert it.get("ticker")
        assert it.get("ret_5d") is not None
    print(f"OK history items={len(items)} counts={agent.counts}")
    for it in items[:4]:
        print(f"  [{it['alignment']}] {it['headline'][:120]}")


if __name__ == "__main__":
    test()
    print("ALL HISTORY TESTS PASSED")
