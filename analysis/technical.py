"""
Technical analysis — indicators, signals, and momentum.
Uses the 'ta' library for indicator computation.
"""

import pandas as pd
import numpy as np
import ta
import ta.trend
import ta.momentum
import ta.volatility
import ta.volume


def analyze(data: dict) -> dict:
    """
    Compute technical indicators and generate signals.

    Returns structured dict with indicators and a summary.
    """
    hist = data.get("history", pd.DataFrame())

    if hist.empty or len(hist) < 20:
        return {"error": "Not enough price history for technical analysis."}

    df = hist.copy()
    df.columns = [c.lower() for c in df.columns]

    indicators = _compute_indicators(df)
    signals = _generate_signals(indicators, df)
    support_resistance = _find_support_resistance(df)

    return {
        "indicators": indicators,
        "signals": signals,
        "support_resistance": support_resistance,
        "summary": _summarize(signals),
        "df": df,  # Used for charting
    }


# ── Indicators ─────────────────────────────────────────────────────────────────

def _compute_indicators(df: pd.DataFrame) -> dict:
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    ind = {}

    # ── Moving Averages ────────────────────────────────
    for period in [20, 50, 200]:
        sma = ta.trend.sma_indicator(close, window=period)
        ind[f"sma_{period}"] = _last(sma)

    for period in [12, 26]:
        ema = ta.trend.ema_indicator(close, window=period)
        ind[f"ema_{period}"] = _last(ema)

    # ── RSI ────────────────────────────────────────────
    rsi = ta.momentum.rsi(close, window=14)
    ind["rsi"] = _last(rsi)

    # ── MACD ───────────────────────────────────────────
    macd_line = ta.trend.macd(close)
    macd_signal = ta.trend.macd_signal(close)
    macd_hist = ta.trend.macd_diff(close)
    ind["macd"] = _last(macd_line)
    ind["macd_signal"] = _last(macd_signal)
    ind["macd_hist"] = _last(macd_hist)
    ind["_macd_series"] = macd_line
    ind["_macd_signal_series"] = macd_signal
    ind["_macd_hist_series"] = macd_hist

    # ── Bollinger Bands ────────────────────────────────
    bb = ta.volatility.BollingerBands(close, window=20)
    ind["bb_upper"] = _last(bb.bollinger_hband())
    ind["bb_mid"] = _last(bb.bollinger_mavg())
    ind["bb_lower"] = _last(bb.bollinger_lband())
    ind["_bb_upper_series"] = bb.bollinger_hband()
    ind["_bb_lower_series"] = bb.bollinger_lband()

    # ── ATR (volatility) ───────────────────────────────
    atr = ta.volatility.average_true_range(high, low, close, window=14)
    ind["atr"] = _last(atr)

    # ── Volume moving average ──────────────────────────
    vol_sma = ta.trend.sma_indicator(volume.astype(float), window=20)
    ind["vol_sma_20"] = _last(vol_sma)
    ind["vol_current"] = _last(volume)

    # ── Stochastic ─────────────────────────────────────
    stoch = ta.momentum.StochasticOscillator(high, low, close, window=14)
    ind["stoch_k"] = _last(stoch.stoch())
    ind["stoch_d"] = _last(stoch.stoch_signal())

    # ── Current price ──────────────────────────────────
    ind["price"] = _last(close)

    return ind


# ── Signals ────────────────────────────────────────────────────────────────────

