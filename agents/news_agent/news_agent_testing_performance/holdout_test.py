"""Out-of-sample walk-forward: earlier dates + names that were NOT in the first top-2 set."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sector_news_agent"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "historical_correlation_agent"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core_analyzer import analyze_inbox
from companies import UNIVERSE
from evaluate import grade, prev_session, session_return, summarize_calls, trading_pairs
from news_agent_testing_performance import fetch_day_news
from prices import fetch_chart, fetch_charts

# Names that dominated the FIRST 8-day top-2. Hold them out.
BANNED = {
    "Tata Motors",
    "SBI",
    "TCS",
    "Balrampur Chini",
    "Lupin",
    "Wipro",
}

NAME_T = {c["name"]: c["ticker"] for c in UNIVERSE}


def score_pairs(pairs, charts, banned=None):
    banned = banned or set()
    allc = []
    day_rows = []
    for news_day, check_day in pairs:
        headlines = fetch_day_news(news_day)
        analysis = analyze_inbox(headlines)
        up = [r for r in (analysis.get("companies_up") or []) if r["name"] not in banned][:5]
        down = [r for r in (analysis.get("companies_down") or []) if r["name"] not in banned][:5]
        day_calls = []
        for side, rows in (("up", up), ("down", down)):
            for rank, row in enumerate(rows, start=1):
                ticker = NAME_T.get(row["name"])
                bars = (charts.get(ticker) or {}).get("bars") if ticker else None
                if bars:
                    prior = prev_session(bars, news_day)
                    same = session_return(bars, prior, news_day) if prior else None
                    if same is not None:
                        if side == "up" and same >= 2.0:
                            continue
                        if side == "down" and same <= -2.0:
                            continue
                ret = session_return(bars, news_day, check_day) if bars else None
                day_calls.append(
                    {
                        "company": row["name"],
                        "side": side,
                        "rank": rank,
                        "next_ret": ret,
                        "result": grade(side, ret),
                    }
                )
        allc.extend(day_calls)
        top2 = [c for c in day_calls if c["rank"] <= 2]
        s = summarize_calls(top2)
        day_rows.append(
            {
                "news_date": news_day,
                "check_date": check_day,
                "headlines": len(headlines),
                "up": [c["company"] for c in top2 if c["side"] == "up"],
                "down": [c["company"] for c in top2 if c["side"] == "down"],
                **s,
            }
        )
        print(
            f"  {news_day}->{check_day} n={len(headlines)} top2={s.get('hit_rate')} "
            f"{s.get('hits')}/{s.get('decided')} UP={day_rows[-1]['up']} DOWN={day_rows[-1]['down']}"
        )
    return allc, day_rows


def main() -> None:
    cal = fetch_chart("INFY.NS")
    first = trading_pairs(cal["bars"], n=8, skip_last=0)
    hold = trading_pairs(cal["bars"], n=8, skip_last=8)
    print("FIRST window", first)
    print("HOLDOUT window", hold)
    tickers = [c["ticker"] for c in UNIVERSE]
    charts = fetch_charts(tickers)
    print("charts", len(charts))

    print("\n==== HOLDOUT DATES · FULL UNIVERSE ====")
    allc, _ = score_pairs(hold, charts, banned=None)
    t2 = summarize_calls([c for c in allc if c["rank"] <= 2])
    t5 = summarize_calls(allc)
    print("HOLD full top2", t2)
    print("HOLD full top5", t5)

    print("\n==== HOLDOUT DATES · BAN first-sample top2 names ====")
    allc2, _ = score_pairs(hold, charts, banned=BANNED)
    t2b = summarize_calls([c for c in allc2 if c["rank"] <= 2])
    t5b = summarize_calls(allc2)
    print("HOLD banned top2", t2b)
    print("HOLD banned top5", t5b)

    out = {
        "first_window": first,
        "holdout_window": hold,
        "banned": sorted(BANNED),
        "hold_full_top2": t2,
        "hold_full_top5": t5,
        "hold_banned_top2": t2b,
        "hold_banned_top5": t5b,
    }
    Path(__file__).resolve().parent.joinpath("data", "holdout.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8"
    )
    print("\nWROTE data/holdout.json")


if __name__ == "__main__":
    main()
