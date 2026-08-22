"""Tag macro / policy headlines."""

from __future__ import annotations

TYPES: dict[str, list[str]] = {
    "monetary": [
        "rbi", "repo rate", "mpc", "monetary policy", "interest rate",
        "liquidity", "crisil", "inflation target",
    ],
    "fiscal": [
        "budget", "fiscal", "gst", "tax", "disinvestment", "capex",
        "finance ministry", "mof",
    ],
    "trade": [
        "tariff", "import duty", "export duty", "fta", "wto", "customs",
        "trade deal",
    ],
    "energy": [
        "crude", "oil", "opec", "fuel", "petrol", "diesel", "gas price",
    ],
    "global": [
        "fed", "federal reserve", "ecb", "us jobs", "treasury",
        "dollar", "yen", "china gdp",
    ],
    "regulation": [
        "sebi", "irdai", "trai", "cci", "guideline", "circular",
    ],
}


def classify_macro(headline: str, summary: str = "") -> tuple[str | None, int]:
    blob = f"{headline} {summary}".lower()
    scores: dict[str, int] = {}
    for kind, words in TYPES.items():
        score = sum(2 if " " in w else 1 for w in words if w in blob)
        if score:
            scores[kind] = score
    if not scores:
        return None, 0
    winner = max(scores, key=scores.get)
    return winner, scores[winner]
