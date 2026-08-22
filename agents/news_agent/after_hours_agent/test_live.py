from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from window import classify_window, is_unpriced

IST = ZoneInfo("Asia/Kolkata")


def test() -> None:
    now = datetime(2026, 8, 22, 18, 0, tzinfo=IST)  # Saturday
    sat = datetime(2026, 8, 22, 11, 0, tzinfo=IST)
    assert classify_window(sat, now) == "weekend"
    fri_after = datetime(2026, 8, 21, 16, 5, tzinfo=IST)
    assert classify_window(fri_after, now) == "after_close"
    fri_session = datetime(2026, 8, 21, 12, 0, tzinfo=IST)
    assert classify_window(fri_session, now) is None
    mon_pre = datetime(2026, 8, 17, 8, 40, tzinfo=IST)
    # older than 72h from Sat 22 18:00? Fri 21 is ok; Mon 17 08:40 is ~5.4 days — drop
    assert classify_window(mon_pre, now) is None
    mon_pre_fresh = datetime(2026, 8, 21, 8, 40, tzinfo=IST)
    assert classify_window(mon_pre_fresh, now) == "pre_open"
    ok, kind, _ = is_unpriced("Fri, 21 Aug 2026 11:00:00 +0530", now)
    assert ok is False and kind is None
    ok, kind, _ = is_unpriced("Fri, 21 Aug 2026 16:10:00 +0530", now)
    assert ok and kind == "after_close"
    print("OK after-hours window")


if __name__ == "__main__":
    test()
    print("ALL AFTER-HOURS TESTS PASSED")
