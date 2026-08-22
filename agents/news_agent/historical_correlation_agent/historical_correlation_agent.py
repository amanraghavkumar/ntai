"""Historical Correlation Agent.

For companies named in today's live news, pull NSE daily bars from
Moneycontrol and measure how the stock moved 5 days after similar
UP / DOWN headlines over the last ~6 months.
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
sys.path.insert(0, str(ROOT.parent / "sector_news_agent"))
sys.path.insert(0, str(ROOT))

from correlate import parse_day, summarize, tone  # noqa: E402
from http_client import FetchError, fetch_text  # noqa: E402
from prices import fetch_chart, fetch_charts, reaction_after, window_returns  # noqa: E402
from rss import parse_rss, utc_now  # noqa: E402
from tickers import UNIVERSE, companies_in_text  # noqa: E402

AGENT_NAME = "historical_correlation_agent"
LOG_DIR = ROOT / "logs"
DATA_DIR = ROOT / "data"
SECTOR_LAST = ROOT.parent / "sector_news_agent" / "data" / "last_run.json"


def item_id(headline: str, ticker: str) -> str:
    return hashlib.sha1(f"{headline}|{ticker}".encode()).hexdigest()[:16]


def _gnews(name: str) -> str:
    return (
        "https://news.google.com/rss/search?q="
        + quote_plus(f"{name} stock India")
        + "&hl=en-IN&gl=IN&ceid=IN:en"
    )


def _nse_quote(ticker: str) -> str:
    nse = ticker.replace(".NS", "").replace(".BO", "")
    return f"https://www.nseindia.com/get-quotes/equity?symbol={quote_plus(nse)}"


def _work(company: dict, chart: dict[str, Any] | None = None) -> dict[str, Any]:
    if chart is None:
        chart = fetch_chart(company["ticker"])
    bars = chart["bars"]
    rets = window_returns(bars)
    news_rows = []
    try:
        xml = fetch_text(_gnews(company["name"]), timeout=12)
        news_rows = parse_rss(xml)[:18]
    except FetchError:
        news_rows = []
    hist = []
    for row in news_rows:
        day = parse_day(row.get("published"))
        if not day:
            continue
        move = reaction_after(bars, day, ahead=5)
        hist.append(
            {
                "headline": row.get("headline"),
                "day": day,
                "tone": tone(row.get("headline") or ""),
                "move_5d": move,
            }
        )
    current = "neutral"
    if news_rows:
        current = tone(" ".join(r.get("headline") or "" for r in news_rows[:6]))
    note = summarize(company["name"], company["sector"], company["ticker"], rets, hist, current)
    note["source_url"] = _nse_quote(company["ticker"])
    note["sample_news"] = [h["headline"] for h in hist[:3] if h.get("headline")]
    return note


class HistoricalCorrelationAgent:
    def __init__(self, on_log=None, on_item=None, on_status=None, on_action=None, on_step=None):
        self.name = AGENT_NAME
        self.status = "idle"
        self.current_action = "Standing by to map news vs price history."
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
                self.current_action = f"Last cycle: {len(self.items)} history notes."
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

    def _focus(self) -> list[dict]:
        tally: dict[str, int] = {}
        if SECTOR_LAST.exists():
            try:
                pack = json.loads(SECTOR_LAST.read_text(encoding="utf-8"))
                for it in pack.get("items") or []:
                    blob = f"{it.get('headline', '')} {it.get('summary', '')}"
                    for c in companies_in_text(blob):
                        tally[c["name"]] = tally.get(c["name"], 0) + 1
            except Exception:
                pass
        by_name = {c["name"]: c for c in UNIVERSE}
        ranked = sorted(tally.items(), key=lambda kv: kv[1], reverse=True)
        focused = [by_name[name] for name, _ in ranked if name in by_name]
        if len(focused) < 8:
            for c in UNIVERSE:
                if c not in focused:
                    focused.append(c)
                if len(focused) >= 8:
                    break
        return focused[:8]

    def run(self) -> list[dict[str, Any]]:
        self.items = []
        self.counts = {}
        self.steps = []
        self.last_error = None
        produced: list[dict[str, Any]] = []

        self._set_status("fetching", "Selecting companies from today's live news...")
        self.log("Historical Correlation Agent online. LIVE cycle.")
        focus = self._focus()
        self._step("focus", "Pick companies in today's flow", "done", f"{len(focus)} names")
        self.log(f"Focus set: {', '.join(c['name'] for c in focus)}")

        self._set_status("fetching", "Pulling NSE prices + similar headlines...")
        self._step("prices", "Moneycontrol 6-month bars + Google News", "running", f"0/{len(focus)}")
        charts: dict[str, Any] = {}
        try:
            charts = fetch_charts([c["ticker"] for c in focus])
            self.log(f"Price source returned {len(charts)} charts.")
        except Exception as exc:
            self.log(f"Price batch failed: {exc}", level="warn")
        notes = []
        fails = 0
        with ThreadPoolExecutor(max_workers=4) as pool:
            futs = {pool.submit(_work, c, charts.get(c["ticker"])): c for c in focus}
            done = 0
            for fut in as_completed(futs):
                company = futs[fut]
                done += 1
                self._set_status("processing", f"{company['name']} ({done}/{len(focus)})")
                try:
                    notes.append(fut.result())
                    self.log(f"{company['name']}: {notes[-1]['headline'][:140]}")
                except Exception as exc:
                    fails += 1
                    self.log(f"{company['name']} failed: {exc}", level="warn")
                self._step(
                    "prices",
                    "Moneycontrol 6-month bars + Google News",
                    "running",
                    f"{done}/{len(focus)}",
                )

        self._step(
            "prices",
            "Moneycontrol 6-month bars + Google News",
            "done" if notes else "error",
            f"{len(notes)} ok · {fails} fail",
        )
        if not notes:
            self.last_error = "No price history returned."
            self._set_status("error", "Price / news windows empty.")
            return []

        self._set_status("processing", "Scoring news-vs-price alignment...")
        for note in notes:
            align = note["alignment"]
            self.counts[align] = self.counts.get(align, 0) + 1
            self.counts[note["sector"]] = self.counts.get(note["sector"], 0) + 1
            detail = note.get("headline") or ""
            short = (
                f"{note['company']}: {align.replace('_', ' ')} · last {note.get('last')}"
            )
            item = {
                "id": item_id(detail, note["ticker"]),
                "agent_name": AGENT_NAME,
                "sector": note["sector"],
                "alignment": align,
                "company": note["company"],
                "ticker": note["ticker"],
                "headline": short,
                "summary": detail,
                "source_url": note.get("source_url"),
                "source": "moneycontrol",
                "last": note.get("last"),
                "current_tone": note.get("current_tone"),
                "ret_1d": note.get("ret_1d"),
                "ret_5d": note.get("ret_5d"),
                "ret_20d": note.get("ret_20d"),
                "avg_5d_after_pos": note.get("avg_5d_after_pos"),
                "avg_5d_after_neg": note.get("avg_5d_after_neg"),
                "sample_pos": note.get("sample_pos"),
                "sample_neg": note.get("sample_neg"),
                "sample_news": note.get("sample_news") or [],
                "timestamp": utc_now(),
                "status": "completed",
            }
            produced.append(item)
            self.items.append(item)
            if self.on_item:
                self.on_item(item)

        mix = ", ".join(
            f"{k}={v}" for k, v in sorted(self.counts.items()) if k.startswith("support") or k == "mixed"
        )
        self._step("forward", "Send to News Agent", "done", mix or f"{len(produced)} notes")
        self.log(f"Forwarding {len(produced)} correlation notes ({mix}).")
        (DATA_DIR / "last_run.json").write_text(
            json.dumps(
                {"saved_at": utc_now(), "counts": self.counts, "items": self.items},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        self._set_status("done", f"Cycle complete. {len(produced)} history notes sent.")
        self.log("Cycle complete.")
        return produced


def run_once():
    return HistoricalCorrelationAgent().run()


if __name__ == "__main__":
    items = run_once()
    print(json.dumps({"count": len(items), "sample": items[:3]}, indent=2, ensure_ascii=False))
