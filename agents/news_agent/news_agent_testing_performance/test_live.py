from __future__ import annotations

from evaluate import add_days, grade, summarize_calls, trading_pairs


def test() -> None:
    assert add_days("2026-08-20", 1) == "2026-08-21"
    assert grade("up", 1.2) == "hit"
    assert grade("up", -0.8) == "miss"
    assert grade("down", -0.8) == "hit"
    assert grade("down", 0.8) == "miss"
    assert grade("up", 0.02) == "flat"
    bars = [{"date": f"2026-08-{d:02d}", "close": 100 + d} for d in range(10, 22)]
    pairs = trading_pairs(bars, n=8)
    assert pairs, "need pairs"
    for news, check in pairs:
        assert news < check
    s = summarize_calls(
        [
            {"side": "up", "result": "hit", "next_ret": 1.0},
            {"side": "up", "result": "miss", "next_ret": -1.0},
            {"side": "down", "result": "hit", "next_ret": -0.5},
        ]
    )
    assert s["hits"] == 2 and s["misses"] == 1
    print("OK evaluate helpers")


if __name__ == "__main__":
    test()
    print("ALL PERF TESTS PASSED")
