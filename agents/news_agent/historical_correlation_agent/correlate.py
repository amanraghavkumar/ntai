"""Match current headline tone with later price windows."""

from __future__ import annotations

from email.utils import parsedate_to_datetime
from typing import Any

POS = ("rally", "jump", "surge", "upgrade", "buy", "beat", "gain", "soar", "rise")
NEG = ("crash", "fall", "tumble", "downgrade", "miss", "drop", "slump", "plunge", "sell")


def tone(text: str) -> str:
    blob = text.lower()
    p = sum(1 for w in POS if w in blob)
    n = sum(1 for w in NEG if w in blob)
    if p > n:
        return "positive"
    if n > p:
        return "negative"
    return "neutral"


def parse_day(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).date().isoformat()
    except Exception:
        if len(value) >= 10 and value[4] == "-":
            return value[:10]
        return None


def summarize(
    company: str,
    sector: str,
    ticker: str,
    rets: dict[str, float],
    hist: list[dict[str, Any]],
    current_tone: str,
) -> dict[str, Any]:
    pos = [h["move_5d"] for h in hist if h["tone"] == "positive" and h["move_5d"] is not None]
    neg = [h["move_5d"] for h in hist if h["tone"] == "negative" and h["move_5d"] is not None]
    avg_pos = round(sum(pos) / len(pos), 2) if pos else None
    avg_neg = round(sum(neg) / len(neg), 2) if neg else None

    alignment = "mixed"
    if current_tone == "positive" and avg_pos is not None:
        alignment = "supports_up" if avg_pos > 0 else "supports_down"
    elif current_tone == "negative" and avg_neg is not None:
        alignment = "supports_down" if avg_neg < 0 else "supports_up"
    elif rets["ret_5d"] > 1.5:
        alignment = "supports_up"
    elif rets["ret_5d"] < -1.5:
        alignment = "supports_down"

    bits = [
        f"{company} ({ticker}) last {rets['last']}",
        f"1d {rets['ret_1d']}% · 5d {rets['ret_5d']}% · 20d {rets['ret_20d']}%",
    ]
    if avg_pos is not None:
        bits.append(f"after similar UP news, 5d avg {avg_pos}% (n={len(pos)})")
    if avg_neg is not None:
        bits.append(f"after similar DOWN news, 5d avg {avg_neg}% (n={len(neg)})")
    bits.append(f"current tone {current_tone} → {alignment}")

    return {
        "company": company,
        "ticker": ticker,
        "sector": sector,
        "alignment": alignment,
        "current_tone": current_tone,
        "avg_5d_after_pos": avg_pos,
        "avg_5d_after_neg": avg_neg,
        "sample_pos": len(pos),
        "sample_neg": len(neg),
        **rets,
        "headline": " · ".join(bits),
        "summary": bits[-1] if len(bits) > 1 else bits[0],
    }
