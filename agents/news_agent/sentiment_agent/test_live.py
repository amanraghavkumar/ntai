from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sector_news_agent"))

from scorer import score_text
from sentiment_agent import SentimentAgent

FAKE = ("lorem", "dummy sentiment", "placeholder")


def test() -> None:
    assert score_text("Infosys shares surge after upgrade", "")["sentiment"] == "positive"
    assert score_text("Wipro stock crashes on weak outlook", "")["sentiment"] == "negative"
    agent = SentimentAgent()
    items = agent.run()
    assert items, "No live sentiment items"
    for it in items:
        blob = f"{it['headline']} {it.get('summary','')}".lower()
        assert not any(m in blob for m in FAKE)
        assert it["sentiment"] in {"positive", "negative", "neutral"}
        assert it["agent_name"] == "sentiment_agent"
    print(f"OK sentiment items={len(items)} counts={agent.counts}")
    for it in items[:4]:
        print(f"  [{it['sentiment']}] {it['headline'][:100]}")


if __name__ == "__main__":
    test()
    print("ALL SENTIMENT TESTS PASSED")
