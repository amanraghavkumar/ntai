"""Live source catalogue. Every URL is a real public feed / search."""

from __future__ import annotations

from urllib.parse import quote_plus

from classify import SECTORS
from http_client import FetchError, fetch_text
from rss import parse_rss

SECTOR_GOOGLE_Q = {
    "sugar": "India sugar stocks OR sugar mills OR Balrampur Chini OR ethanol blending",
    "IT": "India IT services Infosys OR TCS OR Wipro OR Tech Mahindra stock",
    "pharma": "India pharma Sun Pharma OR Cipla OR Dr Reddy OR USFDA",
    "banking": "India banking HDFC Bank OR ICICI Bank OR SBI OR RBI repo",
    "auto": "India auto Maruti OR Tata Motors OR Mahindra OR EV sales",
    "energy": "India energy Reliance Industries OR NTPC OR ONGC OR Coal India stock",
    "metals": "India metal stocks Tata Steel OR JSW Steel OR Hindalco OR Vedanta",
    "fmcg": "India FMCG HUL OR ITC OR Nestle OR Britannia OR Asian Paints stock",
    "telecom": "India telecom Airtel OR Vodafone Idea OR Zomato OR Paytm stock",
    "finance": "India NBFC Bajaj Finance OR LIC OR HDFC Life OR PFC stock",
    "infra": "India infra L&T OR Adani Ports OR UltraTech OR IndiGo OR Trent stock",
}


def google_news_url(query: str) -> str:
    return (
        "https://news.google.com/rss/search?"
        f"q={quote_plus(query)}&hl=en-IN&gl=IN&ceid=IN:en"
    )


def catalog(wanted: list[str]) -> list[dict]:
    feeds: list[dict] = [
        {
            "id": "et_markets",
            "source": "economic_times",
            "label": "ET Markets",
            "url": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
            "hint": None,
        },
        {
            "id": "et_stocks",
            "source": "economic_times",
            "label": "ET Stocks",
            "url": "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms",
            "hint": None,
        },
        {
            "id": "et_industry",
            "source": "economic_times",
            "label": "ET Industry",
            "url": "https://economictimes.indiatimes.com/industry/rssfeeds/13352306.cms",
            "hint": None,
        },
        {
            "id": "et_tech",
            "source": "economic_times",
            "label": "ET Tech",
            "url": "https://economictimes.indiatimes.com/tech/rssfeeds/13357270.cms",
            "hint": "IT",
        },
        {
            "id": "mc_latest",
            "source": "moneycontrol",
            "label": "Moneycontrol Latest",
            "url": "https://www.moneycontrol.com/rss/latestnews.xml",
            "hint": None,
        },
        {
            "id": "mc_markets",
            "source": "moneycontrol",
            "label": "Moneycontrol Markets",
            "url": "https://www.moneycontrol.com/rss/marketreports.xml",
            "hint": None,
        },
        {
            "id": "mc_biz",
            "source": "moneycontrol",
            "label": "Moneycontrol Business",
            "url": "https://www.moneycontrol.com/rss/business.xml",
            "hint": None,
        },
        {
            "id": "nse_ann",
            "source": "nse_bse_announcements",
            "label": "NSE Announcements",
            "url": "https://nsearchives.nseindia.com/content/RSS/Online_announcements.xml",
            "hint": None,
        },
    ]
    for sector in wanted:
        if sector not in SECTORS and sector != "IT":
            continue
        q = SECTOR_GOOGLE_Q.get(sector)
        if not q:
            continue
        feeds.append(
            {
                "id": f"gnews_{sector}",
                "source": "google_news",
                "label": f"Google News · {sector}",
                "url": google_news_url(q),
                "hint": sector,
            }
        )
    return feeds


def pull_feed(feed: dict) -> tuple[dict, list[dict], str | None]:
    try:
        xml_text = fetch_text(feed["url"])
        rows = parse_rss(xml_text)
        return feed, rows, None
    except FetchError as exc:
        return feed, [], str(exc)
