"""
Data fetcher — pulls stock and company data from yfinance.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta


# Map period → best interval for yfinance
_PERIOD_INTERVAL = {
    "1d":  "5m",
    "5d":  "30m",
    "1mo": "1d",
    "3mo": "1d",
    "6mo": "1d",
    "1y":  "1d",
    "2y":  "1d",
    "5y":  "1wk",
    "10y": "1wk",
    "max": "1mo",
}

# Periods where fundamentals/financials aren't meaningful
_INTRADAY_PERIODS = {"1d", "5d"}


def fetch_stock_data(ticker: str, period: str = "1y") -> dict:
    """
    Fetch all relevant data for a given ticker.

    Args:
        ticker: Stock symbol (e.g. 'AAPL', 'TSLA')
        period: '1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'max'

    Returns:
        dict with keys: info, history, financials, balance_sheet,
                        cashflow, earnings, news, period, interval
    """
    stock = yf.Ticker(ticker)
    interval = _PERIOD_INTERVAL.get(period, "1d")
    is_intraday = period in _INTRADAY_PERIODS

    result = {"period": period, "interval": interval, "is_intraday": is_intraday}

    # Company info and current price data
    try:
        result["info"] = stock.info or {}
    except Exception:
        result["info"] = {}

    # Price history (OHLCV)
    try:
        hist = stock.history(period=period, interval=interval)
        if hist.empty:
            end = datetime.today()
            start = end - timedelta(days=365)
            hist = stock.history(start=start, end=end, interval="1d")
        result["history"] = hist
    except Exception:
        result["history"] = pd.DataFrame()

    # Financial statements
    try:
        result["financials"] = stock.financials  # Income statement (annual)
    except Exception:
        result["financials"] = pd.DataFrame()

    try:
        result["quarterly_financials"] = stock.quarterly_financials
    except Exception:
        result["quarterly_financials"] = pd.DataFrame()

    try:
        result["balance_sheet"] = stock.balance_sheet
    except Exception:
        result["balance_sheet"] = pd.DataFrame()

    try:
        result["cashflow"] = stock.cashflow
    except Exception:
        result["cashflow"] = pd.DataFrame()

    # Analyst recommendations
    try:
        result["recommendations"] = stock.recommendations
    except Exception:
        result["recommendations"] = pd.DataFrame()

    # Recent news
    try:
        result["news"] = stock.news or []
    except Exception:
        result["news"] = []

    return result


def get_safe(info: dict, key: str, default=None):
    """Safely get a value from info dict, returning default if missing or None."""
    val = info.get(key, default)
    return val if val is not None else default
