"""
Wave & trend analysis — Elliott Wave structure detection and market phase identification.

Note: True Elliott Wave labeling requires pattern-matching expertise and is
subjective even among professionals. This module uses a rule-based approach
to identify the likely wave phase and trend structure from price action.
"""

import pandas as pd
import numpy as np


def analyze(data: dict) -> dict:
    """
    Identify the current market phase and wave structure.

    Returns dict with:
        - trend_phase: overall trend direction and phase
        - wave_count: estimated Elliott Wave position
        - swing_points: detected highs/lows
        - fibonacci: key Fibonacci retracement levels
        - summary: plain-English interpretation
    """
    hist = data.get("history", pd.DataFrame())

    if hist.empty or len(hist) < 50:
        return {"error": "Not enough data for wave analysis."}

    df = hist.copy()
    df.columns = [c.lower() for c in df.columns]

    swings = _find_swings(df)
    trend = _identify_trend(df, swings)
    fib = _fibonacci_levels(df, swings)
    wave_est = _estimate_wave(df, swings, trend)
    chart_data = build_wave_chart_data(df, swings, trend, wave_est, fib)

    return {
        "trend_phase": trend,
        "wave_estimate": wave_est,
        "swing_points": swings,
        "fibonacci": fib,
        "summary": _summarize(trend, wave_est, fib),
        "chart_data": chart_data,
    }


# ── Swing Detection ────────────────────────────────────────────────────────────

def _find_swings(df: pd.DataFrame, order: int = 10) -> dict:
    """
    Find significant swing highs and lows using a rolling window.
    order = how many bars on each side must be lower/higher.
    """
    high = df["high"].values
    low = df["low"].values
    dates = df.index

    swing_highs = []
    swing_lows = []

    for i in range(order, len(df) - order):
        # Swing high: highest point in the window
        if high[i] == max(high[i - order:i + order + 1]):
            swing_highs.append({"date": dates[i], "price": round(high[i], 2), "idx": i})
        # Swing low: lowest point in the window
        if low[i] == min(low[i - order:i + order + 1]):
            swing_lows.append({"date": dates[i], "price": round(low[i], 2), "idx": i})

    return {
        "highs": swing_highs[-5:],  # Keep last 5 significant swings
        "lows": swing_lows[-5:],
    }


# ── Trend Identification ───────────────────────────────────────────────────────

def _identify_trend(df: pd.DataFrame, swings: dict) -> dict:
    """
    Identify the primary, intermediate, and short-term trend.
    Uses Dow Theory: higher highs + higher lows = uptrend.
    """
    close = df["close"]
    current = close.iloc[-1]

    # Long-term trend (200-day)
    sma200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else None
    sma50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else None
    sma20 = close.rolling(20).mean().iloc[-1] if len(close) >= 20 else None

    primary = "Uptrend" if (sma200 and current > sma200) else "Downtrend" if sma200 else "Unknown"
    intermediate = "Uptrend" if (sma50 and current > sma50) else "Downtrend" if sma50 else "Unknown"
    short_term = "Uptrend" if (sma20 and current > sma20) else "Downtrend" if sma20 else "Unknown"

    # Swing structure analysis (Dow Theory)
    swing_structure = _analyze_swing_structure(swings)

    # Phase detection
    phase = _detect_phase(primary, intermediate, short_term, swing_structure)

    return {
        "primary": primary,         # Long-term (months)
        "intermediate": intermediate,  # Medium-term (weeks)
        "short_term": short_term,   # Short-term (days)
        "swing_structure": swing_structure,
        "phase": phase,
        "current_price": round(current, 2),
        "sma_20": round(sma20, 2) if sma20 else None,
        "sma_50": round(sma50, 2) if sma50 else None,
        "sma_200": round(sma200, 2) if sma200 else None,
    }


