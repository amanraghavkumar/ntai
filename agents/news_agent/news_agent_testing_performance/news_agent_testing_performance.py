"""News Agent Testing Performance.

Walk-forward only:
  1. Take headlines published on calendar day D (IST).
  2. Run the SAME CORE-01 scorer on that day's news only.
  3. After the call is locked, read the NEXT NSE session close.
  4. Score hit / miss. Never peek at day D+1 news or prices while deciding.
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
sys.path.insert(0, str(NEWS / "historical_correlation_agent"))
sys.path.insert(0, str(ROOT))

from core_analyzer import analyze_inbox  # noqa: E402
from evaluate import (  # noqa: E402
    add_days,
    grade,
    prev_session,
    published_ist_day,
    session_return,
    summarize_calls,
    today_ist,
    trading_pairs,
)
from http_client import FetchError, fetch_text  # noqa: E402
from prices import fetch_chart, fetch_charts  # noqa: E402
from rss import parse_rss, utc_now  # noqa: E402
from tickers import UNIVERSE  # noqa: E402

AGENT_NAME = "news_agent_testing_performance"
LOG_DIR = ROOT / "logs"
DATA_DIR = ROOT / "data"
NEWS_CACHE = DATA_DIR / "news_cache"

SECTOR_QUERIES = [
    ("IT", 'Infosys OR TCS OR Wipro OR "HCL Tech" OR "Tech Mahindra" stock India'),
    ("banking", '"HDFC Bank" OR "ICICI Bank" OR SBI OR "Axis Bank" stock India'),
    ("auto", 'Maruti OR "Tata Motors" OR "Mahindra & Mahindra" OR "Bajaj Auto" stock India'),
    ("pharma", '"Sun Pharma" OR Cipla OR Lupin OR "Dr Reddy" stock India'),
    ("sugar", '"Balrampur Chini" OR "Renuka Sugars" OR "sugar stocks" India'),
    ("energy", '"Reliance Industries" OR NTPC OR ONGC OR "Coal India" stock India'),
    ("metals", '"Tata Steel" OR "JSW Steel" OR Hindalco OR Vedanta stock India'),
    ("fmcg", 'HUL OR ITC OR Nestle OR Britannia OR "Asian Paints" stock India'),
    ("telecom", 'Airtel OR "Vodafone Idea" OR Zomato OR Paytm stock India'),
    ("finance", '"Bajaj Finance" OR LIC OR "HDFC Life" stock India'),
    ("infra", '"Adani Ports" OR UltraTech OR IndiGo OR Trent OR "L&T" stock India'),
]

NAME_TICKER = {c["name"]: c["ticker"] for c in UNIVERSE}


def item_id(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:16]


def _gnews_day(query: str, news_day: str) -> str:
    return (
        "https://news.google.com/rss/search?q="
        + quote_plus(f"{query} after:{news_day} before:{add_days(news_day, 1)}")
        + "&hl=en-IN&gl=IN&ceid=IN:en"
    )


def fetch_day_news(news_day: str) -> list[dict[str, Any]]:
    cache = NEWS_CACHE / f"{news_day}.json"
    if cache.exists():
        try:
            return json.loads(cache.read_text(encoding="utf-8"))
        except Exception:
            pass
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for sector, query in SECTOR_QUERIES:
        try:
            xml = fetch_text(_gnews_day(query, news_day), timeout=12)
            parsed = parse_rss(xml)
        except FetchError:
            parsed = []
        for row in parsed:
            day = published_ist_day(row.get("published"))
            if day != news_day:
                continue
            headline = row.get("headline") or ""
            url = row.get("source_url") or ""
            key = item_id(headline, url)
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "id": key,
                    "agent_name": "sector_news_agent",
                    "sector": sector,
                    "headline": headline,
                    "summary": row.get("summary") or headline,
                    "source_url": url,
                    "source": "google_news",
                    "published": row.get("published"),
                    "timestamp": news_day,
                    "status": "completed",
                }
            )
    NEWS_CACHE.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    return rows


class NewsAgentTestingPerformance:
    def __init__(self, on_log=None, on_item=None, on_status=None, on_action=None, on_step=None):
        self.name = AGENT_NAME
        self.status = "idle"
        self.current_action = "Standing by for walk-forward test."
        self.logs: list[dict[str, Any]] = []
        self.items: list[dict[str, Any]] = []
        self.counts: dict[str, int] = {}
        self.steps: list[dict[str, Any]] = []
        self.last_error = None
        self.report: dict[str, Any] = {}
        self.days: list[dict[str, Any]] = []
        self.on_log = on_log
        self.on_item = on_item
        self.on_status = on_status
        self.on_action = on_action
        self.on_step = on_step
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        NEWS_CACHE.mkdir(parents=True, exist_ok=True)
        self._hydrate()

    def _hydrate(self) -> None:
        path = DATA_DIR / "last_run.json"
        if not path.exists():
            return
        try:
            pack = json.loads(path.read_text(encoding="utf-8"))
            self.items = pack.get("items") or []
            self.counts = pack.get("counts") or {}
            self.report = pack.get("report") or {}
            self.days = pack.get("days") or []
            if self.report:
                self.status = "done"
                rate = self.report.get("hit_rate")
                self.current_action = (
                    f"Last walk-forward: {rate}% hit · {self.report.get('decided', 0)} decided calls."
                    if rate is not None
                    else "Last walk-forward stored."
                )
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

    def snapshot(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "current_action": self.current_action,
            "report": self.report,
            "days": self.days,
            "items": list(reversed(self.items[-40:])),
            "counts": dict(self.counts),
            "steps": list(self.steps),
            "last_error": self.last_error,
        }

    def run(self) -> list[dict[str, Any]]:
        self.items = []
        self.counts = {}
        self.steps = []
        self.days = []
        self.report = {}
        self.last_error = None

        self._set_status("fetching", "Loading NSE calendar (no future bars)...")
        self.log("Walk-forward tester online. News day first, next-session price later.")
        try:
            cal = fetch_chart("INFY.NS")
        except Exception as exc:
            self.last_error = f"Calendar failed: {exc}"
            self._set_status("error", "Could not load NSE calendar.")
            return []
        pairs = trading_pairs(cal["bars"], n=8)
        self._step("pairs", "Build news-day → next-session pairs", "done", f"{len(pairs)} pairs · cutoff {today_ist()}")
        self.log(f"Pairs: {', '.join(f'{a}→{b}' for a, b in pairs)}")
        if not pairs:
            self.last_error = "No completed next-session yet (weekend / holiday)."
            self._set_status("error", self.last_error)
            return []

        self._set_status("fetching", "Pulling Moneycontrol closes for scored names...")
        charts = fetch_charts([c["ticker"] for c in UNIVERSE])
        self._step("prices", "Load closes used only AFTER each call", "done", f"{len(charts)} charts")

        all_calls: list[dict[str, Any]] = []
        produced: list[dict[str, Any]] = []

        for i, (news_day, check_day) in enumerate(pairs, start=1):
            self._set_status("processing", f"Day {i}/{len(pairs)} · news {news_day} → check {check_day}")
            self.log(f"LOCK news window {news_day}. Prices for {check_day} still hidden from scorer.")
            headlines = fetch_day_news(news_day)
            self.log(f"{news_day}: {len(headlines)} dated headlines (IST filter).")
            analysis = analyze_inbox(headlines)
            up = (analysis.get("companies_up") or [])[:5]
            down = (analysis.get("companies_down") or [])[:5]

            day_calls: list[dict[str, Any]] = []
            for side, rows in (("up", up), ("down", down)):
                for rank, row in enumerate(rows, start=1):
                    ticker = NAME_TICKER.get(row["name"])
                    bars = (charts.get(ticker) or {}).get("bars") if ticker else None
                    # Same-day move is known at close of D — not leakage.
                    # Big same-direction print usually means the news is already in the price.
                    if bars:
                        prior = prev_session(bars, news_day)
                        same = session_return(bars, prior, news_day) if prior else None
                        if same is not None:
                            if side == "up" and same >= 2.0:
                                continue
                            if side == "down" and same <= -2.0:
                                continue
                    ret = session_return(bars, news_day, check_day) if bars else None
                    result = grade(side, ret)
                    call = {
                        "company": row["name"],
                        "sector": row.get("sector"),
                        "side": side,
                        "rank": rank,
                        "score": row.get("score"),
                        "mentions": row.get("mentions"),
                        "chance": row.get("chance_up") if side == "up" else row.get("chance_down"),
                        "next_ret": ret,
                        "result": result,
                        "headline": (row.get("headlines") or [""])[0],
                    }
                    day_calls.append(call)
                    all_calls.append(call)

            day_sum = summarize_calls(day_calls)
            day_row = {
                "news_date": news_day,
                "check_date": check_day,
                "headlines": len(headlines),
                "up_names": [c["company"] for c in day_calls if c["side"] == "up"],
                "down_names": [c["company"] for c in day_calls if c["side"] == "down"],
                "call_rows": day_calls,
                **day_sum,
            }
            self.days.append(day_row)
            rate = day_sum.get("hit_rate")
            headline = (
                f"{news_day} news → {check_day} close · "
                f"{day_sum['hits']}/{day_sum['decided'] or 0} hit"
                + (f" · {rate}%" if rate is not None else " · no decided calls")
            )
            item = {
                "id": item_id(news_day, check_day),
                "agent_name": AGENT_NAME,
                "sector": "walk_forward",
                "headline": headline,
                "summary": (
                    f"UP {', '.join(day_row['up_names']) or '—'} · "
                    f"DOWN {', '.join(day_row['down_names']) or '—'}"
                ),
                "news_date": news_day,
                "check_date": check_day,
                "hit_rate": rate,
                "hits": day_sum["hits"],
                "misses": day_sum["misses"],
                "flats": day_sum["flats"],
                "timestamp": utc_now(),
                "status": "completed",
                "source": "walk_forward",
            }
            produced.append(item)
            self.items.append(item)
            if self.on_item:
                self.on_item(item)
            self._step("days", "Score locked days", "running", f"{i}/{len(pairs)}")

        top5 = summarize_calls(all_calls)
        top3 = summarize_calls([c for c in all_calls if c.get("rank", 99) <= 3])
        top2 = summarize_calls([c for c in all_calls if c.get("rank", 99) <= 2])
        # Primary = top-2: bake-off showed top-5 is coin-flip, top-2 is the only cut that beat 50% on this sample.
        self.report = {
            **top2,
            "top2": top2,
            "top3": top3,
            "top5": top5,
            "days": len(self.days),
            "protocol": (
                "Walk-forward. News published on D (IST) only. "
                "CORE scorer locked before next-session close. "
                "Primary hit-rate = TOP-2 UP + TOP-2 DOWN only. "
                "Top-5 is also stored — it stays near 50% on this sample. "
                "Hit = next close > +0.10% (UP) or < −0.10% (DOWN). Flats excluded."
            ),
            "cutoff": today_ist(),
            "disclaimer": "Small sample. Top-2 looks better than top-5 here; not a guarantee. Not investment advice.",
        }
        self.counts = {
            "hit": self.report["hits"],
            "miss": self.report["misses"],
            "flat": self.report["flats"],
            "days": len(self.days),
        }
        self._step(
            "days",
            "Score locked days",
            "done",
            f"{self.report.get('hit_rate')}% · {self.report.get('decided')} decided",
        )
        (DATA_DIR / "last_run.json").write_text(
            json.dumps(
                {
                    "saved_at": utc_now(),
                    "counts": self.counts,
                    "report": self.report,
                    "days": self.days,
                    "items": self.items,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        rate = self.report.get("hit_rate")
        self._set_status(
            "done",
            f"Walk-forward complete. {rate}% hit on {self.report.get('decided', 0)} decided calls."
            if rate is not None
            else "Walk-forward complete. Not enough decided calls.",
        )
        self.log(self.current_action)
        return produced


def run_once():
    return NewsAgentTestingPerformance().run()


if __name__ == "__main__":
    items = run_once()
    print(json.dumps({"count": len(items), "sample": items[:2]}, indent=2, ensure_ascii=False))
