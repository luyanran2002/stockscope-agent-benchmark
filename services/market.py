"""Resilient public market-data access for the dashboard.

Nasdaq's public historical endpoint is used first. Unlike Yahoo Finance it does
not require cookies or a crumb token, so it works reliably from shared cloud IPs.
Yahoo remains an optional fallback and metadata provider.
"""

from datetime import date, timedelta
import json
import os
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from typing import Optional

import pandas as pd
import streamlit as st
import yfinance as yf


def _secret(name: str) -> str:
    """Read an optional Streamlit secret without making local development fail."""
    try:
        return st.secrets.get(name, os.getenv(name, ""))
    except Exception:
        return os.getenv(name, "")


def _json_request(url: str, headers: Optional[dict] = None) -> dict:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; StockScope/1.0)", **(headers or {})})
    with urlopen(request, timeout=15) as response:
        return json.load(response)


def normalise_ticker(value: str) -> str:
    """Accept common user input such as brk.b and return Yahoo's BRK-B form."""
    symbol = (value or "").strip().upper().replace(".", "-").replace(" ", "")
    return symbol if re.fullmatch(r"[A-Z0-9^-]{1,15}", symbol) else ""


def _start_date(period: str) -> date:
    days = {"1mo": 35, "3mo": 100, "6mo": 190, "1y": 380, "2y": 760, "5y": 1880}
    return date.today() - timedelta(days=days.get(period, 380))


def _nasdaq_history(symbol: str, period: str) -> pd.DataFrame:
    """Fetch official Nasdaq daily OHLCV without an API key."""
    rows = []
    # Nasdaq separates ETFs (SPY, QQQ, IWM...) from common stocks.
    for asset_class in ("etf", "stocks") if symbol in {"SPY", "QQQ", "IWM", "DIA", "VTI"} else ("stocks", "etf"):
        query = urlencode({
            "assetclass": asset_class,
            "fromdate": _start_date(period).isoformat(),
            "todate": date.today().isoformat(),
            "limit": "5000",
        })
        url = f"https://api.nasdaq.com/api/quote/{symbol}/historical?{query}"
        payload = _json_request(url, {"Accept": "application/json, text/plain, */*"})
        body = payload.get("data") if isinstance(payload, dict) else None
        rows = body.get("tradesTable", {}).get("rows", []) if isinstance(body, dict) else []
        if rows:
            break
    if not rows:
        return pd.DataFrame()
    raw = pd.DataFrame(rows).rename(columns={"date": "Date", "close": "Close", "volume": "Volume", "open": "Open", "high": "High", "low": "Low"})
    raw["Date"] = pd.to_datetime(raw["Date"], format="%m/%d/%Y", errors="coerce")
    for column in ["Open", "High", "Low", "Close", "Volume"]:
        raw[column] = pd.to_numeric(raw[column].astype(str).str.replace(r"[$,]", "", regex=True), errors="coerce")
    raw = raw.dropna(subset=["Date", "Close"]).set_index("Date").sort_index()
    raw.attrs["source"] = "Nasdaq（公开日线）"
    return raw


def _yahoo_history(symbol: str, period: str) -> pd.DataFrame:
    ticker = yf.Ticker(symbol)
    frame = ticker.history(period=period, interval="1d", auto_adjust=True)
    if frame.empty:
        return pd.DataFrame()
    frame = frame.reset_index()
    frame["Date"] = pd.to_datetime(frame["Date"], utc=True).dt.tz_convert(None)
    frame = frame.set_index("Date").sort_index()
    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = frame.columns.get_level_values(0)
    frame = frame.dropna(subset=["Close"])
    frame.attrs["source"] = "Yahoo Finance"
    return frame


