"""Headline sentiment. Lexicon only — no invented labels."""

from __future__ import annotations

POS = [
    "rally", "rallies", "jump", "jumps", "surge", "surges", "soar", "soars",
    "gain", "gains", "gained", "buy", "bullish", "upgrade", "upgrades",
    "beat", "beats", "rise", "rises", "rose", "record high", "outperform",
    "boost", "boosts", "rebound", "rebounds", "accumulate", "overweight",
    "profit", "strong", "optimistic", "recovery", "expansion",
]
NEG = [
    "crash", "crashes", "fall", "falls", "fell", "tumble", "tumbles",
    "slump", "slumps", "sell-off", "downgrade", "miss", "misses",
    "drop", "drops", "decline", "declines", "weak", "warning",
    "underperform", "bearish", "plunge", "plunges", "selloff",
    "loss", "losses", "default", "probe", "fraud", "ban",
]


def score_text(headline: str, summary: str = "") -> dict:
    blob = f" {headline} {summary} ".lower()
    pos_hits = [w for w in POS if w in blob]
    neg_hits = [w for w in NEG if w in blob]
    raw = len(pos_hits) - len(neg_hits)
    if raw > 0:
        label = "positive"
    elif raw < 0:
        label = "negative"
    else:
        label = "neutral"
    strength = abs(raw) + 0.2 * (len(pos_hits) + len(neg_hits))
    confidence = int(min(92, 40 + strength * 12))
    return {
        "sentiment": label,
        "score": raw,
        "confidence": confidence,
        "pos_hits": pos_hits[:6],
        "neg_hits": neg_hits[:6],
    }
