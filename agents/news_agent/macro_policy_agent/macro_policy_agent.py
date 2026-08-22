"""Macro / Policy Agent — live RBI, budget, global, energy wires."""

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
from policy_taxonomy import classify_macro  # noqa: E402

AGENT_NAME = "macro_policy_agent"
LOG_DIR = ROOT / "logs"
DATA_DIR = ROOT / "data"

FEEDS = [
    {
        "id": "g_rbi",
        "source": "google_news",
        "label": "Google News · RBI / MPC",
        "url": "https://news.google.com/rss/search?q="
        + quote_plus("RBI repo rate MPC monetary policy India")
        + "&hl=en-IN&gl=IN&ceid=IN:en",
    },
    {
        "id": "g_budget",
        "source": "google_news",
        "label": "Google News · Budget / GST",
        "url": "https://news.google.com/rss/search?q="
        + quote_plus("India budget GST tax policy finance ministry")
        + "&hl=en-IN&gl=IN&ceid=IN:en",
    },
    {
        "id": "g_global",
        "source": "google_news",
        "label": "Google News · Fed / global",
        "url": "https://news.google.com/rss/search?q="
        + quote_plus("Federal Reserve rate cut dollar India markets")
        + "&hl=en-IN&gl=IN&ceid=IN:en",
    },
    {
        "id": "g_crude",
        "source": "google_news",
        "label": "Google News · Crude / energy",
        "url": "https://news.google.com/rss/search?q="
        + quote_plus("crude oil price India petrol diesel OPEC")
        + "&hl=en-IN&gl=IN&ceid=IN:en",
    },
    {
        "id": "et_news",
        "source": "economic_times",
        "label": "ET News",
        "url": "https://economictimes.indiatimes.com/news/rssfeeds/1715249553.cms",
    },
]


def item_id(headline: str, url: str) -> str:
    return hashlib.sha1(f"{headline}|{url}".encode("utf-8", errors="ignore")).hexdigest()[:16]


def _pull(feed: dict):
    try:
        return feed, parse_rss(fetch_text(feed["url"])), None
    except FetchError as exc:
        return feed, [], str(exc)


class MacroPolicyAgent:
    def __init__(self, on_log=None, on_item=None, on_status=None, on_action=None, on_step=None):
        self.name = AGENT_NAME
        self.status = "idle"
        self.current_action = "Standing by for policy wires."
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
                self.current_action = f"Last cycle: {len(self.items)} policy items on disk."
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

        self._set_status("fetching", "Opening RBI / budget / global wires...")
        self.log("Macro Policy Agent online. LIVE cycle.")
        self._step("init", "Load policy map", "done", "6 buckets")

        raw = []
        fails = 0
        self._step("fetch", "Fetch policy feeds", "running", "0")
        with ThreadPoolExecutor(max_workers=5) as pool:
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
                self._step("fetch", "Fetch policy feeds", "running", f"{done}/{len(FEEDS)}")

        self._step("fetch", "Fetch policy feeds", "done" if raw else "error", f"{len(raw)} raw · {fails} down")
        if not raw:
            self.last_error = "All macro sources failed."
            self._set_status("error", "No policy wire answered.")
            return []

        self._set_status("processing", f"Tagging {len(raw)} policy items...")
        self._step("classify", "Tag policy type", "running", str(len(raw)))
        for feed, row in raw:
            headline = row.get("headline") or ""
            summary = row.get("summary") or ""
            kind, score = classify_macro(headline, summary)
            if not kind:
                continue
            url = row.get("source_url") or ""
            iid = item_id(headline, url)
            if iid in seen:
                continue
            seen.add(iid)
            self.counts[kind] = self.counts.get(kind, 0) + 1
            if sum(1 for i in produced if i["sector"] == kind) >= 18:
                continue
            item = {
                "id": iid,
                "agent_name": AGENT_NAME,
                "sector": kind,
                "headline": headline,
                "summary": summary or headline,
                "source_url": url,
                "source": feed["source"],
                "published": row.get("published") or utc_now(),
                "timestamp": utc_now(),
                "status": "completed",
                "match_score": score,
            }
            produced.append(item)
            self.items.append(item)
            if self.on_item:
                self.on_item(item)

        mix = ", ".join(f"{k}={v}" for k, v in sorted(self.counts.items())) or "none"
        self._step("classify", "Tag policy type", "done", mix)
        self._step("forward", "Send to News Agent", "done", f"{len(produced)} packets")
        self.log(f"Forwarding {len(produced)} policy items ({mix}).")
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        (DATA_DIR / "last_run.json").write_text(
            json.dumps({"saved_at": utc_now(), "counts": self.counts, "items": self.items}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._set_status("done", f"Cycle complete. {len(produced)} policy items sent.")
        self.log("Cycle complete.")
        return produced


def run_once():
    return MacroPolicyAgent().run()


if __name__ == "__main__":
    print(json.dumps({"count": len(run_once())}, indent=2))
