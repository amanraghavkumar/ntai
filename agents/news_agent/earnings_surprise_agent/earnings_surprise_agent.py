"""Earnings Surprise Agent.

Live results headlines only. Tags beat / miss / inline from the words
on the page. Never invents EPS or consensus numbers.
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
from surprise import classify_surprise, extract_pct  # noqa: E402

AGENT_NAME = "earnings_surprise_agent"
LOG_DIR = ROOT / "logs"
DATA_DIR = ROOT / "data"
KEEP = 60

FEEDS = [
    {
        "id": "g_results",
        "source": "google_news",
        "label": "Google News · Results",
        "url": (
            "https://news.google.com/rss/search?q="
            + quote_plus("India listed company quarterly results beats estimates OR misses estimates NSE")
            + "&hl=en-IN&gl=IN&ceid=IN:en"
        ),
    },
    {
        "id": "g_q",
        "source": "google_news",
        "label": "Google News · Q results",
        "url": (
            "https://news.google.com/rss/search?q="
            + quote_plus("Q1 OR Q2 OR Q3 OR Q4 results Infosys OR TCS OR Reliance OR HDFC Bank")
            + "&hl=en-IN&gl=IN&ceid=IN:en"
        ),
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
]


def item_id(headline: str, url: str) -> str:
    return hashlib.sha1(f"{headline}|{url}".encode("utf-8", errors="ignore")).hexdigest()[:16]


def _pull(feed: dict):
    try:
        return feed, parse_rss(fetch_text(feed["url"], timeout=14)), None
    except FetchError as exc:
        return feed, [], str(exc)


class EarningsSurpriseAgent:
    def __init__(self, on_log=None, on_item=None, on_status=None, on_action=None, on_step=None):
        self.name = AGENT_NAME
        self.status = "idle"
        self.current_action = "Standing by for live results headlines."
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
                self.current_action = f"Last cycle: {len(self.items)} earnings notes."
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

        self._set_status("fetching", "Opening live results wires...")
        self.log("Earnings Surprise Agent online. Will not invent EPS numbers.")
        self._step("rule", "Tag only stated beat/miss/inline", "done", "no guessed consensus")

        raw: list[tuple[dict, dict]] = []
        fails = 0
        self._step("fetch", "Fetch results feeds", "running", f"0/{len(FEEDS)}")
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
                self.log(f"{feed['label']}: {len(rows)} raw")
                raw.extend((feed, row) for row in rows)
                self._step("fetch", "Fetch results feeds", "running", f"{done}/{len(FEEDS)}")

        self._step("fetch", "Fetch results feeds", "done" if raw else "error", f"{len(raw)} raw · {fails} down")
        if not raw:
            self.last_error = "All earnings sources failed."
            self._set_status("error", self.last_error)
            return []

        dropped = 0
        self._set_status("processing", f"Tagging {len(raw)} headlines...")
        for feed, row in raw:
            headline = row.get("headline") or ""
            summary = row.get("summary") or ""
            surprise, strength = classify_surprise(headline, summary)
            if not surprise:
                dropped += 1
                continue
            names = companies_in_text(f"{headline} {summary}")
            if not names:
                dropped += 1
                continue
            sector, _ = classify(headline, summary)
            if not sector:
                sector = names[0]["sector"]
            url = row.get("source_url") or ""
            iid = item_id(headline, url)
            if iid in seen:
                continue
            seen.add(iid)
            self.counts[surprise] = self.counts.get(surprise, 0) + 1
            self.counts[sector] = self.counts.get(sector, 0) + 1
            if sum(1 for i in produced if i["surprise"] == surprise) >= 18:
                continue
            item = {
                "id": iid,
                "agent_name": AGENT_NAME,
                "sector": sector,
                "surprise": surprise,
                "match_score": strength,
                "pct_in_text": extract_pct(f"{headline} {summary}"),
                "company": names[0]["name"],
                "companies": [c["name"] for c in names],
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

        mix = ", ".join(
            f"{k}={v}" for k, v in sorted(self.counts.items()) if k in {"beat", "miss", "inline", "results_only"}
        )
        self._step("tag", "Tag surprise", "done", mix or "none")
        self.log(f"Kept {len(produced)} named results notes. Dropped {dropped}. {mix}")
        if not produced:
            self.last_error = "No named-company results headlines with usable language."
            self._set_status("done", self.last_error)
        else:
            self._set_status("done", f"Cycle complete. {len(produced)} earnings notes ({mix}).")
        self._step("forward", "Send to News Agent", "done", f"{len(produced)} packets")
        (DATA_DIR / "last_run.json").write_text(
            json.dumps(
                {"saved_at": utc_now(), "counts": self.counts, "items": self.items},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        self.log("Cycle complete.")
        return produced


def run_once():
    return EarningsSurpriseAgent().run()


if __name__ == "__main__":
    items = run_once()
    print(json.dumps({"count": len(items), "sample": items[:3]}, indent=2, ensure_ascii=False))
