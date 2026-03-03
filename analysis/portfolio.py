"""
Portfolio recommendation engine.

Combines P&L position data with technical, fundamental, and wave
analysis to produce a structured hold/sell/add recommendation.
"""


def generate_recommendation(
    holding: dict,
    current_price: float,
    tech: dict,
    fund: dict,
    wave: dict,
) -> dict:
    """
    Produce a recommendation for a single holding.

    Args:
        holding:       DB row dict (ticker, entry_price, quantity, entry_date, notes)
        current_price: Live price fetched from yfinance info
        tech:          Result from analysis.technical.analyze()
        fund:          Result from analysis.fundamental.analyze()
        wave:          Result from analysis.wave.analyze()

    Returns dict with keys:
        action, score, pnl_pct, pnl_usd, current_value,
        pnl_reason, technical_reason, fundamental_reason, wave_reason,
        target_price, stop_loss, hold_range, overall_summary
    """
    entry  = holding["entry_price"]
    qty    = holding["quantity"]

    pnl_usd     = (current_price - entry) * qty
    pnl_pct     = ((current_price - entry) / entry) * 100 if entry else 0
    current_val  = current_price * qty

    # ── Scoring: each factor contributes –2 to +2 ──────────────────────────
    score = 0
    reasons = {}

    # 1. P&L threshold
    pnl_reason, pnl_score = _pnl_reason(pnl_pct)
    score += pnl_score
    reasons["pnl"] = pnl_reason

    # 2. Technical signals
    tech_reason, tech_score = _technical_reason(tech)
    score += tech_score
    reasons["technical"] = tech_reason

    # 3. Fundamental valuation
    fund_reason, fund_score = _fundamental_reason(fund)
    score += fund_score
    reasons["fundamental"] = fund_reason

    # 4. Wave / price context
    wave_reason, wave_score = _wave_reason(wave)
    score += wave_score
    reasons["wave"] = wave_reason

    # ── Derive action ────────────────────────────────────────────────────────
    if score >= 4:
        action = "STRONG ADD"
    elif score >= 2:
        action = "ADD / HOLD"
    elif score >= -1:
        action = "HOLD"
    elif score >= -3:
        action = "CONSIDER SELLING"
    else:
        action = "SELL"

    # ── Price targets from support/resistance ────────────────────────────────
    sr = tech.get("support_resistance", {}) if tech else {}
    resistances = sr.get("resistance", [])
    supports    = sr.get("support", [])

    target_price = resistances[0] if resistances else round(current_price * 1.10, 2)
    stop_loss    = supports[0]    if supports    else round(current_price * 0.90, 2)
    hold_range   = (stop_loss, target_price)

    # ── Overall summary ──────────────────────────────────────────────────────
    summary = _overall_summary(action, pnl_pct, pnl_usd, score, target_price, stop_loss)

    return {
        "action":              action,
        "score":               score,
        "pnl_pct":             round(pnl_pct, 2),
        "pnl_usd":             round(pnl_usd, 2),
        "current_value":       round(current_val, 2),
        "pnl_reason":          reasons["pnl"],
        "technical_reason":    reasons["technical"],
        "fundamental_reason":  reasons["fundamental"],
        "wave_reason":         reasons["wave"],
        "target_price":        target_price,
        "stop_loss":           stop_loss,
        "hold_range":          hold_range,
        "overall_summary":     summary,
    }


# ── Factor helpers ─────────────────────────────────────────────────────────────

def _pnl_reason(pnl_pct: float) -> tuple[str, int]:
    if pnl_pct >= 40:
        return (
            f"Position is up {pnl_pct:.1f}% — substantial profit locked in. "
            "Strongly consider taking full or partial profits.",
            -2,
        )
    if pnl_pct >= 25:
        return (
            f"Position is up {pnl_pct:.1f}% — significant gain. "
            "Consider trimming to lock in profits while letting winners run.",
            -1,
        )
    if pnl_pct >= 5:
        return (
            f"Position is up {pnl_pct:.1f}% — healthy, within normal hold range.",
            +1,
        )
    if pnl_pct >= -5:
        return (
            f"Position is roughly flat ({pnl_pct:+.1f}%) — no urgency to act.",
            0,
        )
    if pnl_pct >= -15:
        return (
            f"Position is down {abs(pnl_pct):.1f}% — moderate drawdown. "
            "Review conviction before adding more.",
            -1,
        )
    return (
        f"Position is down {abs(pnl_pct):.1f}% — significant loss. "
        "Consider cutting the position to limit further downside.",
        -2,
    )


