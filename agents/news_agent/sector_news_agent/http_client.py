"""Shared HTTP helper. Real network only — no cached fiction."""

from __future__ import annotations

import ssl
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/rss+xml, application/xml, text/xml, text/html, */*",
    "Accept-Language": "en-IN,en;q=0.9",
    "Cache-Control": "no-cache",
}

CTX = ssl.create_default_context()


class FetchError(RuntimeError):
    pass


def fetch_text(url: str, timeout: int = 14, retries: int = 2) -> str:
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            req = Request(url, headers=DEFAULT_HEADERS)
            with urlopen(req, timeout=timeout, context=CTX) as resp:
                raw = resp.read()
                charset = resp.headers.get_content_charset() or "utf-8"
                return raw.decode(charset, errors="ignore")
        except (HTTPError, URLError, TimeoutError, ssl.SSLError, OSError) as exc:
            last = exc
            time.sleep(0.35 * (attempt + 1))
    raise FetchError(f"{url.split('?')[0]} → {last}")
