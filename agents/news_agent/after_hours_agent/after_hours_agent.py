"""After-Hours / Weekend Agent.

Only headlines that could not have been traded yet:
  - weekday published at/after 15:30 IST
  - Saturday / Sunday any time
  - weekday before 09:15 IST (pre-open)
Session tape (09:15–15:30) is dropped. No pubDate → dropped.
"""

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
NEWS = ROOT.parent
sys.path.insert(0, str(NEWS))
sys.path.insert(0, str(NEWS / "sector_news_agent"))
sys.path.insert(0, str(ROOT))

from classify import classify  # noqa: E402
from companies import companies_in_text  # noqa: E402
from http_client import FetchError, fetch_text  # noqa: E402
from rss import parse_rss, utc_now  # noqa: E402
from window import is_unpriced  # noqa: E402

AGENT_NAME = "after_hours_agent"
LOG_DIR = ROOT / "logs"
DATA_DIR = ROOT / "data"
KEEP = 80

FEEDS = [
    {
        "id": "et_markets",
        "source": "economic_times",
        "label": "ET Markets",
        "url": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    },
    {
        "id": "et_stocks",
        "source": "economic_times",
        "label": "ET Stocks",
        "url": "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms",
    },
    {
        "id": "mc_latest",
        "source": "moneycontrol",
        "label": "Moneycontrol Latest",
        "url": "https://www.moneycontrol.com/rss/latestnews.xml",
    },
    {
        "id": "mc_biz",
        "source": "moneycontrol",
        "label": "Moneycontrol Business",
        "url": "https://www.moneycontrol.com/rss/business.xml",
    },
    {
        "id": "g_after",
        "source": "google_news",
        "label": "Google News · after-hours India",
        "url": (
            "https://news.google.com/rss/search?q="
            + quote_plus("India stock market today after hours OR weekend OR Monday")
            + "&hl=en-IN&gl=IN&ceid=IN:en"
        ),
    },
    {
        "id": "g_stocks",
        "source": "google_news",
        "label": "Google News · India stocks",
        "url": (
            "https://news.google.com/rss/search?q="
            + quote_plus("India stocks NSE BSE listed company")
            + "&hl=en-IN&gl=IN&ceid=IN:en"
        ),
    },
]


def item_id(headline: str, url: str) -> str:
    return hashlib.sha1(f"{headline}|{url}".encode("utf-8", errors="ignore")).hexdigest()[:16]


def _pull(feed: dict):
    try:
        return feed, parse_rss(fetch_text(feed["url"], timeout=14)), None
    except FetchError as exc:
        return feed, [], str(exc)


class AfterHoursAgent:
    def __init__(self, on_log=None, on_item=None, on_status=None, on_action=None, on_step=None):
        self.name = AGENT_NAME
        self.status = "idle"
        self.current_action = "Standing by for unpriced (after-close / weekend) tape."
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
                self.current_action = f"Last cycle: {len(self.items)} unpriced headlines."
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

        self._set_status("fetching", "Pulling wires, then keeping only unpriced timestamps...")
        self.log("After-Hours Agent online. Session tape will be dropped.")
        self._step("rule", "Unpriced window", "done", "Sat/Sun · after 15:30 IST · before 09:15 IST · 72h")

        raw: list[tuple[dict, dict]] = []
        fails = 0
        self._step("fetch", "Fetch live feeds", "running", f"0/{len(FEEDS)}")
        with ThreadPoolExecutor(max_workers=6) as pool:
            done = 0
            for fut in as_completed([pool.submit(_pull, f) for f in FEEDS]):
                feed, rows, err = fut.result()
                done += 1
                self._set_status("fetching", f"{feed['label']} ({done}/{len(FEEDS)})")
                if err:
                    fails += 1
                    self.log(f"{feed['label']} unavailable: {err}", level="warn")
                    continue
                self.log(f"{feed['label']}: {len(rows)} raw")
                raw.extend((feed, row) for row in rows)
                self._step("fetch", "Fetch live feeds", "running", f"{done}/{len(FEEDS)}")

        self._step("fetch", "Fetch live feeds", "done" if raw else "error", f"{len(raw)} raw · {fails} down")
        if not raw:
            self.last_error = "All after-hours sources failed."
            self._set_status("error", self.last_error)
            return []

        dropped_session = 0
        dropped_nodate = 0
        dropped_noname = 0
        self._set_status("processing", f"Filtering {len(raw)} rows for unpriced window...")
        for feed, row in raw:
            headline = row.get("headline") or ""
            summary = row.get("summary") or ""
            published = row.get("published")
            ok, kind, published_ist = is_unpriced(published)
            if not published:
                dropped_nodate += 1
                continue
            if not ok:
                dropped_session += 1
                continue
            names = companies_in_text(f"{headline} {summary}")
            if not names:
                dropped_noname += 1
                continue
            sector, _ = classify(headline, summary)
            if not sector:
                sector = names[0]["sector"]
            url = row.get("source_url") or ""
            iid = item_id(headline, url)
            if iid in seen:
                continue
            seen.add(iid)
            self.counts[kind or "unpriced"] = self.counts.get(kind or "unpriced", 0) + 1
            self.counts[sector] = self.counts.get(sector, 0) + 1
            if len(produced) >= KEEP:
                continue
            item = {
                "id": iid,
                "agent_name": AGENT_NAME,
                "sector": sector,
                "window": kind,
                "unpriced": True,
                "companies": [c["name"] for c in names],
                "headline": headline,
                "summary": summary or headline,
                "source_url": url,
                "source": feed["source"],
                "published": published,
                "published_ist": published_ist,
                "timestamp": utc_now(),
                "status": "completed",
            }
            produced.append(item)
            self.items.append(item)
            if self.on_item:
                self.on_item(item)

        self._step(
            "filter",
            "Keep unpriced only",
            "done",
            f"kept {len(produced)} · session {dropped_session} · no-date {dropped_nodate} · no-name {dropped_noname}",
        )
        self.log(
            f"Kept {len(produced)} unpriced. Dropped session={dropped_session} "
            f"no-date={dropped_nodate} no-named-company={dropped_noname}."
        )
        if not produced:
            self.last_error = "No unpriced named-company headlines in the last 72h."
            self._set_status("done", self.last_error)
            (DATA_DIR / "last_run.json").write_text(
                json.dumps({"saved_at": utc_now(), "counts": self.counts, "items": []}, indent=2),
                encoding="utf-8",
            )
            return []

        mix = ", ".join(f"{k}={v}" for k, v in sorted(self.counts.items()) if k in {"weekend", "after_close", "pre_open"})
        self._step("forward", "Send to News Agent", "done", mix or f"{len(produced)} packets")
        self.log(f"Forwarding {len(produced)} unpriced packets ({mix}).")
        (DATA_DIR / "last_run.json").write_text(
            json.dumps(
                {"saved_at": utc_now(), "counts": self.counts, "items": self.items},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        self._set_status("done", f"Cycle complete. {len(produced)} unpriced headlines sent.")
        self.log("Cycle complete.")
        return produced


def run_once():
    return AfterHoursAgent().run()


if __name__ == "__main__":
    items = run_once()
    print(json.dumps({"count": len(items), "sample": items[:3]}, indent=2, ensure_ascii=False))