@st.cache_data(ttl=300, show_spinner=False)
def fetch_price_history(symbol: str, period: str) -> pd.DataFrame:
    # Do not let a provider's transient outage take the whole dashboard down.
    try:
        frame = _nasdaq_history(symbol, period)
        if not frame.empty:
            return frame
    except Exception:
        pass
    try:
        return _yahoo_history(symbol, period)
    except Exception as exc:
        raise RuntimeError("公开行情源暂时不可用，请稍后刷新。") from exc


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_company_profile(symbol: str) -> dict:
    """Public Nasdaq data plus optional Alpha Vantage valuation fundamentals."""
    profile: dict = {}
    asset_class = "etf" if symbol in {"SPY", "QQQ", "IWM", "DIA", "VTI"} else "stocks"
    try:
        info = _json_request(f"https://api.nasdaq.com/api/quote/{symbol}/info?assetclass={asset_class}").get("data", {})
        summary = _json_request(f"https://api.nasdaq.com/api/quote/{symbol}/summary?assetclass={asset_class}").get("data", {}).get("summaryData", {})
        profile = {
            "longName": info.get("companyName"), "exchange": info.get("exchange"),
            "marketCap": _to_number(summary.get("MarketCap", {}).get("value")),
            "averageVolume": _to_number(summary.get("AverageVolume", {}).get("value")),
            "sector": summary.get("Sector", {}).get("value"), "industry": summary.get("Industry", {}).get("value"),
        }
    except Exception:
        pass
    api_key = _secret("ALPHAVANTAGE_API_KEY")
    if api_key:
        try:
            overview = _json_request(f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={symbol}&apikey={api_key}")
            profile.update({
                "trailingPE": _to_number(overview.get("PERatio")), "forwardPE": _to_number(overview.get("ForwardPE")),
                "priceToBook": _to_number(overview.get("PriceToBookRatio")), "beta": _to_number(overview.get("Beta")),
                "dividendYield": _to_number(overview.get("DividendYield")), "longBusinessSummary": overview.get("Description"),
                "website": overview.get("OfficialSite"), "fiftyTwoWeekHigh": _to_number(overview.get("52WeekHigh")),
                "fiftyTwoWeekLow": _to_number(overview.get("52WeekLow")),
            })
        except Exception:
            pass
    if profile:
        return {key: value for key, value in profile.items() if value is not None}
    try:
        info = yf.Ticker(symbol).info
    except Exception:
        # Fundamental data is useful but must never block price-chart rendering.
        return {}
    keys = [
        "longName", "shortName", "exchange", "sector", "industry", "website", "country",
        "marketCap", "trailingPE", "forwardPE", "priceToBook", "dividendYield", "beta",
        "fiftyTwoWeekHigh", "fiftyTwoWeekLow", "averageVolume", "longBusinessSummary",
    ]
    return {key: info.get(key) for key in keys if info.get(key) is not None}


def _to_number(value: object) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(str(value).replace("$", "").replace(",", "").replace("%", ""))
    except (TypeError, ValueError):
        return None


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_sp500_constituents() -> list[dict]:
    """Latest S&P 500 constituent table, cached daily for fast ticker discovery."""
    tables = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
    table = tables[0][["Symbol", "Security", "GICS Sector"]].copy()
    table["Symbol"] = table["Symbol"].str.replace(".", "-", regex=False)
    return table.rename(columns={"Symbol": "symbol", "Security": "name", "GICS Sector": "sector"}).to_dict("records")


@st.cache_data(ttl=600, show_spinner=False)
def fetch_x_sentiment(symbol: str) -> Optional[list[dict]]:
    """Recent public X posts via the official API; requires an owner-provided bearer token."""
    token = _secret("X_BEARER_TOKEN")
    if not token:
        return None
    query = urlencode({"query": f"({symbol} OR ${symbol} OR #{symbol}) (lang:en OR lang:zh) -is:retweet", "max_results": "10", "tweet.fields": "created_at,lang,public_metrics"})
    try:
        payload = _json_request(f"https://api.x.com/2/tweets/search/recent?{query}", {"Authorization": f"Bearer {token}"})
        return payload.get("data", [])
    except Exception:
        return []
