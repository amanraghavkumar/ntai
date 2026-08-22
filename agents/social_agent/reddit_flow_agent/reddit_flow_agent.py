"""Reddit Flow Agent — live subreddit RSS. No invented posts."""

from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
NEWS = ROOT.parents[1] / "news_agent"
sys.path.insert(0, str(NEWS))
sys.path.insert(0, str(NEWS / "sector_news_agent"))
sys.path.insert(0, str(ROOT))

from classify import classify  # noqa: E402
from companies import companies_in_text  # noqa: E402
from http_client import FetchError, fetch_text  # noqa: E402
from rss import parse_rss, utc_now  # noqa: E402

AGENT_NAME = "reddit_flow_agent"
LOG_DIR = ROOT / "logs"
DATA_DIR = ROOT / "data"

FEEDS = [
    {
        "id": "india_investments",
        "subreddit": "IndiaInvestments",
        "url": "https://www.reddit.com/r/IndiaInvestments/.rss",
    },
    {
        "id": "indian_street_bets",
        "subreddit": "IndianStreetBets",
        "url": "https://www.reddit.com/r/IndianStreetBets/.rss",
    },
    {
        "id": "indian_stock_market",
        "subreddit": "IndianStockMarket",
        "url": "https://www.reddit.com/r/IndianStockMarket/.rss",
    },
    {
        "id": "dalal_street_talks",
        "subreddit": "DalalStreetTalks",
        "url": "https://www.reddit.com/r/DalalStreetTalks/.rss",
    },
]


def item_id(headline: str, url: str) -> str:
    return hashlib.sha1(f"{headline}|{url}".encode("utf-8", errors="ignore")).hexdigest()[:16]


class RedditFlowAgent:
    def __init__(self, on_log=None, on_item=None, on_status=None, on_action=None, on_step=None):
        self.name = AGENT_NAME
        self.status = "idle"
        self.current_action = "Standing by for Reddit market buzz."
        self.logs: list[dict[str, Any]] = []
        self.items: list[dict[str, Any]] = []
        self.counts: dict[str, int] = {}
        self.steps: list[dict[str, Any]] = []
        self.last_error = None
        self.on_log = on_log
        self.on_item = on_item
        self.on_status = on_status
        self.on_action = on_action
        self.on_step = on_step
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._hydrate()

    def _hydrate(self) -> None:
        path = DATA_DIR / "last_run.json"
        if not path.exists():
            return
        try:
            pack = json.loads(path.read_text(encoding="utf-8"))
            self.items = pack.get("items") or []
            self.counts = pack.get("counts") or {}
            if self.items:
                self.status = "done"
                self.current_action = f"Last cycle: {len(self.items)} Reddit posts."
        except Exception:
            pass

    def _set_status(self, status: str, action: str | None = None) -> None:
        self.status = status
        if action:
            self.current_action = action
            if self.on_action:
                self.on_action(action)
        if self.on_status:
            self.on_status(status)

    def log(self, message: str, level: str = "info") -> None:
        entry = {
            "timestamp": utc_now(),
            "level": level,
            "agent_name": self.name,
            "message": message,
        }
        self.logs.append(entry)
        if len(self.logs) > 400:
            self.logs = self.logs[-400:]
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with (LOG_DIR / f"{day}.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        if self.on_log:
            self.on_log(entry)

    def _step(self, key: str, label: str, status: str, detail: str = "") -> None:
        row = {"key": key, "label": label, "status": status, "detail": detail, "at": utc_now()}
        existing = next((s for s in self.steps if s["key"] == key), None)
        if existing:
            existing.update(row)
        else:
            self.steps.append(row)
        if self.on_step:
            self.on_step(row)

    def run(self) -> list[dict[str, Any]]:
        self.items = []
        self.counts = {}
        self.steps = []
        self.last_error = None
        produced: list[dict[str, Any]] = []
        seen: set[str] = set()

        self._set_status("fetching", "Opening Reddit RSS (slow + spaced to avoid 429)...")
        self.log("Reddit Flow Agent online. LIVE cycle.")
        self._step("rule", "Named companies only when forwarding to News CORE", "done", "buzz desk, not a predictor")

        raw: list[tuple[dict, dict]] = []
        fails = 0
        self._step("fetch", "Fetch subreddit RSS", "running", f"0/{len(FEEDS)}")
        for i, feed in enumerate(FEEDS, start=1):
            self._set_status("fetching", f"r/{feed['subreddit']} ({i}/{len(FEEDS)})")
            try:
                xml = fetch_text(feed["url"], timeout=14, retries=1)
                rows = parse_rss(xml)
                self.log(f"r/{feed['subreddit']}: {len(rows)} live posts")
                raw.extend((feed, row) for row in rows)
            except FetchError as exc:
                fails += 1
                self.log(f"r/{feed['subreddit']} unavailable: {exc}", level="warn")
            self._step("fetch", "Fetch subreddit RSS", "running", f"{i}/{len(FEEDS)}")
            time.sleep(0.8)

        self._step("fetch", "Fetch subreddit RSS", "done" if raw else "error", f"{len(raw)} raw · {fails} down")
        if not raw:
            self.last_error = "All Reddit RSS feeds failed (429 / block)."
            self._set_status("error", self.last_error)
            return []

        named = 0
        self._set_status("processing", f"Tagging {len(raw)} posts...")
        for feed, row in raw:
            headline = row.get("headline") or ""
            summary = row.get("summary") or ""
            names = companies_in_text(f"{headline} {summary}")
            sector, _ = classify(headline, summary)
            if not sector and names:
                sector = names[0]["sector"]
            if not sector:
                sector = "social"
            url = row.get("source_url") or ""
            iid = item_id(headline, url)
            if iid in seen:
                continue
            seen.add(iid)
            self.counts[feed["subreddit"]] = self.counts.get(feed["subreddit"], 0) + 1
            if names:
                named += 1
                self.counts["named"] = self.counts.get("named", 0) + 1
            item = {
                "id": iid,
                "agent_name": AGENT_NAME,
                "sector": sector,
                "subreddit": feed["subreddit"],
                "companies": [c["name"] for c in names],
                "named": bool(names),
                "headline": headline,
                "summary": summary or headline,
                "source_url": url,
                "source": "reddit",
                "published": row.get("published") or utc_now(),
                "timestamp": utc_now(),
                "status": "completed",
                "forward_to_news": bool(names),
            }
            produced.append(item)
            self.items.append(item)
            if self.on_item:
                self.on_item(item)

        self._step("tag", "Extract listed names", "done", f"{named} named / {len(produced)} posts")
        self.log(f"Kept {len(produced)} posts, {named} name a tracked company.")
        (DATA_DIR / "last_run.json").write_text(
            json.dumps(
                {"saved_at": utc_now(), "counts": self.counts, "items": self.items},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        self._set_status("done", f"Cycle complete. {len(produced)} posts · {named} named.")
        self.log("Cycle complete.")
        return produced


def run_once():
    return RedditFlowAgent().run()


if __name__ == "__main__":
    items = run_once()
    print(json.dumps({"count": len(items), "named": sum(1 for i in items if i.get("named")), "sample": items[:2]}, indent=2, ensure_ascii=False))