def _analyze_swing_structure(swings: dict) -> str:
    """Check if swing highs and lows are rising or falling (Dow Theory)."""
    highs = [s["price"] for s in swings["highs"]]
    lows = [s["price"] for s in swings["lows"]]

    hh = len(highs) >= 2 and highs[-1] > highs[-2]  # Higher high
    hl = len(lows) >= 2 and lows[-1] > lows[-2]     # Higher low
    lh = len(highs) >= 2 and highs[-1] < highs[-2]  # Lower high
    ll = len(lows) >= 2 and lows[-1] < lows[-2]     # Lower low

    if hh and hl:
        return "Higher Highs & Higher Lows (Bullish)"
    elif lh and ll:
        return "Lower Highs & Lower Lows (Bearish)"
    elif hh and ll:
        return "Mixed Structure (Volatile)"
    elif lh and hl:
        return "Consolidation / Compression"
    else:
        return "Indeterminate"


def _detect_phase(primary: str, intermediate: str, short_term: str, swing: str) -> str:
    """
    Map trend alignment to a market phase name.
    Classic phases: Accumulation, Markup, Distribution, Markdown.
    """
    all_up = primary == "Uptrend" and intermediate == "Uptrend" and short_term == "Uptrend"
    all_down = primary == "Downtrend" and intermediate == "Downtrend" and short_term == "Downtrend"
    mixed_bullish = primary == "Uptrend" and intermediate == "Uptrend" and short_term == "Downtrend"
    mixed_bearish = primary == "Downtrend" and intermediate == "Downtrend" and short_term == "Uptrend"

    if all_up and "Bullish" in swing:
        return "Markup Phase — Strong uptrend across all timeframes"
    elif all_down and "Bearish" in swing:
        return "Markdown Phase — Strong downtrend across all timeframes"
    elif mixed_bullish:
        return "Pullback in Uptrend — Possible buying opportunity"
    elif mixed_bearish:
        return "Bounce in Downtrend — Possible short-selling opportunity"
    elif "Consolidation" in swing:
        return "Consolidation / Accumulation — Direction unclear"
    elif primary == "Uptrend":
        return "Uptrend (Mixed Signals) — Caution"
    elif primary == "Downtrend":
        return "Downtrend (Mixed Signals) — Caution"
    else:
        return "Uncertain — Insufficient data"


# ── Elliott Wave Estimation ────────────────────────────────────────────────────

def _estimate_wave(df: pd.DataFrame, swings: dict, trend: dict) -> dict:
    """
    Heuristic Elliott Wave position estimation.
    This is a simplified rule-based approximation, not a full EW model.

    In a bull market:
      Waves 1, 3, 5 = impulse (up)
      Waves 2, 4    = correction (down)
      Waves A, B, C = corrective sequence after wave 5

    We estimate based on how many alternating swings we can count.
    """
    highs = swings["highs"]
    lows = swings["lows"]
    primary = trend.get("primary", "Unknown")

    if len(highs) < 2 or len(lows) < 2:
        return {"position": "Insufficient swing data", "confidence": "Low"}

    # Count alternating swings (simplified)
    all_swings = sorted(highs + lows, key=lambda x: x["idx"])

    swing_directions = []
    for i in range(1, len(all_swings)):
        prev = all_swings[i - 1]
        curr = all_swings[i]
        if curr in highs:
            swing_directions.append("up")
        else:
            swing_directions.append("down")

    if not swing_directions:
        return {"position": "Cannot determine", "confidence": "Low"}

    # Last move direction
    last_move = swing_directions[-1]
    num_swings = len(swing_directions)

    # In an uptrend, try to place within 5-wave structure
    if primary == "Uptrend":
        if last_move == "up":
            if num_swings <= 2:
                position = "Wave 1 or 3 (Impulse up) — Early/mid uptrend"
            elif num_swings <= 4:
                position = "Wave 3 or 5 (Impulse up) — Mid/late uptrend"
            else:
                position = "Possible Wave 5 or Wave B — Late stage, watch for reversal"
        else:  # last move down
            if num_swings <= 2:
                position = "Wave 2 (Correction) — Pullback in early uptrend"
            elif num_swings <= 4:
                position = "Wave 4 (Correction) — Pullback before final wave 5"
            else:
                position = "Possible Wave A or C — Corrective phase, potential reversal zone"

    elif primary == "Downtrend":
        if last_move == "down":
            position = "Impulse wave down — Trend continuation likely"
        else:
            position = "Corrective bounce in downtrend — Watch for resumption"
    else:
        position = "Trend unclear — Wave count unreliable"

    return {
        "position": position,
        "last_swing_direction": last_move,
        "swing_count": num_swings,
        "confidence": "Medium" if num_swings >= 3 else "Low",
        "note": "Elliott Wave is inherently subjective. Use this as one signal among many.",
    }


