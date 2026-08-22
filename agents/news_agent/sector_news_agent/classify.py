"""Keyword + company map classifier. Returns None when unsure — never guesses."""

from __future__ import annotations

SECTORS: dict[str, list[str]] = {
    "sugar": [
        "sugar", "chini", "ethanol", "cane", "bagasse", "sugar mill",
        "balrampur", "dhampur", "renuka", "triveni", "dalmia bharat sugar",
        "dwarikesh", "bannari amman", "bajaj hindusthan", "eid parry",
        "ethanol blending", "fair and remunerative",
    ],
    "IT": [
        "infosys", "tata consultancy", " tcs ", "wipro",
        "hcltech", "hcl tech", "hcl technologies", "tech mahindra",
        "ltimindtree", "lti mindtree", "persistent systems", "coforge",
        "mphasis", "it services", "software services",
        "infotech", "saas", "ltts", "cyient", "tata elxsi", "kpit",
        "tata technologies", "oracle financial",
    ],
    "pharma": [
        "pharma", "pharmaceutical", "cipla", "sun pharma", "dr reddy",
        "dr. reddy", "biocon", "lupin", "aurobindo", "divis", "divi's",
        "zydus", "glenmark", "alkem", "torrent pharma", "laurus",
        "apollo hospitals", "usfda", "us fda", "anda", "formulation",
    ],
    "banking": [
        "hdfc bank", "icici bank", "state bank of india", "axis bank",
        "kotak mahindra bank", "indusind", "yes bank", "bandhan bank",
        "idfc first", "punjab national", "bank of baroda", "canara bank",
        "federal bank", "reserve bank", "repo rate", "npa",
        "credit growth", "private bank", "psu bank", "banking",
    ],
    "auto": [
        "maruti", "tata motors", "mahindra & mahindra", "hero motocorp",
        "bajaj auto", "eicher", "tvs motor", "ashok leyland", "hyundai",
        "ola electric", "bharat forge", "motherson",
        "two-wheeler", "passenger vehicle", "automobile",
        "auto sector", "ev sales", "electric vehicle",
    ],
    "energy": [
        "reliance industries", "ongc", "ntpc", "power grid", "coal india",
        "tata power", "adani green", "adani power", "suzlon",
        "indian oil", "bpcl", "crude", "renewable", "solar power",
        "oil and gas", "power sector",
    ],
    "metals": [
        "tata steel", "jsw steel", "hindalco", "vedanta", "jindal steel",
        "steel authority", "hindustan zinc", "nmdc", "steel prices",
        "aluminium", "copper", "iron ore",
    ],
    "fmcg": [
        "hindustan unilever", "itc", "nestle", "britannia", "dabur",
        "marico", "tata consumer", "varun beverages", "asian paints",
        "pidilite", "titan company", "fmcg",
    ],
    "telecom": [
        "bharti airtel", "airtel", "vodafone idea", "jio", "5g",
        "zomato", "paytm", "nykaa", "naukri", "telecom",
    ],
    "finance": [
        "bajaj finance", "bajaj finserv", "sbi life", "hdfc life",
        "power finance corporation", "shriram finance", "cholamandalam",
        "nbfc", "life insurance corporation",
    ],
    "infra": [
        "larsen & toubro", "adani ports", "adani enterprises", "ultratech",
        "shree cement", "ambuja", "grasim", "indigo", "interglobe",
        "trent", "dmart", "dixon", "polycab", "havells",
        "hindustan aeronautics", "bharat electronics", "irctc",
        "cement", "infrastructure",
    ],
}

CANON = {"it": "IT"}


def normalize_sector(name: str | None) -> str | None:
    if not name:
        return None
    if name.lower() == "it":
        return "IT"
    return name.lower() if name.lower() in SECTORS or name == "IT" else None


def classify(headline: str, summary: str = "", hint: str | None = None) -> tuple[str | None, int]:
    blob = f" {headline} {summary} ".lower()
    scores: dict[str, int] = {}
    for sector, keywords in SECTORS.items():
        score = 0
        for kw in keywords:
            if kw.lower() in blob:
                score += 2 if " " in kw or len(kw) > 6 else 1
        if score:
            scores[sector] = score
    hint_n = normalize_sector(hint)
    if hint_n and hint_n in scores:
        scores[hint_n] += 2
    if not scores:
        return None, 0
    winner = max(scores, key=scores.get)
    if scores[winner] < 2 and hint_n != winner:
        return None, scores[winner]
    return winner, scores[winner]
