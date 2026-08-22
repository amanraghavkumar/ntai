"""Tag earnings headlines. Never invents a number that is not in the text."""

from __future__ import annotations

import re

BEAT = (
    "beats estimate",
    "beat estimate",
    "beats estimates",
    "beat estimates",
    "beats forecast",
    "topped estimate",
    "above estimate",
    "above consensus",
    "profit beat",
    "earnings beat",
    "surprises on the upside",
    "beats street",
    "beat street",
)
MISS = (
    "misses estimate",
    "miss estimate",
    "misses estimates",
    "missed estimate",
    "below estimate",
    "below consensus",
    "profit miss",
    "earnings miss",
    "misses forecast",
    "disappoints",
    "missed street",
)
INLINE = (
    "in line",
    "in-line",
    "inline with estimate",
    "matches estimate",
    "in line with estimates",
)
RESULTS = (
    "quarterly result",
    "q1 result",
    "q2 result",
    "q3 result",
    "q4 result",
    "q1fy",
    "q2fy",
    "q3fy",
    "q4fy",
    "financial result",
    "earnings",
    "net profit",
    "pat ",
    "profit after tax",
    "declares result",
    "posts profit",
    "posts loss",
)


def classify_surprise(headline: str, summary: str = "") -> tuple[str | None, int]:
    blob = f" {headline} {summary} ".lower()
    if any(w in blob for w in BEAT):
        return "beat", 3
    if any(w in blob for w in MISS):
        return "miss", 3
    if any(w in blob for w in INLINE):
        return "inline", 2
    if any(w in blob for w in RESULTS):
        # result mentioned, but no beat/miss language — do not guess
        return "results_only", 1
    return None, 0


def extract_pct(text: str) -> float | None:
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", text or "")
    if not m:
        return None
    return float(m.group(1))
