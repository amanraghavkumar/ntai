"""Single company map for CORE, History and Sector News.

Aliases stay long / unique so Kotak Mahindra ≠ M&M and Infosystems ≠ Infosys.
"""

from __future__ import annotations

import re
from typing import Any

COMPANIES: list[dict[str, Any]] = [
    # sugar
    {"name": "Balrampur Chini", "ticker": "BALRAMCHIN.NS", "sector": "sugar", "aliases": ["balrampur chini", "balrampur"]},
    {"name": "Shree Renuka Sugars", "ticker": "RENUKA.NS", "sector": "sugar", "aliases": ["shree renuka", "renuka sugars"]},
    {"name": "Triveni Engineering", "ticker": "TRIVENI.NS", "sector": "sugar", "aliases": ["triveni engineering"]},
    {"name": "Dalmia Bharat Sugar", "ticker": "DALMIASUG.NS", "sector": "sugar", "aliases": ["dalmia bharat sugar", "dalmia sugar"]},
    {"name": "Dhampur Sugar", "ticker": "DHAMPURSUG.NS", "sector": "sugar", "aliases": ["dhampur sugar", "dhampur"]},
    {"name": "Dwarikesh Sugar", "ticker": "DWARKESH.NS", "sector": "sugar", "aliases": ["dwarikesh sugar", "dwarikesh"]},
    {"name": "Bajaj Hindusthan Sugar", "ticker": "BAJAJHIND.NS", "sector": "sugar", "aliases": ["bajaj hindusthan"]},
    {"name": "Bannari Amman Sugars", "ticker": "BANARISUG.NS", "sector": "sugar", "aliases": ["bannari amman"]},
    {"name": "EID Parry", "ticker": "EIDPARRY.NS", "sector": "sugar", "aliases": ["eid parry"]},
    # IT
    {"name": "Infosys", "ticker": "INFY.NS", "sector": "IT", "aliases": ["infosys"]},
    {"name": "TCS", "ticker": "TCS.NS", "sector": "IT", "aliases": ["tata consultancy", "tcs"]},
    {"name": "Wipro", "ticker": "WIPRO.NS", "sector": "IT", "aliases": ["wipro"]},
    {"name": "HCLTech", "ticker": "HCLTECH.NS", "sector": "IT", "aliases": ["hcltech", "hcl tech", "hcl technologies"]},
    {"name": "Tech Mahindra", "ticker": "TECHM.NS", "sector": "IT", "aliases": ["tech mahindra"]},
    {"name": "Persistent Systems", "ticker": "PERSISTENT.NS", "sector": "IT", "aliases": ["persistent systems"]},
    {"name": "Coforge", "ticker": "COFORGE.NS", "sector": "IT", "aliases": ["coforge"]},
    {"name": "LTIMindtree", "ticker": "LTIM.NS", "sector": "IT", "aliases": ["ltimindtree", "lti mindtree"]},
    {"name": "Mphasis", "ticker": "MPHASIS.NS", "sector": "IT", "aliases": ["mphasis"]},
    {"name": "Tata Elxsi", "ticker": "TATAELXSI.NS", "sector": "IT", "aliases": ["tata elxsi"]},
    {"name": "Tata Technologies", "ticker": "TATATECH.NS", "sector": "IT", "aliases": ["tata technologies"]},
    {"name": "KPIT Technologies", "ticker": "KPITTECH.NS", "sector": "IT", "aliases": ["kpit"]},
    {"name": "LTTS", "ticker": "LTTS.NS", "sector": "IT", "aliases": ["l&t technology", "ltts"]},
    {"name": "Cyient", "ticker": "CYIENT.NS", "sector": "IT", "aliases": ["cyient"]},
    {"name": "OFSS", "ticker": "OFSS.NS", "sector": "IT", "aliases": ["oracle financial", "ofss"]},
    # pharma
    {"name": "Sun Pharma", "ticker": "SUNPHARMA.NS", "sector": "pharma", "aliases": ["sun pharma", "sun pharmaceutical"]},
    {"name": "Cipla", "ticker": "CIPLA.NS", "sector": "pharma", "aliases": ["cipla"]},
    {"name": "Dr Reddy's", "ticker": "DRREDDY.NS", "sector": "pharma", "aliases": ["dr reddy", "dr. reddy"]},
    {"name": "Biocon", "ticker": "BIOCON.NS", "sector": "pharma", "aliases": ["biocon"]},
    {"name": "Lupin", "ticker": "LUPIN.NS", "sector": "pharma", "aliases": ["lupin"]},
    {"name": "Aurobindo Pharma", "ticker": "AUROPHARMA.NS", "sector": "pharma", "aliases": ["aurobindo pharma", "aurobindo"]},
    {"name": "Divi's Labs", "ticker": "DIVISLAB.NS", "sector": "pharma", "aliases": ["divi's labs", "divis labs"]},
    {"name": "Zydus Lifesciences", "ticker": "ZYDUSLIFE.NS", "sector": "pharma", "aliases": ["zydus lifesciences", "zydus"]},
    {"name": "Glenmark", "ticker": "GLENMARK.NS", "sector": "pharma", "aliases": ["glenmark"]},
    {"name": "Torrent Pharma", "ticker": "TORNTPHARM.NS", "sector": "pharma", "aliases": ["torrent pharma"]},
    {"name": "Alkem", "ticker": "ALKEM.NS", "sector": "pharma", "aliases": ["alkem"]},
    {"name": "Laurus Labs", "ticker": "LAURUSLABS.NS", "sector": "pharma", "aliases": ["laurus labs", "laurus"]},
    {"name": "Apollo Hospitals", "ticker": "APOLLOHOSP.NS", "sector": "pharma", "aliases": ["apollo hospitals"]},
    # banking
    {"name": "HDFC Bank", "ticker": "HDFCBANK.NS", "sector": "banking", "aliases": ["hdfc bank"]},
    {"name": "ICICI Bank", "ticker": "ICICIBANK.NS", "sector": "banking", "aliases": ["icici bank"]},
    {"name": "SBI", "ticker": "SBIN.NS", "sector": "banking", "aliases": ["state bank of india", "sbi"]},
    {"name": "Axis Bank", "ticker": "AXISBANK.NS", "sector": "banking", "aliases": ["axis bank"]},
    {"name": "Kotak Mahindra Bank", "ticker": "KOTAKBANK.NS", "sector": "banking", "aliases": ["kotak mahindra bank", "kotak bank"]},
    {"name": "IndusInd Bank", "ticker": "INDUSINDBK.NS", "sector": "banking", "aliases": ["indusind bank", "indusind"]},
    {"name": "City Union Bank", "ticker": "CUB.NS", "sector": "banking", "aliases": ["city union bank", "city union"]},
    {"name": "Bank of Baroda", "ticker": "BANKBARODA.NS", "sector": "banking", "aliases": ["bank of baroda"]},
    {"name": "PNB", "ticker": "PNB.NS", "sector": "banking", "aliases": ["punjab national bank"]},
    {"name": "Canara Bank", "ticker": "CANBK.NS", "sector": "banking", "aliases": ["canara bank"]},
    {"name": "Federal Bank", "ticker": "FEDERALBNK.NS", "sector": "banking", "aliases": ["federal bank"]},
    {"name": "Yes Bank", "ticker": "YESBANK.NS", "sector": "banking", "aliases": ["yes bank"]},
    {"name": "IDFC First Bank", "ticker": "IDFCFIRSTB.NS", "sector": "banking", "aliases": ["idfc first"]},
    {"name": "Bandhan Bank", "ticker": "BANDHANBNK.NS", "sector": "banking", "aliases": ["bandhan bank"]},
    # auto
    {"name": "Maruti Suzuki", "ticker": "MARUTI.NS", "sector": "auto", "aliases": ["maruti suzuki", "maruti"]},
    {"name": "Tata Motors", "ticker": "TMCV.NS", "sector": "auto", "aliases": ["tata motors"]},
    {"name": "Mahindra & Mahindra", "ticker": "M&M.NS", "sector": "auto", "aliases": ["mahindra & mahindra", "mahindra and mahindra", "m&m"]},
    {"name": "Bajaj Auto", "ticker": "BAJAJ-AUTO.NS", "sector": "auto", "aliases": ["bajaj auto"]},
    {"name": "TVS Motor", "ticker": "TVSMOTOR.NS", "sector": "auto", "aliases": ["tvs motor", "tvs motors"]},
    {"name": "Hero MotoCorp", "ticker": "HEROMOTOCO.NS", "sector": "auto", "aliases": ["hero motocorp", "hero moto"]},
    {"name": "Eicher Motors", "ticker": "EICHERMOT.NS", "sector": "auto", "aliases": ["eicher motors", "eicher"]},
    {"name": "Ashok Leyland", "ticker": "ASHOKLEY.NS", "sector": "auto", "aliases": ["ashok leyland"]},
    {"name": "Bharat Forge", "ticker": "BHARATFORG.NS", "sector": "auto", "aliases": ["bharat forge"]},
    {"name": "Motherson", "ticker": "MOTHERSON.NS", "sector": "auto", "aliases": ["samvardhana motherson", "motherson"]},
    {"name": "Hyundai Motor India", "ticker": "HYUNDAI.NS", "sector": "auto", "aliases": ["hyundai motor india", "hyundai india"]},
    {"name": "Ola Electric", "ticker": "OLAELEC.NS", "sector": "auto", "aliases": ["ola electric"]},
    # energy
    {"name": "Reliance Industries", "ticker": "RELIANCE.NS", "sector": "energy", "aliases": ["reliance industries", "ril"]},
    {"name": "ONGC", "ticker": "ONGC.NS", "sector": "energy", "aliases": ["ongc"]},
    {"name": "NTPC", "ticker": "NTPC.NS", "sector": "energy", "aliases": ["ntpc"]},
    {"name": "Power Grid", "ticker": "POWERGRID.NS", "sector": "energy", "aliases": ["power grid"]},
    {"name": "Coal India", "ticker": "COALINDIA.NS", "sector": "energy", "aliases": ["coal india"]},
    {"name": "Tata Power", "ticker": "TATAPOWER.NS", "sector": "energy", "aliases": ["tata power"]},
    {"name": "Adani Green", "ticker": "ADANIGREEN.NS", "sector": "energy", "aliases": ["adani green"]},
    {"name": "Adani Power", "ticker": "ADANIPOWER.NS", "sector": "energy", "aliases": ["adani power"]},
    {"name": "Suzlon", "ticker": "SUZLON.NS", "sector": "energy", "aliases": ["suzlon"]},
    {"name": "IOC", "ticker": "IOC.NS", "sector": "energy", "aliases": ["indian oil", "ioc"]},
    {"name": "BPCL", "ticker": "BPCL.NS", "sector": "energy", "aliases": ["bpcl", "bharat petroleum"]},
    # metals
    {"name": "Tata Steel", "ticker": "TATASTEEL.NS", "sector": "metals", "aliases": ["tata steel"]},
    {"name": "JSW Steel", "ticker": "JSWSTEEL.NS", "sector": "metals", "aliases": ["jsw steel"]},
    {"name": "Hindalco", "ticker": "HINDALCO.NS", "sector": "metals", "aliases": ["hindalco"]},
    {"name": "Vedanta", "ticker": "VEDL.NS", "sector": "metals", "aliases": ["vedanta"]},
    {"name": "Jindal Steel", "ticker": "JINDALSTEL.NS", "sector": "metals", "aliases": ["jindal steel"]},
    {"name": "SAIL", "ticker": "SAIL.NS", "sector": "metals", "aliases": ["sail", "steel authority"]},
    {"name": "Hindustan Zinc", "ticker": "HINDZINC.NS", "sector": "metals", "aliases": ["hindustan zinc"]},
    {"name": "NMDC", "ticker": "NMDC.NS", "sector": "metals", "aliases": ["nmdc"]},
    # fmcg
    {"name": "Hindustan Unilever", "ticker": "HINDUNILVR.NS", "sector": "fmcg", "aliases": ["hindustan unilever", "hul"]},
    {"name": "ITC", "ticker": "ITC.NS", "sector": "fmcg", "aliases": ["itc"]},
    {"name": "Nestle India", "ticker": "NESTLEIND.NS", "sector": "fmcg", "aliases": ["nestle india", "nestle"]},
    {"name": "Britannia", "ticker": "BRITANNIA.NS", "sector": "fmcg", "aliases": ["britannia"]},
    {"name": "Dabur", "ticker": "DABUR.NS", "sector": "fmcg", "aliases": ["dabur"]},
    {"name": "Marico", "ticker": "MARICO.NS", "sector": "fmcg", "aliases": ["marico"]},
    {"name": "Tata Consumer", "ticker": "TATACONSUM.NS", "sector": "fmcg", "aliases": ["tata consumer"]},
    {"name": "Varun Beverages", "ticker": "VBL.NS", "sector": "fmcg", "aliases": ["varun beverages"]},
    {"name": "Titan", "ticker": "TITAN.NS", "sector": "fmcg", "aliases": ["titan company", "titan"]},
    {"name": "Asian Paints", "ticker": "ASIANPAINT.NS", "sector": "fmcg", "aliases": ["asian paints"]},
    {"name": "Pidilite", "ticker": "PIDILITIND.NS", "sector": "fmcg", "aliases": ["pidilite"]},
    # telecom / consumer internet
    {"name": "Bharti Airtel", "ticker": "BHARTIARTL.NS", "sector": "telecom", "aliases": ["bharti airtel", "airtel"]},
    {"name": "Vodafone Idea", "ticker": "IDEA.NS", "sector": "telecom", "aliases": ["vodafone idea", "vi "]},
    {"name": "Zomato", "ticker": "ZOMATO.NS", "sector": "telecom", "aliases": ["zomato", "eternal"]},
    {"name": "Paytm", "ticker": "PAYTM.NS", "sector": "telecom", "aliases": ["paytm", "one97"]},
    {"name": "Nykaa", "ticker": "NYKAA.NS", "sector": "telecom", "aliases": ["nykaa"]},
    {"name": "Info Edge", "ticker": "NAUKRI.NS", "sector": "telecom", "aliases": ["info edge", "naukri"]},
    # finance / nbfc / insurance
    {"name": "Bajaj Finance", "ticker": "BAJFINANCE.NS", "sector": "finance", "aliases": ["bajaj finance"]},
    {"name": "Bajaj Finserv", "ticker": "BAJAJFINSV.NS", "sector": "finance", "aliases": ["bajaj finserv"]},
    {"name": "LIC", "ticker": "LICI.NS", "sector": "finance", "aliases": ["life insurance corporation", "lic "]},
    {"name": "SBI Life", "ticker": "SBILIFE.NS", "sector": "finance", "aliases": ["sbi life"]},
    {"name": "HDFC Life", "ticker": "HDFCLIFE.NS", "sector": "finance", "aliases": ["hdfc life"]},
    {"name": "PFC", "ticker": "PFC.NS", "sector": "finance", "aliases": ["power finance corporation"]},
    {"name": "REC", "ticker": "RECLTD.NS", "sector": "finance", "aliases": ["rec ltd", "rural electrification"]},
    {"name": "Shriram Finance", "ticker": "SHRIRAMFIN.NS", "sector": "finance", "aliases": ["shriram finance"]},
    {"name": "Cholamandalam", "ticker": "CHOLAFIN.NS", "sector": "finance", "aliases": ["cholamandalam"]},
    # infra / capital goods / consumption
    {"name": "Larsen & Toubro", "ticker": "LT.NS", "sector": "infra", "aliases": ["larsen & toubro", "l&t"]},
    {"name": "Adani Ports", "ticker": "ADANIPORTS.NS", "sector": "infra", "aliases": ["adani ports"]},
    {"name": "Adani Enterprises", "ticker": "ADANIENT.NS", "sector": "infra", "aliases": ["adani enterprises"]},
    {"name": "UltraTech Cement", "ticker": "ULTRACEMCO.NS", "sector": "infra", "aliases": ["ultratech"]},
    {"name": "Shree Cement", "ticker": "SHREECEM.NS", "sector": "infra", "aliases": ["shree cement"]},
    {"name": "Ambuja Cements", "ticker": "AMBUJACEM.NS", "sector": "infra", "aliases": ["ambuja cements", "ambuja"]},
    {"name": "Grasim", "ticker": "GRASIM.NS", "sector": "infra", "aliases": ["grasim"]},
    {"name": "InterGlobe Aviation", "ticker": "INDIGO.NS", "sector": "infra", "aliases": ["indigo", "interglobe"]},
    {"name": "Trent", "ticker": "TRENT.NS", "sector": "infra", "aliases": ["trent"]},
    {"name": "DMart", "ticker": "DMART.NS", "sector": "infra", "aliases": ["dmart", "avenue supermarts"]},
    {"name": "Dixon", "ticker": "DIXON.NS", "sector": "infra", "aliases": ["dixon"]},
    {"name": "Polycab", "ticker": "POLYCAB.NS", "sector": "infra", "aliases": ["polycab"]},
    {"name": "Havells", "ticker": "HAVELLS.NS", "sector": "infra", "aliases": ["havells"]},
    {"name": "Hindustan Aeronautics", "ticker": "HAL.NS", "sector": "infra", "aliases": ["hindustan aeronautics"]},
    {"name": "Bharat Electronics", "ticker": "BEL.NS", "sector": "infra", "aliases": ["bharat electronics"]},
    {"name": "IRCTC", "ticker": "IRCTC.NS", "sector": "infra", "aliases": ["irctc"]},
]

