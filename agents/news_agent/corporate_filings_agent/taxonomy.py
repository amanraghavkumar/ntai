"""Tag exchange filings by type. Never invents a category without a keyword hit."""

from __future__ import annotations

TYPES: dict[str, list[str]] = {
    "financial_results": [
        "financial result", "quarterly result", "q1 result", "q2 result",
        "q3 result", "q4 result", "audited result", "unaudited result",
        "profit after tax", "declares earnings", "earnings conference",
        "financial results",
    ],
    "insider_trade": [
        "insider", "sast", "promoter bought", "promoter sold",
        "inter-se transfer", "pit regulation", "trading window",
    ],
    "board_meeting": [
        "board meeting", "board of directors", "consideration of",
    ],
    "dividend": [
        "dividend", "interim dividend", "final dividend", "record date",
    ],
    "merger_acquisition": [
        "merger", "amalgamation", "acquisition", "scheme of",
        "takeover", "open offer",
    ],
    "credit_rating": [
        "credit rating", "rating agency", "crisil", "icra", "care rating",
        "outlook revised",
    ],
    "shareholding": [
        "shareholding pattern", "bulk deal", "block deal", "pledge",
    ],
    "agm_egm": [
        "annual general", "extraordinary general", "agm", "egm",
        "postal ballot",
    ],
    "order_win": [
        "letter of award", "letter of intent", "order win", "contract win",
        "purchase order",
    ],
}


def classify_filing(headline: str, summary: str = "") -> tuple[str, int]:
    blob = f"{headline} {summary}".lower()
    scores: dict[str, int] = {}
    for kind, words in TYPES.items():
        score = sum(2 if " " in w else 1 for w in words if w in blob)
        if score:
            scores[kind] = score
    if not scores:
        return "other_disclosure", 0
    winner = max(scores, key=scores.get)
    return winner, scores[winner]
