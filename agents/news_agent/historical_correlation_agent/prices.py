"""Live NSE daily bars. Moneycontrol first, Yahoo spark as fallback."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

from http_client import FetchError, fetch_text

CACHE = Path(__file__).resolve().parent / "data" / "price_cache"
CACHE.mkdir(parents=True, exist_ok=True)

# Moneycontrol sometimes uses a different NSE symbol after demergers.
MC_ALIAS = {
    "TATAMOTORS": "TMCV",
}


def _nse_symbol(ticker: str) -> str:
    return ticker.replace(".NS", "").replace(".BO", "")


def fetch_mc_history(nse_symbol: str) -> dict[str, Any]:
    nse_symbol = MC_ALIAS.get(nse_symbol, nse_symbol)
    now = int(time.time())
    frm = now - 200 * 86400
    encoded = quote(nse_symbol, safe="-._")
    url = (
        "https://priceapi.moneycontrol.com/techCharts/indianMarket/stock/history"
        f"?symbol={encoded}&resolution=1D&from={frm}&to={now}&countback=160&currencyCode=INR"
    )
    raw = fetch_text(url, timeout=16, retries=1)
    data = json.loads(raw)
    if data.get("s") != "ok":
        raise FetchError(f"mc {nse_symbol} {data.get('s')}")
    ts = data.get("t") or []
    closes = data.get("c") or []
    wrapped = {
        "chart": {
            "result": [{"timestamp": ts, "indicators": {"quote": [{"close": closes}]}}]
        }
    }
    return _parse_chart(f"{nse_symbol}.NS", wrapped)


def fetch_charts(tickers: list[str], range_code: str = "6mo") -> dict[str, dict[str, Any]]:
    """Moneycontrol history first (Yahoo is often 429)."""
    out: dict[str, dict[str, Any]] = {}
    for ticker in tickers:
        try:
            out[ticker] = fetch_chart(ticker, range_code)
            time.sleep(0.12)
        except Exception:
            continue
    if out:
        return out
    url = (
        "https://query1.finance.yahoo.com/v7/finance/spark?"
        f"symbols={','.join(tickers)}&range={range_code}&interval=1d"
    )
    raw = fetch_text(url, timeout=18, retries=1)
    data = json.loads(raw)
    for node in (data.get("spark") or {}).get("result") or []:
        symbol = node.get("symbol")
        resp = (node.get("response") or [{}])[0]
        ts = resp.get("timestamp") or []
        closes = ((resp.get("indicators") or {}).get("quote") or [{}])[0].get("close") or []
        if not ts or not closes:
            continue
        wrapped = {
            "chart": {
                "result": [
                    {"timestamp": ts, "indicators": {"quote": [{"close": closes}]}}
                ]
            }
        }
        try:
            out[symbol] = _parse_chart(symbol, wrapped)
        except FetchError:
            continue
    return out


def fetch_chart(ticker: str, range_code: str = "6mo") -> dict[str, Any]:
    safe = ticker.replace("/", "_")
    cache_file = CACHE / f"{safe}_{range_code}.json"
    if cache_file.exists() and time.time() - cache_file.stat().st_mtime < 1800:
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            return _parse_chart(ticker, data)
        except Exception:
            pass

    nse = _nse_symbol(ticker)
    try:
        parsed = fetch_mc_history(nse)
        payload = {
            "chart": {
                "result": [
                    {
                        "timestamp": [b["ts"] for b in parsed["bars"]],
                        "indicators": {"quote": [{"close": [b["close"] for b in parsed["bars"]]}]},
                    }
                ]
            }
        }
        cache_file.write_text(json.dumps(payload), encoding="utf-8")
        return parsed
    except Exception:
        pass

    url = (
        "https://query2.finance.yahoo.com/v8/finance/chart/"
        f"{ticker}?interval=1d&range={range_code}"
    )
    last = None
    raw = ""
    try:
        raw = fetch_text(url, timeout=10, retries=0)
    except FetchError as exc:
        last = exc
        if cache_file.exists():
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            return _parse_chart(ticker, data)
        raise last
    data = json.loads(raw)
    cache_file.write_text(json.dumps(data), encoding="utf-8")
    return _parse_chart(ticker, data)


def _parse_chart(ticker: str, data: dict[str, Any]) -> dict[str, Any]:
    result = (data.get("chart") or {}).get("result") or []
    if not result:
        raise FetchError(f"no chart for {ticker}")
    node = result[0]
    ts = node.get("timestamp") or []
    quote = ((node.get("indicators") or {}).get("quote") or [{}])[0]
    closes = quote.get("close") or []
    rows = []
    for t, c in zip(ts, closes):
        if c is None:
            continue
        rows.append(
            {
                "ts": int(t),
                "date": datetime.fromtimestamp(int(t), tz=timezone.utc).date().isoformat(),
                "close": float(c),
            }
        )
    if len(rows) < 6:
        raise FetchError(f"too few bars for {ticker}")
    return {"ticker": ticker, "bars": rows}


def pct(a: float, b: float) -> float:
    if not a:
        return 0.0
    return round((b / a - 1.0) * 100.0, 2)


def window_returns(bars: list[dict]) -> dict[str, float]:
    closes = [b["close"] for b in bars]
    last = closes[-1]

    def back(n: int) -> float:
        if len(closes) <= n:
            return pct(closes[0], last)
        return pct(closes[-1 - n], last)

    return {
        "last": round(last, 2),
        "ret_1d": back(1),
        "ret_5d": back(5),
        "ret_20d": back(20),
        "ret_60d": back(min(60, len(closes) - 1)),
    }


def reaction_after(bars: list[dict], day_iso: str, ahead: int = 5) -> float | None:
    dates = [b["date"] for b in bars]
    if not dates:
        return None
    idx = None
    for i, d in enumerate(dates):
        if d >= day_iso:
            idx = i
            break
    if idx is None:
        return None
    j = min(idx + ahead, len(bars) - 1)
    if j <= idx:
        return None
    return pct(bars[idx]["close"], bars[j]["close"])