# ── Fibonacci Retracement ──────────────────────────────────────────────────────

def _fibonacci_levels(df: pd.DataFrame, swings: dict) -> dict:
    """
    Calculate Fibonacci retracement levels from the most recent major swing.
    """
    highs = swings["highs"]
    lows = swings["lows"]

    if not highs or not lows:
        return {}

    last_high = max(highs, key=lambda x: x["idx"])
    last_low = min(lows, key=lambda x: x["idx"])

    # Determine direction of the most recent major move
    if last_high["idx"] > last_low["idx"]:
        # Most recent major move was UP: fib from low to high
        low_price = last_low["price"]
        high_price = last_high["price"]
        direction = "Upswing"
    else:
        # Most recent major move was DOWN: fib from high to low
        high_price = last_high["price"]
        low_price = last_low["price"]
        direction = "Downswing"

    diff = high_price - low_price
    levels = {
        "0.0%": round(low_price, 2),
        "23.6%": round(high_price - 0.236 * diff, 2),
        "38.2%": round(high_price - 0.382 * diff, 2),
        "50.0%": round(high_price - 0.500 * diff, 2),
        "61.8%": round(high_price - 0.618 * diff, 2),
        "78.6%": round(high_price - 0.786 * diff, 2),
        "100.0%": round(high_price, 2),
    }

    current_price = df["close"].iloc[-1]

    # Find closest fib level to current price
    closest = min(levels.items(), key=lambda x: abs(x[1] - current_price))

    return {
        "direction": direction,
        "swing_high": high_price,
        "swing_low": low_price,
        "levels": levels,
        "current_price": round(current_price, 2),
        "nearest_level": closest[0],
        "nearest_price": closest[1],
    }


# ── Summary ────────────────────────────────────────────────────────────────────

def _summarize(trend: dict, wave: dict, fib: dict) -> str:
    lines = []

    phase = trend.get("phase", "Unknown")
    lines.append(f"**Market Phase:** {phase}")

    primary = trend.get("primary", "")
    intermediate = trend.get("intermediate", "")
    short_term = trend.get("short_term", "")
    lines.append(f"**Trend Alignment:** Primary {primary} | Intermediate {intermediate} | Short-term {short_term}")

    swing_struct = trend.get("swing_structure", "")
    if swing_struct:
        lines.append(f"**Swing Structure:** {swing_struct}")

    wave_pos = wave.get("position", "")
    confidence = wave.get("confidence", "")
    if wave_pos:
        lines.append(f"**Elliott Wave Estimate:** {wave_pos} (Confidence: {confidence})")

    if fib and fib.get("nearest_level"):
        lines.append(f"**Fibonacci:** Price near {fib['nearest_level']} retracement (${fib['nearest_price']})")

    return "\n".join(lines)


# ── Wave Chart Data ────────────────────────────────────────────────────────────

