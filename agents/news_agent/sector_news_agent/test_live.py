"""Live integration test. Fails if the agent serves invented headlines."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from classify import classify
from http_client import fetch_text
from rss import parse_rss
from sector_news_agent import SectorNewsAgent
from sources import google_news_url

FAKE_MARKERS = (
    "lorem ipsum",
    "dummy headline",
    "sample news",
    "placeholder",
    "scripted",
    "fake news",
    "test headline 1",
)


def test_google_news_live() -> int:
    url = google_news_url("India sugar stocks Balrampur")
    xml = fetch_text(url)
    rows = parse_rss(xml)
    assert rows, "Google News returned zero items"
    assert any(r["source_url"].startswith("http") for r in rows), "No http urls"
    print(f"OK google_news live items={len(rows)} first={rows[0]['headline'][:90]}")
    return 0


def test_classifier() -> int:
    sec, score = classify("Balrampur Chini mills raise ethanol output", "")
    assert sec == "sugar" and score > 0
    sec, score = classify("Infosys wins multi-year IT services deal", "")
    assert sec == "IT"
    sec, score = classify("Weather in Delhi today sunny", "")
    assert sec is None
    print("OK classifier")
    return 0


def test_full_agent() -> int:
    logs: list[str] = []
    agent = SectorNewsAgent(on_log=lambda e: logs.append(e["message"]))
    items = agent.run()
    assert items, f"Agent returned no live items. logs={logs[-6:]}"
    for item in items:
        blob = f"{item['headline']} {item.get('summary','')}".lower()
        assert not any(m in blob for m in FAKE_MARKERS), item["headline"]
        assert item["headline"]
        assert item["sector"] in {"sugar", "IT", "pharma", "banking", "auto"}
        assert item["source_url"].startswith("http") or item["source_url"] == ""
        assert item["agent_name"] == "sector_news_agent"
    sectors = {i["sector"] for i in items}
    print(f"OK full agent items={len(items)} sectors={sorted(sectors)} counts={agent.counts}")
    print("sample:")
    for i in items[:4]:
        print(f"  [{i['sector']}] {i['headline'][:100]}")
    return 0


if __name__ == "__main__":
    test_classifier()
    test_google_news_live()
    test_full_agent()
    print("ALL LIVE TESTS PASSED")
