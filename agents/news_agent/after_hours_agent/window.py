"""Honest unpriced window. Regular 09:15–15:30 IST tape is rejected."""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

try:
    IST = ZoneInfo("Asia/Kolkata")
except ZoneInfoNotFoundError:
    IST = timezone(timedelta(hours=5, minutes=30), name="IST")
OPEN = time(9, 15)
CLOSE = time(15, 30)
MAX_AGE = timedelta(hours=72)


def parse_ist(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(IST)
    except Exception:
        return None


def classify_window(dt: datetime, now: datetime | None = None) -> str | None:
    """Return weekend / after_close / pre_open, else None (priced session)."""
    now = now or datetime.now(IST)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)
    dt = dt.astimezone(IST)
    if now - dt > MAX_AGE:
        return None
    if now < dt:
        return None
    wd = dt.weekday()
    clock = dt.time()
    if wd >= 5:
        return "weekend"
    if clock >= CLOSE:
        return "after_close"
    if clock < OPEN:
        return "pre_open"
    return None


def is_unpriced(published: str | None, now: datetime | None = None) -> tuple[bool, str | None, str | None]:
    dt = parse_ist(published)
    if not dt:
        return False, None, None
    kind = classify_window(dt, now)
    return kind is not None, kind, dt.isoformat()