BLOCK = {
    "Infosys": ["infosystems", "hcl infosystems"],
    "SBI": ["sbi mutual", "sbi etf", "sbi nifty", "sbi mf", "sbi cards", "sbi life"],
    "ICICI Bank": ["icici securities", "icici direct", "icici prudential"],
    "TCS": ["etcs", "ntcs"],
    "Reliance Industries": ["reliance communications", "reliance infrastructure", "reliance power", "reliance capital"],
    "ITC": ["itc hotels"],
    "LIC": ["sbi life", "hdfc life"],
    "Titan": ["titanic"],
    "InterGlobe Aviation": ["indigo paints"],
}

UNIVERSE = COMPANIES


def companies_in_text(text: str) -> list[dict]:
    blob = f" {text.lower()} "
    found = []
    seen = set()
    ranked = []
    for c in COMPANIES:
        for alias in c["aliases"]:
            ranked.append((len(alias), alias, c))
    ranked.sort(reverse=True)
    for _, alias, c in ranked:
        if c["name"] in seen:
            continue
        if any(bad in blob for bad in BLOCK.get(c["name"], [])):
            continue
        if not re.search(r"(?<![a-z0-9])" + re.escape(alias.lower()) + r"(?![a-z0-9])", blob):
            continue
        seen.add(c["name"])
        found.append(c)
    return found
