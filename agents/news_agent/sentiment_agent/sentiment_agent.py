"""Sentiment Agent — live market headlines scored positive / negative / neutral."""

from __future__ import annotations

import hashlib
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "sector_news_agent"))
sys.path.insert(0, str(ROOT))

from http_client import FetchError, fetch_text  # noqa: E402
from rss import parse_rss, utc_now  # noqa: E402
from scorer import score_text  # noqa: E402

AGENT_NAME = "sentiment_agent"
LOG_DIR = ROOT / "logs"
DATA_DIR = ROOT / "data"

FEEDS = [
    {
        "id": "g_mkt",
        "source": "google_news",
        "label": "Google News · India markets",
        "url": "https://news.google.com/rss/search?q="
        + quote_plus("India stock market Sensex Nifty today")
        + "&hl=en-IN&gl=IN&ceid=IN:en",
    },
    {
        "id": "g_stocks",
        "source": "google_news",
        "label": "Google News · stocks rally crash",
        "url": "https://news.google.com/rss/search?q="
        + quote_plus("India stocks rally OR crash OR surge OR slump")
        + "&hl=en-IN&gl=IN&ceid=IN:en",
    },
    {
        "id": "et_markets",
        "source": "economic_times",
        "label": "ET Markets",
        "url": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    },
    {
        "id": "mc_latest",
        "source": "moneycontrol",
        "label": "Moneycontrol Latest",
        "url": "https://www.moneycontrol.com/rss/latestnews.xml",
    },
]


def item_id(headline: str, url: str) -> str:
    return hashlib.sha1(f"{headline}|{url}".encode("utf-8", errors="ignore")).hexdigest()[:16]


def _pull(feed: dict):
    try:
        return feed, parse_rss(fetch_text(feed["url"])), None
    except FetchError as exc:
        return feed, [], str(exc)


class SentimentAgent:
    def __init__(self, on_log=None, on_item=None, on_status=None, on_action=None, on_step=None):
        self.name = AGENT_NAME
        self.status = "idle"
        self.current_action = "Standing by to score live headlines."
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
                self.current_action = f"Last cycle: {len(self.items)} scored items on disk."
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

        self._set_status("fetching", "Pulling live market headlines to score...")
        self.log("Sentiment Agent online. LIVE cycle.")
        self._step("init", "Load sentiment lexicon", "done", "pos/neg word lists")

        raw = []
        fails = 0
        self._step("fetch", "Fetch live headlines", "running", "0")
        with ThreadPoolExecutor(max_workers=4) as pool:
            done = 0
            for fut in as_completed([pool.submit(_pull, f) for f in FEEDS]):
                feed, rows, err = fut.result()
                done += 1
                self._set_status("fetching", f"{feed['label']} ({done}/{len(FEEDS)})")
                if err:
                    fails += 1
                    self.log(f"{feed['label']} unavailable: {err}", level="warn")
                    continue
                self.log(f"{feed['label']}: {len(rows)} live items")
                raw.extend((feed, row) for row in rows)
                self._step("fetch", "Fetch live headlines", "running", f"{done}/{len(FEEDS)}")

        self._step("fetch", "Fetch live headlines", "done" if raw else "error", f"{len(raw)} raw · {fails} down")
        if not raw:
            self.last_error = "All sentiment sources failed."
            self._set_status("error", "No headline source answered.")
            return []

        self._set_status("processing", f"Scoring {len(raw)} headlines...")
        self._step("score", "Tag positive / negative / neutral", "running", str(len(raw)))
        for feed, row in raw:
            headline = row.get("headline") or ""
            summary = row.get("summary") or ""
            tone = score_text(headline, summary)
            url = row.get("source_url") or ""
            iid = item_id(headline, url)
            if iid in seen or not headline:
                continue
            seen.add(iid)
            label = tone["sentiment"]
            self.counts[label] = self.counts.get(label, 0) + 1
            if sum(1 for i in produced if i["sector"] == label) >= 30:
                continue
            item = {
                "id": iid,
                "agent_name": AGENT_NAME,
                "sector": label,
                "sentiment": label,
                "sentiment_score": tone["score"],
                "confidence": tone["confidence"],
                "pos_hits": tone["pos_hits"],
                "neg_hits": tone["neg_hits"],
                "headline": headline,
                "summary": summary or headline,
                "source_url": url,
                "source": feed["source"],
                "published": row.get("published") or utc_now(),
                "timestamp": utc_now(),
                "status": "completed",
            }
            produced.append(item)
            self.items.append(item)
            if self.on_item:
                self.on_item(item)

        mix = ", ".join(f"{k}={v}" for k, v in sorted(self.counts.items())) or "none"
        self._step("score", "Tag positive / negative / neutral", "done", mix)
        self._step("forward", "Send to News Agent", "done", f"{len(produced)} packets")
        self.log(f"Forwarding {len(produced)} scored headlines ({mix}).")
        (DATA_DIR / "last_run.json").write_text(
            json.dumps({"saved_at": utc_now(), "counts": self.counts, "items": self.items}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._set_status("done", f"Cycle complete. {len(produced)} scored items sent.")
        self.log("Cycle complete.")
        return produced


def run_once():
    return SentimentAgent().run()


if __name__ == "__main__":
    items = run_once()
    print(json.dumps({"count": len(items), "sample": items[:3]}, indent=2, ensure_ascii=False))