def build_wave_chart_data(df: pd.DataFrame, swings: dict, trend: dict, wave_est: dict, fib: dict) -> dict | None:
    """
    Build data needed to draw an Elliott Wave chart with projections.

    Returns None if there isn't enough reliable data to draw the chart.

    Returns dict with:
        - applicable: bool
        - labeled_points: list of {date, price, label, is_high, color}
        - zigzag_x / zigzag_y: coordinates for the wave zigzag line
        - scenarios: list of {name, color, dash, points: [{date, price}], target_label}
        - confidence: str
    """
    highs = swings.get("highs", [])
    lows = swings.get("lows", [])
    confidence = wave_est.get("confidence", "Low")
    swing_count = wave_est.get("swing_count", 0)

    # Only draw when we have enough reliable swing data
    if swing_count < 3 or confidence == "Low" or (not highs and not lows):
        return {"applicable": False, "reason": "Insufficient swing data for wave chart"}

    primary = trend.get("primary", "Unknown")

    # Merge and sort all swings chronologically
    all_swings = []
    for h in highs:
        all_swings.append({**h, "is_high": True})
    for l in lows:
        all_swings.append({**l, "is_high": False})
    all_swings.sort(key=lambda x: x["idx"])

    # Remove consecutive same-type swings (keep the more extreme one)
    cleaned = []
    for s in all_swings:
        if cleaned and cleaned[-1]["is_high"] == s["is_high"]:
            # Keep the higher high or lower low
            if s["is_high"] and s["price"] > cleaned[-1]["price"]:
                cleaned[-1] = s
            elif not s["is_high"] and s["price"] < cleaned[-1]["price"]:
                cleaned[-1] = s
        else:
            cleaned.append(s)

    if len(cleaned) < 3:
        return {"applicable": False, "reason": "Not enough alternating swings"}

    # Label swings as Elliott Wave numbers
    # In uptrend: starts from a low (wave start), alternates up/down
    # In downtrend: starts from a high
    wave_labels_bull = ["1", "2", "3", "4", "5", "A", "B", "C"]
    wave_labels_bear = ["1", "2", "3", "4", "5", "A", "B", "C"]

    labeled = []
    label_colors_bull = {
        "1": "#60a5fa", "2": "#f87171", "3": "#4ade80",
        "4": "#f87171", "5": "#60a5fa", "A": "#fb923c",
        "B": "#a78bfa", "C": "#fb923c",
    }
    label_colors_bear = {
        "1": "#f87171", "2": "#60a5fa", "3": "#ef4444",
        "4": "#60a5fa", "5": "#f87171", "A": "#fb923c",
        "B": "#a78bfa", "C": "#fb923c",
    }

    # Use last 7 swings max (enough for 5-wave + ABC)
    display_swings = cleaned[-7:] if len(cleaned) > 7 else cleaned
    colors = label_colors_bull if primary == "Uptrend" else label_colors_bear
    labels = wave_labels_bull

    for i, s in enumerate(display_swings):
        lbl = labels[i] if i < len(labels) else "?"
        labeled.append({
            "date": s["date"],
            "price": s["price"],
            "label": lbl,
            "is_high": s["is_high"],
            "color": colors.get(lbl, "#94a3b8"),
        })

    # Zigzag coords
    zigzag_x = [p["date"] for p in labeled]
    zigzag_y = [p["price"] for p in labeled]

    # ── Project future scenarios ───────────────────────────────────────────────
    scenarios = _build_projections(df, labeled, primary, fib, swing_count)

    return {
        "applicable": True,
        "labeled_points": labeled,
        "zigzag_x": zigzag_x,
        "zigzag_y": zigzag_y,
        "scenarios": scenarios,
        "confidence": confidence,
        "swing_count": swing_count,
        "primary_trend": primary,
    }