def _technical_reason(tech: dict) -> tuple[str, int]:
    if not tech or "error" in tech:
        return "Technical data unavailable.", 0

    signals = tech.get("signals", {})
    summary = tech.get("summary", {})
    ind     = tech.get("indicators", {})

    trend  = summary.get("trend", "Neutral / Mixed")
    bull_n = len(summary.get("bullish_signals", []))
    bear_n = len(summary.get("bearish_signals", []))

    rsi    = ind.get("rsi")
    macd   = ind.get("macd")
    macd_s = ind.get("macd_signal")

    parts = []

    # RSI comment
    if rsi is not None:
        if rsi > 70:
            parts.append(f"RSI is {rsi:.0f} (overbought) — momentum may be weakening")
        elif rsi < 30:
            parts.append(f"RSI is {rsi:.0f} (oversold) — potential bounce territory")
        else:
            parts.append(f"RSI is {rsi:.0f} (neutral zone)")

    # MACD comment
    if macd is not None and macd_s is not None:
        if macd > macd_s:
            parts.append("MACD is above signal line (bullish momentum)")
        else:
            parts.append("MACD has crossed below signal line (bearish divergence)")

    # Overall trend
    parts.append(f"Overall technical trend: {trend} ({bull_n} bullish vs {bear_n} bearish signals)")

    # Score
    if trend == "Bullish" and (rsi is None or rsi < 70):
        score = +2
    elif trend == "Bullish":
        score = +1
    elif trend == "Bearish" and (rsi is not None and rsi > 70):
        score = -2
    elif trend == "Bearish":
        score = -1
    else:
        score = 0

    return ". ".join(parts) + ".", score


def _fundamental_reason(fund: dict) -> tuple[str, int]:
    if not fund or "error" in fund:
        return "Fundamental data unavailable (may be intraday period or ETF).", 0

    overall = fund.get("summary", {}).get("overall", "Neutral")
    val     = fund.get("valuation", {})
    prof    = fund.get("profitability", {})

    parts = []

    pe_rating = val.get("rating", "")
    if pe_rating and pe_rating != "N/A":
        parts.append(f"Valuation is {pe_rating.lower()}")

    margin = prof.get("net_margin")
    if margin is not None:
        # net_margin is already a formatted percentage string from _pct()
        parts.append(f"Net margin {margin}")

    parts.append(f"Fundamental view: {overall}")

    if overall in ("Bullish", "Strong"):
        score = +2
    elif "Bullish" in overall or overall == "Moderate":
        score = +1
    elif overall in ("Bearish",):
        score = -2
    elif "Bearish" in overall:
        score = -1
    else:
        score = 0

    return ". ".join(parts) + ".", score


def _wave_reason(wave: dict) -> tuple[str, int]:
    if not wave or "error" in wave:
        return "Wave analysis unavailable.", 0

    trend   = wave.get("trend_phase", {})
    wave_e  = wave.get("wave_estimate", {})
    fib     = wave.get("fibonacci", {})

    primary = trend.get("primary", "Unknown")
    wave_pos = wave_e.get("position", "")
    confidence = wave_e.get("confidence", "Low")

    parts = []

    if primary != "Unknown":
        parts.append(f"Primary trend: {primary}")

    if wave_pos and confidence != "Low":
        parts.append(f"Elliott Wave estimate: {wave_pos} (confidence: {confidence})")
        # Late-stage warning
        if any(w in wave_pos for w in ("Wave 5", "Wave C", "wave 5", "wave C")):
            parts.append("Late-stage wave detected — reversal risk is elevated")

    nearest = fib.get("nearest_level") if fib else None
    if nearest:
        parts.append(f"Price near {nearest} Fibonacci retracement level")

    # Score
    if primary == "Uptrend" and "Wave 5" not in (wave_pos or ""):
        score = +1
    elif primary == "Uptrend" and "Wave 5" in (wave_pos or ""):
        score = -1
    elif primary == "Downtrend":
        score = -1
    else:
        score = 0

    text = ". ".join(parts) + "." if parts else "Insufficient data for wave context."
    return text, score


def _overall_summary(
    action: str,
    pnl_pct: float,
    pnl_usd: float,
    score: int,
    target: float,
    stop: float,
) -> str:
    direction = "profit" if pnl_usd >= 0 else "loss"
    pnl_str = f"${abs(pnl_usd):,.0f} unrealized {direction} ({pnl_pct:+.1f}%)"

    if action == "STRONG ADD":
        return (
            f"All indicators are aligned bullishly with {pnl_str}. "
            f"Consider adding to the position. "
            f"Upside target ${target:.2f}, protect below ${stop:.2f}."
        )
    if action == "ADD / HOLD":
        return (
            f"More signals are positive than negative. Current {pnl_str}. "
            f"Holding or adding on dips is reasonable. "
            f"Watch ${target:.2f} as next resistance, stop at ${stop:.2f}."
        )
    if action == "HOLD":
        return (
            f"Mixed signals with {pnl_str}. No strong reason to act — "
            f"maintain the position between ${stop:.2f} support and ${target:.2f} target."
        )
    if action == "CONSIDER SELLING":
        return (
            f"Several indicators are cautionary with {pnl_str}. "
            f"Consider reducing exposure or setting a tight stop at ${stop:.2f}. "
            f"A close below ${stop:.2f} would confirm further weakness."
        )
    return (
        f"Multiple factors are bearish with {pnl_str}. "
        f"Exiting the position is advisable to protect capital. "
        f"Next support at ${stop:.2f}; a bounce to ${target:.2f} could offer a better exit."
    )
