"""Corporate Filings Agent — live NSE / BSE / results / insider flow."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote_plus

ROOT = Path(__file__).resolve().parent
SIBLING = ROOT.parent / "sector_news_agent"
sys.path.insert(0, str(SIBLING))
sys.path.insert(0, str(ROOT))

from http_client import FetchError, fetch_text  # noqa: E402
from rss import parse_rss, utc_now  # noqa: E402
from taxonomy import classify_filing  # noqa: E402

AGENT_NAME = "corporate_filings_agent"
LOG_DIR = ROOT / "logs"
DATA_DIR = ROOT / "data"
KEEP = 80

FEEDS = [
    {
        "id": "nse_ann",
        "source": "nse",
        "label": "NSE Online Announcements",
        "url": "https://nsearchives.nseindia.com/content/RSS/Online_announcements.xml",
    },
    {
        "id": "g_results",
        "source": "google_news",
        "label": "Google News · Results",
        "url": "https://news.google.com/rss/search?q="
        + quote_plus("India listed company quarterly results NSE BSE")
        + "&hl=en-IN&gl=IN&ceid=IN:en",
    },
    {
        "id": "g_insider",
        "source": "google_news",
        "label": "Google News · Insider / SAST",
        "url": "https://news.google.com/rss/search?q="
        + quote_plus("India insider trading SAST promoter buy sell NSE")
        + "&hl=en-IN&gl=IN&ceid=IN:en",
    },
    {
        "id": "g_board",
        "source": "google_news",
        "label": "Google News · Board / Dividend",
        "url": "https://news.google.com/rss/search?q="
        + quote_plus("NSE board meeting dividend buyback India")
        + "&hl=en-IN&gl=IN&ceid=IN:en",
    },
    {
        "id": "et_markets",
        "source": "economic_times",
        "label": "ET Markets",
        "url": "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms",
    },
]


SUBJECT_RE = re.compile(r"\|SUBJECT:\s*([^|]+)", re.I)
NAME_ONLY_RE = re.compile(r"\b(limited|ltd|plc|inc)\.?\s*$", re.I)
PREFIX_RE = re.compile(
    r"^.*?has informed the Exchange (?:about |regarding )?",
    re.I,
)


def item_id(headline: str, url: str) -> str:
    return hashlib.sha1(f"{headline}|{url}".encode("utf-8", errors="ignore")).hexdigest()[:16]


def compose_headline(title: str, summary: str) -> str:
    """NSE RSS titles are often just the company name. Lift the subject."""
    title = (title or "").strip()
    summary = (summary or "").strip()
    name_only = bool(NAME_ONLY_RE.search(title)) and len(title.split()) <= 10
    if not (name_only and summary):
        return title
    raw = SUBJECT_RE.search(summary)
    subject = (raw.group(1) if raw else summary).strip()
    subject = PREFIX_RE.sub("", subject)
    subject = re.sub(r"\s+", " ", subject).split("|")[0].strip(" .")
    if subject and subject.lower() not in title.lower():
        return f"{title} — {subject[:180]}"
    return title


def _pull(feed: dict) -> tuple[dict, list[dict], str | None]:
    try:
        xml = fetch_text(feed["url"])
        return feed, parse_rss(xml), None
    except FetchError as exc:
        return feed, [], str(exc)


class CorporateFilingsAgent:
    def __init__(
        self,
        on_log=None,
        on_item=None,
        on_status=None,
        on_action=None,
        on_step=None,
    ):
        self.name = AGENT_NAME
        self.status = "idle"
        self.current_action = "Standing by for exchange filings."
        self.logs: list[dict[str, Any]] = []
        self.items: list[dict[str, Any]] = []
        self.counts: dict[str, int] = {}
        self.steps: list[dict[str, Any]] = []
        self.last_error: str | None = None
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
                self.current_action = f"Last cycle: {len(self.items)} filings on disk."
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

        self._set_status("fetching", "Opening NSE / Google filings sockets...")
        self.log("Corporate Filings Agent online. LIVE cycle.")
        self._step("init", "Load filings taxonomy", "done", "9 types")

        raw: list[tuple[dict, dict]] = []
        fails = 0
        self._step("fetch", "Fetch exchange + news feeds", "running", f"0/{len(FEEDS)}")
        with ThreadPoolExecutor(max_workers=5) as pool:
            futs = [pool.submit(_pull, f) for f in FEEDS]
            done = 0
            for fut in as_completed(futs):
                feed, rows, err = fut.result()
                done += 1
                self._set_status("fetching", f"{feed['label']} ({done}/{len(FEEDS)})")
                if err:
                    fails += 1
                    self.log(f"{feed['label']} unavailable: {err}", level="warn")
                    continue
                self.log(f"{feed['label']}: {len(rows)} live items")
                for row in rows:
                    raw.append((feed, row))
                self._step("fetch", "Fetch exchange + news feeds", "running", f"{done}/{len(FEEDS)}")

        self._step("fetch", "Fetch exchange + news feeds", "done" if raw else "error", f"{len(raw)} raw · {fails} down")
        if not raw:
            self.last_error = "All filings sources failed."
            self._set_status("error", "No exchange feed answered.")
            return []

        self._set_status("processing", f"Tagging {len(raw)} filings...")
        self._step("classify", "Tag filing type", "running", str(len(raw)))
        for feed, row in raw:
            raw_title = row.get("headline") or ""
            summary = row.get("summary") or ""
            headline = compose_headline(raw_title, summary)
            kind, score = classify_filing(headline, summary)
            if kind == "other_disclosure" and feed["source"] != "nse":
                continue
            url = row.get("source_url") or ""
            iid = item_id(headline, url)
            if iid in seen:
                continue
            seen.add(iid)
            self.counts[kind] = self.counts.get(kind, 0) + 1
            if sum(1 for i in produced if i["filing_type"] == kind) >= 16:
                continue
            item = {
                "id": iid,
                "agent_name": AGENT_NAME,
                "sector": kind,
                "filing_type": kind,
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
        self._step("classify", "Tag filing type", "done", mix)
        self._step("forward", "Send to News Agent", "done", f"{len(produced)} packets")
        self.log(f"Forwarding {len(produced)} filings to news_agent ({mix}).")
        (DATA_DIR / "last_run.json").write_text(
            json.dumps({"saved_at": utc_now(), "counts": self.counts, "items": self.items}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._set_status("done", f"Cycle complete. {len(produced)} filings sent to News Agent.")
        self.log("Cycle complete.")
        return produced


def run_once() -> list[dict[str, Any]]:
    return CorporateFilingsAgent().run()


if __name__ == "__main__":
    items = run_once()
    print(json.dumps({"count": len(items), "sample": items[:4]}, indent=2, ensure_ascii=False))