def _build_projections(df: pd.DataFrame, labeled: list, primary: str, fib: dict, swing_count: int) -> list:
    """
    Build 2 projection scenarios extending from the last detected swing.

    Uses Fibonacci extensions to estimate price targets.
    """
    if len(labeled) < 2:
        return []

    last = labeled[-1]
    second_last = labeled[-2]

    last_date = last["date"]
    last_price = last["price"]
    prev_price = second_last["price"]

    # Estimate typical bar duration from df index
    if len(df) > 1:
        idx = df.index
        # Convert to timestamps for arithmetic
        try:
            delta = (idx[-1] - idx[-2])
            step_days = max(delta.days if hasattr(delta, 'days') else 1, 1)
        except Exception:
            step_days = 1
    else:
        step_days = 1

    def future_date(n_steps):
        try:
            return last_date + pd.Timedelta(days=step_days * n_steps)
        except Exception:
            return last_date

    # Height of the last completed wave leg
    leg_height = abs(last_price - prev_price)

    # Determine direction of the NEXT expected move
    # If last swing is a high → next move is down; if low → next move is up
    next_up = not last["is_high"]

    scenarios = []

    if next_up:
        # Bullish scenario: extend upward using 1.618x the last leg
        bull_target = round(last_price + leg_height * 1.618, 2)
        bull_mid = round(last_price + leg_height * 0.786, 2)
        scenarios.append({
            "name": "Bullish scenario",
            "color": "#4ade80",
            "dash": "dash",
            "points": [
                {"date": last_date, "price": last_price},
                {"date": future_date(10), "price": bull_mid},
                {"date": future_date(25), "price": bull_target},
            ],
            "target_label": f"Bull target ~${bull_target}",
        })
        # Conservative scenario: only 1.0x extension
        cons_target = round(last_price + leg_height * 1.0, 2)
        scenarios.append({
            "name": "Conservative scenario",
            "color": "#f59e0b",
            "dash": "dot",
            "points": [
                {"date": last_date, "price": last_price},
                {"date": future_date(10), "price": round(last_price + leg_height * 0.5, 2)},
                {"date": future_date(20), "price": cons_target},
            ],
            "target_label": f"Conservative ~${cons_target}",
        })
        # Bearish reversal scenario (if wave 5 or late stage)
        if any(p["label"] in ("5", "C") for p in labeled[-2:]):
            bear_target = round(last_price - leg_height * 0.618, 2)
            scenarios.append({
                "name": "Reversal scenario",
                "color": "#f87171",
                "dash": "dashdot",
                "points": [
                    {"date": last_date, "price": last_price},
                    {"date": future_date(8), "price": round(last_price + leg_height * 0.2, 2)},
                    {"date": future_date(20), "price": bear_target},
                ],
                "target_label": f"Reversal risk ~${bear_target}",
            })
    else:
        # Bearish/corrective scenario: pullback
        bear_target = round(last_price - leg_height * 0.618, 2)
        bear_deep = round(last_price - leg_height * 1.0, 2)
        scenarios.append({
            "name": "Correction scenario",
            "color": "#f87171",
            "dash": "dash",
            "points": [
                {"date": last_date, "price": last_price},
                {"date": future_date(10), "price": round(last_price - leg_height * 0.382, 2)},
                {"date": future_date(20), "price": bear_target},
            ],
            "target_label": f"Correction target ~${bear_target}",
        })
        # Bounce scenario after the pullback
        bounce_target = round(bear_target + leg_height * 1.618, 2)
        scenarios.append({
            "name": "Recovery scenario",
            "color": "#60a5fa",
            "dash": "dot",
            "points": [
                {"date": last_date, "price": last_price},
                {"date": future_date(8), "price": bear_target},
                {"date": future_date(25), "price": bounce_target},
            ],
            "target_label": f"Recovery target ~${bounce_target}",
        })
        # Deep correction scenario
        if primary == "Downtrend":
            deep_target = round(last_price - leg_height * 1.618, 2)
            scenarios.append({
                "name": "Deep correction",
                "color": "#ef4444",
                "dash": "dashdot",
                "points": [
                    {"date": last_date, "price": last_price},
                    {"date": future_date(15), "price": round(last_price - leg_height * 1.0, 2)},
                    {"date": future_date(30), "price": deep_target},
                ],
                "target_label": f"Deep correction ~${deep_target}",
            })

    return scenarios
