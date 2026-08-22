"""CORE-01 analyzer.

Reads packets already collected by satellite agents and scores
company / sector news-flow. Never invents companies that were not
mentioned in live headlines.
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from companies import BLOCK, COMPANIES

UP = [
    "rally", "rallies", "jump", "jumps", "surge", "surges", "soar", "soars",
    "gain", "gains", "gained", "buy", "bullish", "upgrade", "upgrades",
    "beat", "beats", "rise", "rises", "rose", "record high", "hits high",
    "outperform", "boost", "boosts", "rebound", "rebounds",
    "accumulate", "overweight",
]
DOWN = [
    "crash", "crashes", "fall", "falls", "fell", "tumble", "tumbles",
    "slump", "slumps", "sell-off", "downgrade", "misses",
    "drop", "drops", "decline", "declines", "warning", "cut target",
    "underperform", "bearish", "plunge", "plunges", "selloff",
]

FORWARD = [
    "will", "to raise", "to consider", "board meeting", "upgrade",
    "target of", "outlook", "from september", "from next", "plans to",
    "set to", "likely to", "may raise", "to announce",
]
BACKWARD = [
    "today", "yesterday", "this week", "on friday", "on thursday",
    "on wednesday", "closed", "ended", "already", "after the bell",
    "session", "intraday",
]
ROUNDUP = [
    "stocks to watch", "top gainers", "top losers", "market wrap",
    "stocks to buy", "what to watch", "gainers and losers",
]

MIN_ABS_SCORE = 1.5
MIN_MENTIONS = 2


def _blob(item: dict[str, Any]) -> str:
    return f" {item.get('headline','')} {item.get('summary','')} ".lower()


def _has_token(text: str, token: str) -> bool:
    return re.search(r"(?<![a-z0-9])" + re.escape(token.lower()) + r"(?![a-z0-9])", text) is not None


def _tone(text: str) -> tuple[int, list[str]]:
    hits: list[str] = []
    score = 0
    low = text.lower()
    for w in UP:
        if _has_token(low, w):
            score += 1
            hits.append(f"+{w}")
    for w in DOWN:
        if _has_token(low, w):
            score -= 1
            hits.append(f"-{w}")
    return score, hits


def _horizon(text: str) -> float:
    """Past-tape headlines are weaker next-session signals than forward ones."""
    low = text.lower()
    fwd = sum(1 for w in FORWARD if w in low)
    back = sum(1 for w in BACKWARD if w in low)
    if any(w in low for w in ROUNDUP):
        return 0.35
    if fwd and not back:
        return 1.25
    if back and not fwd:
        return 0.30
    if back and fwd:
        return 0.70
    return 1.0


def _chance(score: float, mentions: int, side: str) -> int:
    signed = score if side == "up" else -score
    strength = signed + 0.25 * mentions
    raw = 50 + 42 * math.tanh(strength / 10.0)
    return int(max(8, min(91, round(raw))))


def _mentions(text: str) -> list[dict[str, Any]]:
    low = f" {text.lower()} "
    found: list[dict[str, Any]] = []
    seen: set[str] = set()
    ranked = []
    for c in COMPANIES:
        for alias in c["aliases"]:
            ranked.append((len(alias), alias, c))
    ranked.sort(reverse=True)
    occupied: list[tuple[int, int]] = []
    for _, alias, c in ranked:
        if c["name"] in seen:
            continue
        blocked = False
        for bad in BLOCK.get(c["name"], []):
            if bad in low:
                blocked = True
                break
        if blocked:
            continue
        m = re.search(r"(?<![a-z0-9])" + re.escape(alias.lower()) + r"(?![a-z0-9])", low)
        if not m:
            continue
        idx, end = m.start(), m.end()
        if any(idx < b and end > a for a, b in occupied):
            continue
        occupied.append((idx, end))
        seen.add(c["name"])
        found.append(c)
    return found


def _share_weight(n_names: int) -> float:
    if n_names <= 1:
        return 1.0
    if n_names == 2:
        return 0.45
    return 0.20


def analyze_inbox(items: list[dict[str, Any]]) -> dict[str, Any]:
    contrib: dict[str, int] = defaultdict(int)
    companies: dict[str, dict[str, Any]] = {}
    sectors: dict[str, dict[str, Any]] = defaultdict(lambda: {"up": 0, "down": 0, "mentions": 0, "score": 0.0})
    evidence: list[dict[str, Any]] = []

    for item in items:
        agent = item.get("agent_name") or item.get("routed_by") or "unknown"
        contrib[agent] += 1
        text = _blob(item)
        raw_tone, hits = _tone(text)
        names = _mentions(text)
        horizon = _horizon(text)
        weight = _share_weight(len(names)) * horizon
        unpriced = bool(item.get("unpriced") or agent == "after_hours_agent")
        if unpriced:
            weight *= 2.0
        tone = raw_tone * weight
        sector = item.get("sector") or "unknown"
        sec = sectors[sector]
        sec["mentions"] += 1
        sec["score"] += tone
        if tone > 0:
            sec["up"] += 1
        elif tone < 0:
            sec["down"] += 1

        for c in names:
            row = companies.setdefault(
                c["name"],
                {
                    "name": c["name"],
                    "sector": c["sector"],
                    "mentions": 0,
                    "score": 0.0,
                    "tilt": "neutral",
                    "why": [],
                    "headlines": [],
                    "after_hours": 0,
                },
            )
            row["mentions"] += 1
            row["score"] += tone
            if unpriced:
                row["after_hours"] = int(row.get("after_hours") or 0) + 1
            if item.get("headline") and item["headline"] not in row["headlines"]:
                row["headlines"].append(item["headline"])
            for h in hits[:4]:
                if h not in row["why"]:
                    row["why"].append(h)
            if unpriced and "unpriced after-hours" not in row["why"]:
                row["why"].append("unpriced after-hours")
            if horizon <= 0.35 and "priced-in/past tape" not in row["why"]:
                row["why"].append("priced-in/past tape")
            if len(names) >= 3 and "basket headline" not in row["why"]:
                row["why"].append("basket headline")

        if names and raw_tone != 0:
            evidence.append(
                {
                    "headline": item.get("headline"),
                    "sector": sector,
                    "companies": [c["name"] for c in names],
                    "tone": round(tone, 2),
                    "source": item.get("source"),
                    "source_url": item.get("source_url"),
                    "agent_name": agent,
                }
            )

    hist_nudge: dict[str, int] = {}
    for item in items:
        if item.get("agent_name") != "historical_correlation_agent":
            continue
        name = item.get("company")
        align = item.get("alignment")
        if not name:
            continue
        if align == "supports_up":
            hist_nudge[name] = hist_nudge.get(name, 0) + 2
        elif align == "supports_down":
            hist_nudge[name] = hist_nudge.get(name, 0) - 2
    for name, delta in hist_nudge.items():
        if name in companies:
            companies[name]["score"] += delta
            companies[name]["why"].append(f"history {delta:+}")
            companies[name]["history_nudge"] = delta

    earn_nudge: dict[str, int] = {}
    for item in items:
        if item.get("agent_name") != "earnings_surprise_agent":
            continue
        surprise = item.get("surprise")
        names = item.get("companies") or ([item.get("company")] if item.get("company") else [])
        delta = 0
        if surprise == "beat":
            delta = 4
        elif surprise == "miss":
            delta = -4
        elif surprise == "inline":
            delta = 0
        else:
            continue
        for name in names:
            if not name:
                continue
            earn_nudge[name] = earn_nudge.get(name, 0) + delta
    for name, delta in earn_nudge.items():
        if name in companies and delta:
            companies[name]["score"] += delta
            companies[name]["why"].append(f"earnings {delta:+}")
            companies[name]["earnings_nudge"] = delta

    ranked = []
    for row in companies.values():
        row["score"] = round(float(row["score"]), 2)
        if row["score"] > 0:
            row["tilt"] = "up"
        elif row["score"] < 0:
            row["tilt"] = "down"
        else:
            row["tilt"] = "mixed"
        row["chance_up"] = _chance(row["score"], row["mentions"], "up")
        row["chance_down"] = _chance(row["score"], row["mentions"], "down")
        row["headlines"] = row["headlines"][:3]
        row["conviction"] = abs(row["score"]) >= MIN_ABS_SCORE and row["mentions"] >= MIN_MENTIONS
        ranked.append(row)
    ranked.sort(key=lambda r: (r["score"], r["mentions"]), reverse=True)

    up_all = [r for r in ranked if r["tilt"] == "up"]
    up_all.sort(key=lambda r: (r["conviction"], r["score"], r["mentions"]), reverse=True)
    up = up_all[:5]
    down_all = [r for r in ranked if r["tilt"] == "down"]
    down_all.sort(key=lambda r: (r["conviction"], -r["score"], r["mentions"]), reverse=True)
    down = down_all[:5]

    sector_rows = []
    for name, sec in sectors.items():
        tilt = "up" if sec["score"] > 0 else "down" if sec["score"] < 0 else "mixed"
        sector_rows.append({"sector": name, **sec, "tilt": tilt, "score": round(float(sec["score"]), 2)})
    sector_rows.sort(key=lambda r: r["score"], reverse=True)

    steps = [
        {"key": "ingest", "label": "Ingest satellite packets", "status": "done", "detail": f"{len(items)} items"},
        {"key": "agents", "label": "Split by source agent", "status": "done", "detail": ", ".join(f"{k}={v}" for k, v in contrib.items()) or "none"},
        {"key": "names", "label": "Extract listed companies (word-bound, no lookalikes)", "status": "done", "detail": f"{len(ranked)} companies named"},
        {"key": "tone", "label": "Score forward news, down-weight past-tape / baskets", "status": "done", "detail": f"{len(up)} leaning up · {len(down)} leaning down"},
        {
            "key": "history",
            "label": "Apply historical 5d reaction nudge",
            "status": "done",
            "detail": f"{len(hist_nudge)} names nudged" if hist_nudge else "no history packet yet",
        },
        {"key": "brief", "label": "Build CORE-01 briefing", "status": "done", "detail": "ready"},
    ]

    if up:
        top = ", ".join(f"{c['name']} {c['chance_up']}%" for c in up[:5])
        brief = (
            f"Top-5 news-flow UP chances: {top}. "
            "This is headline-language probability, not a guaranteed move."
        )
    elif ranked:
        brief = (
            "CORE-01 read the live packet stream but net language is mixed or negative. "
            "No clean 'up' cluster yet."
        )
    else:
        brief = "CORE-01 is waiting. Satellite agents have not named specific companies yet."

    after_hours = [
        {
            "name": r["name"],
            "sector": r["sector"],
            "after_hours": r.get("after_hours") or 0,
            "tilt": r["tilt"],
            "score": r["score"],
            "headlines": r["headlines"][:2],
        }
        for r in ranked
        if r.get("after_hours")
    ]
    after_hours.sort(key=lambda r: (-r["after_hours"], -abs(r["score"])))

    # NEXT SESSION book: only unpriced tape + stated earnings beat/miss.
    # Session-hour "rally today" news is excluded on purpose.
    ns: dict[str, dict[str, Any]] = {}
    for item in items:
        agent = item.get("agent_name") or ""
        unpriced = bool(item.get("unpriced") or agent == "after_hours_agent")
        surprise = item.get("surprise")
        earn = agent == "earnings_surprise_agent" and surprise in {"beat", "miss"}
        if not (unpriced or earn):
            continue
        text = _blob(item)
        raw_tone, hits = _tone(text)
        names = _mentions(text)
        if earn and item.get("company"):
            extra = [c for c in COMPANIES if c["name"] == item["company"]]
            for c in extra:
                if c not in names:
                    names.append(c)
        if not names:
            continue
        weight = _share_weight(len(names)) * (1.25 if earn else 1.0)
        tone = raw_tone * weight
        if surprise == "beat":
            tone += 4
        elif surprise == "miss":
            tone -= 4
        for c in names:
            row = ns.setdefault(
                c["name"],
                {
                    "name": c["name"],
                    "sector": c["sector"],
                    "mentions": 0,
                    "score": 0.0,
                    "why": [],
                    "headlines": [],
                    "after_hours": 0,
                    "earnings": None,
                },
            )
            row["mentions"] += 1
            row["score"] += tone
            if unpriced:
                row["after_hours"] += 1
            if earn:
                row["earnings"] = surprise
            if item.get("headline") and item["headline"] not in row["headlines"]:
                row["headlines"].append(item["headline"])
            for h in hits[:3]:
                if h not in row["why"]:
                    row["why"].append(h)

    ns_ranked = []
    for row in ns.values():
        row["score"] = round(float(row["score"]), 2)
        row["tilt"] = "up" if row["score"] > 0 else "down" if row["score"] < 0 else "mixed"
        row["chance_up"] = _chance(row["score"], row["mentions"], "up")
        row["chance_down"] = _chance(row["score"], row["mentions"], "down")
        row["headlines"] = row["headlines"][:2]
        ns_ranked.append(row)
    ns_up = sorted([r for r in ns_ranked if r["tilt"] == "up"], key=lambda r: (r["score"], r["mentions"]), reverse=True)[:5]
    ns_down = sorted([r for r in ns_ranked if r["tilt"] == "down"], key=lambda r: (r["score"], -r["mentions"]))[:5]

    flow_up = sorted([r for r in ranked if r["tilt"] == "up"], key=lambda r: (r["mentions"], r["score"]), reverse=True)[:8]
    flow_down = sorted([r for r in ranked if r["tilt"] == "down"], key=lambda r: (r["mentions"], -r["score"]), reverse=True)[:8]

    if ns_up:
        brief = (
            "NEXT SESSION (unpriced + earnings only): "
            + ", ".join(f"{c['name']} lean-up {c['chance_up']}%" for c in ns_up[:3])
            + ". Not a price forecast. NEWS FLOW board has no tomorrow %."
        )
    elif ranked:
        brief = "NEWS FLOW has names, but no unpriced / earnings packet for a next-session book yet."
    else:
        brief = "CORE-01 is waiting. Satellite agents have not named specific companies yet."

    return {
        "name": "core-01",
        "display_name": "CORE-01 News",
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "packet_count": len(items),
        "contributions": dict(contrib),
        "steps": steps,
        "companies_up": up[:12],
        "companies_down": sorted(down, key=lambda r: (r["score"], -r["mentions"]))[:8],
        "news_flow_up": flow_up,
        "news_flow_down": flow_down,
        "next_session_up": ns_up,
        "next_session_down": ns_down,
        "sectors": sector_rows,
        "evidence": evidence[:20],
        "after_hours": after_hours[:12],
        "brief": brief,
        "disclaimer": (
            "Two boards. NEWS FLOW = who is in headlines (no tomorrow %). "
            "NEXT SESSION = after 15:30 / weekend / pre-open + stated earnings beat/miss only. "
            "Lean % is unpriced-news strength, not a Monday guarantee. Not investment advice."
        ),
    }
