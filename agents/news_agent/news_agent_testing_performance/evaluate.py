"""Walk-forward scoring. News day D is scored only against the NEXT session."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

try:
    IST = ZoneInfo("Asia/Kolkata")
except ZoneInfoNotFoundError:
    IST = timezone(timedelta(hours=5, minutes=30), name="IST")
FLAT_PCT = 0.10


def today_ist() -> str:
    return datetime.now(IST).date().isoformat()


def add_days(iso: str, n: int) -> str:
    d = date.fromisoformat(iso)
    return (d + timedelta(days=n)).isoformat()


def published_ist_day(value: str | None) -> str | None:
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(IST).date().isoformat()
    except Exception:
        if len(value) >= 10 and value[4] == "-":
            return value[:10]
        return None


def trading_pairs(bars: list[dict], n: int = 8, skip_last: int = 0) -> list[tuple[str, str]]:
    """(news_date, check_date) where check_date already has a close and is not today."""
    days = [b["date"] for b in bars]
    cutoff = today_ist()
    pairs: list[tuple[str, str]] = []
    for i, news_day in enumerate(days[:-1]):
        check = days[i + 1]
        if check >= cutoff:
            continue
        pairs.append((news_day, check))
    if skip_last:
        pairs = pairs[:-skip_last] if skip_last < len(pairs) else []
    return pairs[-n:]


def close_on(bars: list[dict], day: str) -> float | None:
    for b in bars:
        if b["date"] == day:
            return float(b["close"])
    return None


def prev_session(bars: list[dict], day: str) -> str | None:
    prev = None
    for b in bars:
        if b["date"] >= day:
            return prev
        prev = b["date"]
    return prev


def session_return(bars: list[dict], news_day: str, check_day: str) -> float | None:
    a = close_on(bars, news_day)
    b = close_on(bars, check_day)
    if not a or not b:
        return None
    return round((b / a - 1.0) * 100.0, 2)


def grade(side: str, ret: float | None) -> str:
    if ret is None:
        return "no_price"
    if abs(ret) < FLAT_PCT:
        return "flat"
    if side == "up":
        return "hit" if ret > 0 else "miss"
    return "hit" if ret < 0 else "miss"


def summarize_calls(rows: list[dict[str, Any]]) -> dict[str, Any]:
    hits = sum(1 for r in rows if r["result"] == "hit")
    misses = sum(1 for r in rows if r["result"] == "miss")
    flats = sum(1 for r in rows if r["result"] == "flat")
    decided = hits + misses
    up = [r for r in rows if r["side"] == "up" and r["result"] in {"hit", "miss"}]
    down = [r for r in rows if r["side"] == "down" and r["result"] in {"hit", "miss"}]
    up_rets = [r["next_ret"] for r in rows if r["side"] == "up" and r.get("next_ret") is not None]
    down_rets = [r["next_ret"] for r in rows if r["side"] == "down" and r.get("next_ret") is not None]

    def rate(h: int, m: int) -> int | None:
        if h + m == 0:
            return None
        return int(round(100.0 * h / (h + m)))

    avg_up = round(sum(up_rets) / len(up_rets), 2) if up_rets else None
    avg_down = round(sum(down_rets) / len(down_rets), 2) if down_rets else None
    spread = None
    if avg_up is not None and avg_down is not None:
        spread = round(avg_up - avg_down, 2)
    return {
        "hits": hits,
        "misses": misses,
        "flats": flats,
        "calls": len(rows),
        "decided": decided,
        "hit_rate": rate(hits, misses),
        "up_hit_rate": rate(sum(1 for r in up if r["result"] == "hit"), sum(1 for r in up if r["result"] == "miss")),
        "down_hit_rate": rate(sum(1 for r in down if r["result"] == "hit"), sum(1 for r in down if r["result"] == "miss")),
        "avg_up_next_ret": avg_up,
        "avg_down_next_ret": avg_down,
        "spread": spread,
    }