def _generate_signals(ind: dict, df: pd.DataFrame) -> dict:
    signals = {}
    price = ind.get("price")

    # ── Trend signals ──────────────────────────────────
    if price and ind.get("sma_50") and ind.get("sma_200"):
        if price > ind["sma_200"]:
            signals["above_200sma"] = {"value": True, "label": "Price above 200 SMA", "bullish": True}
        else:
            signals["above_200sma"] = {"value": False, "label": "Price below 200 SMA", "bullish": False}

        if ind["sma_50"] > ind["sma_200"]:
            signals["ma_cross"] = {"value": "Golden Cross", "label": "50 SMA > 200 SMA (Golden Cross)", "bullish": True}
        else:
            signals["ma_cross"] = {"value": "Death Cross", "label": "50 SMA < 200 SMA (Death Cross)", "bullish": False}

    # ── RSI signals ────────────────────────────────────
    rsi = ind.get("rsi")
    if rsi is not None:
        if rsi < 30:
            signals["rsi"] = {"value": round(rsi, 1), "label": f"RSI {rsi:.1f} — Oversold", "bullish": True}
        elif rsi > 70:
            signals["rsi"] = {"value": round(rsi, 1), "label": f"RSI {rsi:.1f} — Overbought", "bullish": False}
        else:
            signals["rsi"] = {"value": round(rsi, 1), "label": f"RSI {rsi:.1f} — Neutral", "bullish": None}

    # ── MACD signals ───────────────────────────────────
    macd = ind.get("macd")
    macd_sig = ind.get("macd_signal")
    if macd is not None and macd_sig is not None:
        if macd > macd_sig:
            signals["macd"] = {"value": round(macd - macd_sig, 4), "label": "MACD above signal (bullish)", "bullish": True}
        else:
            signals["macd"] = {"value": round(macd - macd_sig, 4), "label": "MACD below signal (bearish)", "bullish": False}

    # ── Bollinger Band signals ─────────────────────────
    bb_upper = ind.get("bb_upper")
    bb_lower = ind.get("bb_lower")
    if price and bb_upper and bb_lower:
        if price >= bb_upper:
            signals["bb"] = {"value": "Upper band", "label": "Price at upper Bollinger Band (overbought zone)", "bullish": False}
        elif price <= bb_lower:
            signals["bb"] = {"value": "Lower band", "label": "Price at lower Bollinger Band (oversold zone)", "bullish": True}
        else:
            signals["bb"] = {"value": "Mid band", "label": "Price within Bollinger Bands", "bullish": None}

    # ── Volume confirmation ────────────────────────────
    vol = ind.get("vol_current")
    vol_avg = ind.get("vol_sma_20")
    if vol and vol_avg and vol_avg > 0:
        ratio = vol / vol_avg
        if ratio > 1.5:
            signals["volume"] = {"value": f"{ratio:.1f}x avg", "label": f"Volume {ratio:.1f}x average — strong conviction", "bullish": None}
        elif ratio < 0.5:
            signals["volume"] = {"value": f"{ratio:.1f}x avg", "label": f"Volume {ratio:.1f}x average — weak conviction", "bullish": None}

    # ── Stochastic ─────────────────────────────────────
    stoch_k = ind.get("stoch_k")
    stoch_d = ind.get("stoch_d")
    if stoch_k is not None and stoch_d is not None:
        if stoch_k < 20 and stoch_d < 20:
            signals["stoch"] = {"value": round(stoch_k, 1), "label": f"Stochastic {stoch_k:.1f} — Oversold", "bullish": True}
        elif stoch_k > 80 and stoch_d > 80:
            signals["stoch"] = {"value": round(stoch_k, 1), "label": f"Stochastic {stoch_k:.1f} — Overbought", "bullish": False}

    return signals


# ── Support / Resistance ───────────────────────────────────────────────────────

def _find_support_resistance(df: pd.DataFrame, window: int = 20) -> dict:
    high = df["high"]
    low = df["low"]

    recent_high = high.rolling(window=window, center=True).max()
    recent_low = low.rolling(window=window, center=True).min()

    pivots_high = df[high == recent_high]["high"].dropna()
    pivots_low = df[low == recent_low]["low"].dropna()

    current_price = df["close"].iloc[-1]

    resistances = sorted([p for p in pivots_high.unique() if p > current_price])[:3]
    supports = sorted([p for p in pivots_low.unique() if p < current_price], reverse=True)[:3]

    return {
        "support": [round(s, 2) for s in supports],
        "resistance": [round(r, 2) for r in resistances],
        "current_price": round(current_price, 2),
    }


# ── Summary ────────────────────────────────────────────────────────────────────

def _summarize(signals: dict) -> dict:
    bullish = [s["label"] for s in signals.values() if s.get("bullish") is True]
    bearish = [s["label"] for s in signals.values() if s.get("bullish") is False]
    neutral = [s["label"] for s in signals.values() if s.get("bullish") is None]

    score = len(bullish) - len(bearish)
    if score >= 2:
        trend = "Bullish"
    elif score <= -2:
        trend = "Bearish"
    else:
        trend = "Neutral / Mixed"

    return {
        "bullish_signals": bullish,
        "bearish_signals": bearish,
        "neutral_signals": neutral,
        "trend": trend,
        "score": score,
    }


# ── Helpers ────────────────────────────────────────────────────────────────────

def _last(series) -> float | None:
    if series is None or len(series) == 0:
        return None
    val = series.dropna()
    if len(val) == 0:
        return None
    return round(float(val.iloc[-1]), 4)
