"""
Report builder — synthesizes fundamental, technical, and wave analysis
into a structured, human-readable report.

When a Claude API key is provided, uses AI to write the narrative.
Otherwise falls back to rule-based text generation.
"""

import os
from data.fetcher import get_safe


def build(ticker: str, data: dict, fundamental: dict, technical: dict, wave: dict) -> dict:
    """
    Build a comprehensive analysis report.

    Returns dict with all sections, suitable for rendering in Streamlit.
    """
    info = data.get("info", {})
    news = data.get("news", [])

    company = _company_overview(ticker, info)
    verdict = _overall_verdict(fundamental, technical, wave)
    narrative = _generate_narrative(ticker, company, fundamental, technical, wave, verdict)
    risks = _identify_risks(fundamental, technical, wave, info)
    recent_news = _format_news(news)

    return {
        "ticker": ticker.upper(),
        "company": company,
        "verdict": verdict,
        "narrative": narrative,
        "risks": risks,
        "news": recent_news,
        "fundamental": fundamental,
        "technical": technical,
        "wave": wave,
    }


# ── Company Overview ───────────────────────────────────────────────────────────

def _company_overview(ticker: str, info: dict) -> dict:
    return {
        "name": get_safe(info, "longName", ticker),
        "sector": get_safe(info, "sector", "N/A"),
        "industry": get_safe(info, "industry", "N/A"),
        "country": get_safe(info, "country", "N/A"),
        "employees": get_safe(info, "fullTimeEmployees"),
        "website": get_safe(info, "website", ""),
        "description": get_safe(info, "longBusinessSummary", "No description available."),
        "current_price": get_safe(info, "currentPrice") or get_safe(info, "regularMarketPrice"),
        "currency": get_safe(info, "currency", "USD"),
        "exchange": get_safe(info, "exchange", ""),
        "52w_high": get_safe(info, "fiftyTwoWeekHigh"),
        "52w_low": get_safe(info, "fiftyTwoWeekLow"),
        "avg_volume": get_safe(info, "averageVolume"),
        "analyst_target": get_safe(info, "targetMeanPrice"),
        "analyst_rating": get_safe(info, "recommendationKey", "").replace("_", " ").title(),
    }


# ── Overall Verdict ────────────────────────────────────────────────────────────

def _overall_verdict(fundamental: dict, technical: dict, wave: dict) -> dict:
    """
    Aggregate signals from all three analysis layers into an overall verdict.
    Score: +1 bullish, -1 bearish, 0 neutral per signal.
    """
    scores = []

    # Fundamental signals
    fund_summary = fundamental.get("summary", {})
    overall = fund_summary.get("overall", "Neutral")
    if overall == "Bullish":
        scores.append(1)
    elif overall == "Bearish":
        scores.append(-1)
    else:
        scores.append(0)

    # Technical signals
    tech_summary = technical.get("summary", {})
    tech_trend = tech_summary.get("trend", "Neutral")
    if "Bullish" in tech_trend:
        scores.append(1)
    elif "Bearish" in tech_trend:
        scores.append(-1)
    else:
        scores.append(0)

    # Wave/trend signal
    trend_phase = wave.get("trend_phase", {})
    primary = trend_phase.get("primary", "Unknown")
    if primary == "Uptrend":
        scores.append(1)
    elif primary == "Downtrend":
        scores.append(-1)
    else:
        scores.append(0)

    total = sum(scores)
    if total >= 2:
        verdict = "Strong Buy"
        color = "green"
        emoji = "🟢"
    elif total == 1:
        verdict = "Buy"
        color = "lightgreen"
        emoji = "🟡"
    elif total == 0:
        verdict = "Hold / Neutral"
        color = "yellow"
        emoji = "⚪"
    elif total == -1:
        verdict = "Sell"
        color = "orange"
        emoji = "🟠"
    else:
        verdict = "Strong Sell"
        color = "red"
        emoji = "🔴"

    return {
        "label": verdict,
        "score": total,
        "color": color,
        "emoji": emoji,
        "fundamental": overall,
        "technical": tech_trend,
        "wave_primary": primary,
    }


# ── Narrative ──────────────────────────────────────────────────────────────────

def _generate_narrative(ticker, company, fundamental, technical, wave, verdict) -> dict:
    """
    Generate a plain-English analysis narrative.
    If ANTHROPIC_API_KEY is set, uses Claude for richer analysis.
    Otherwise uses rule-based text.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")

    if api_key:
        return _ai_narrative(ticker, company, fundamental, technical, wave, verdict, api_key)
    else:
        return _rule_based_narrative(ticker, company, fundamental, technical, wave, verdict)


def _rule_based_narrative(ticker, company, fundamental, technical, wave, verdict) -> dict:
    name = company.get("name", ticker)
    price = company.get("current_price")
    price_str = f"${price:.2f}" if price else "N/A"

    fund_summary = fundamental.get("summary", {})
    ratings = fund_summary.get("ratings", {})
    tech_summary = technical.get("summary", {})
    phase = wave.get("trend_phase", {}).get("phase", "Unknown")
    wave_pos = wave.get("wave_estimate", {}).get("position", "Unknown")
    fib = wave.get("fibonacci", {})

    # Fundamental paragraph
    fund_parts = []
    for area, rating in ratings.items():
        fund_parts.append(f"{area}: **{rating}**")
    fund_text = f"{name} ({ticker.upper()}) is currently trading at {price_str}. " \
                f"Fundamentally, the company shows {', '.join(fund_parts)}."

    # Technical paragraph
    bull_sigs = tech_summary.get("bullish_signals", [])
    bear_sigs = tech_summary.get("bearish_signals", [])
    tech_text = f"Technical indicators point to a **{tech_summary.get('trend', 'mixed')}** outlook. "
    if bull_sigs:
        tech_text += f"Bullish signals: {'; '.join(bull_sigs[:3])}. "
    if bear_sigs:
        tech_text += f"Bearish signals: {'; '.join(bear_sigs[:3])}."

    # Wave paragraph
    wave_text = f"From a trend and wave perspective, the stock is in the **{phase}**. "
    wave_text += f"Elliott Wave estimate suggests: {wave_pos}. "
    if fib and fib.get("nearest_level"):
        wave_text += f"Price is near the {fib['nearest_level']} Fibonacci level (${fib.get('nearest_price', '')})."

    # Bull / bear case
    positives = fund_summary.get("positives", [])
    negatives = fund_summary.get("negatives", [])

    bull_case = "; ".join(positives) if positives else "Fundamental data not strongly positive."
    bear_case = "; ".join(negatives) if negatives else "No major fundamental concerns detected."

    return {
        "fundamental": fund_text,
        "technical": tech_text,
        "wave": wave_text,
        "bull_case": bull_case,
        "bear_case": bear_case,
        "ai_powered": False,
    }


def _ai_narrative(ticker, company, fundamental, technical, wave, verdict, api_key) -> dict:
    """Use Claude API to generate a richer, more nuanced narrative."""
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)

        # Build a context summary for Claude
        context = _build_ai_context(ticker, company, fundamental, technical, wave, verdict)

        message = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=1500,
            messages=[{
                "role": "user",
                "content": f"""You are an expert financial analyst. Based on the following data, write a concise and insightful stock analysis report.

{context}

Write 4 sections:
1. **Fundamental Analysis** (2-3 sentences): Comment on valuation, profitability, growth, and financial health.
2. **Technical Analysis** (2-3 sentences): Comment on trend, momentum indicators, and key levels.
3. **Wave & Trend Analysis** (2-3 sentences): Comment on the market phase, Elliott Wave position, and Fibonacci levels.
4. **Bull Case / Bear Case** (2-3 bullet points each): Key reasons to be bullish or bearish.

Be direct, analytical, and specific. Avoid generic statements. Use data points from the context."""
            }]
        )

        # Parse Claude's response into sections
        text = message.content[0].text
        sections = _parse_ai_sections(text)
        sections["ai_powered"] = True
        return sections

    except Exception as e:
        # Fallback to rule-based on any error
        result = _rule_based_narrative(ticker, company, fundamental, technical, wave, verdict)
        result["ai_error"] = str(e)
        return result


def _build_ai_context(ticker, company, fundamental, technical, wave, verdict) -> str:
    """Build a text summary of all analysis data for Claude."""
    lines = [
        f"Stock: {company.get('name', ticker)} ({ticker.upper()})",
        f"Sector: {company.get('sector', 'N/A')} | Industry: {company.get('industry', 'N/A')}",
        f"Current Price: ${company.get('current_price', 'N/A')}",
        f"52-week range: ${company.get('52w_low', 'N/A')} - ${company.get('52w_high', 'N/A')}",
        f"Analyst consensus: {company.get('analyst_rating', 'N/A')} | Target: ${company.get('analyst_target', 'N/A')}",
        "",
        "FUNDAMENTAL METRICS:",
    ]

    val = fundamental.get("valuation", {})
    lines += [
        f"  P/E (trailing): {val.get('trailing_pe', 'N/A')}",
        f"  P/E (forward): {val.get('forward_pe', 'N/A')}",
        f"  Price/Book: {val.get('price_to_book', 'N/A')}",
        f"  PEG Ratio: {val.get('peg_ratio', 'N/A')}",
        f"  Valuation rating: {val.get('rating', 'N/A')}",
    ]

    prof = fundamental.get("profitability", {})
    lines += [
        f"  Gross Margin: {prof.get('gross_margin', 'N/A')}",
        f"  Operating Margin: {prof.get('operating_margin', 'N/A')}",
        f"  Net Margin: {prof.get('net_margin', 'N/A')}",
        f"  ROE: {prof.get('roe', 'N/A')}",
        f"  Profitability rating: {prof.get('rating', 'N/A')}",
    ]

    growth = fundamental.get("growth", {})
    lines += [
        f"  Revenue YoY growth: {growth.get('revenue_yoy', 'N/A')}",
        f"  Earnings YoY growth: {growth.get('earnings_yoy', 'N/A')}",
        f"  Growth rating: {growth.get('rating', 'N/A')}",
    ]

    health = fundamental.get("financial_health", {})
    lines += [
        f"  Current Ratio: {health.get('current_ratio', 'N/A')}",
        f"  Debt/Equity: {health.get('debt_to_equity', 'N/A')}",
        f"  Free Cash Flow: {health.get('free_cash_flow', 'N/A')}",
        f"  Health rating: {health.get('rating', 'N/A')}",
        "",
        "TECHNICAL SIGNALS:",
    ]

    tech_summary = technical.get("summary", {})
    lines.append(f"  Overall trend: {tech_summary.get('trend', 'N/A')}")
    for sig in tech_summary.get("bullish_signals", []):
        lines.append(f"  [BULL] {sig}")
    for sig in tech_summary.get("bearish_signals", []):
        lines.append(f"  [BEAR] {sig}")

    sr = technical.get("support_resistance", {})
    if sr:
        lines.append(f"  Support: {sr.get('support', [])}")
        lines.append(f"  Resistance: {sr.get('resistance', [])}")

    lines += ["", "WAVE & TREND:"]
    trend = wave.get("trend_phase", {})
    lines.append(f"  Phase: {trend.get('phase', 'N/A')}")
    lines.append(f"  Primary trend: {trend.get('primary', 'N/A')}")
    lines.append(f"  Swing structure: {trend.get('swing_structure', 'N/A')}")

    wave_est = wave.get("wave_estimate", {})
    lines.append(f"  Elliott Wave position: {wave_est.get('position', 'N/A')}")

    fib = wave.get("fibonacci", {})
    if fib:
        lines.append(f"  Nearest Fibonacci level: {fib.get('nearest_level', 'N/A')} at ${fib.get('nearest_price', 'N/A')}")

    lines += ["", f"OVERALL VERDICT: {verdict.get('label', 'N/A')} (score: {verdict.get('score', 0)})"]

    return "\n".join(lines)


def _parse_ai_sections(text: str) -> dict:
    """Extract sections from Claude's markdown response."""
    sections = {
        "fundamental": "",
        "technical": "",
        "wave": "",
        "bull_case": "",
        "bear_case": "",
    }

    # Simple section extraction
    lines = text.split("\n")
    current_section = None
    buffer = []

    for line in lines:
        lower = line.lower()
        if "fundamental" in lower and "**" in line:
            if current_section and buffer:
                sections[current_section] = "\n".join(buffer).strip()
            current_section = "fundamental"
            buffer = []
        elif "technical" in lower and "**" in line:
            if current_section and buffer:
                sections[current_section] = "\n".join(buffer).strip()
            current_section = "technical"
            buffer = []
        elif ("wave" in lower or "trend" in lower) and "**" in line:
            if current_section and buffer:
                sections[current_section] = "\n".join(buffer).strip()
            current_section = "wave"
            buffer = []
        elif "bull" in lower and "**" in line:
            if current_section and buffer:
                sections[current_section] = "\n".join(buffer).strip()
            current_section = "bull_case"
            buffer = []
        elif "bear" in lower and "**" in line:
            if current_section and buffer:
                sections[current_section] = "\n".join(buffer).strip()
            current_section = "bear_case"
            buffer = []
        elif current_section:
            buffer.append(line)

    if current_section and buffer:
        sections[current_section] = "\n".join(buffer).strip()

    # Fallback: if parsing failed, put everything in fundamental
    if not any(sections.values()):
        sections["fundamental"] = text

    return sections


# ── Risks ──────────────────────────────────────────────────────────────────────

def _identify_risks(fundamental, technical, wave, info) -> list[str]:
    risks = []

    # Fundamental risks
    fund_summary = fundamental.get("summary", {})
    for neg in fund_summary.get("negatives", []):
        risks.append(f"Fundamental: {neg} shows weakness")

    # Technical risks
    tech_summary = technical.get("summary", {})
    for sig in tech_summary.get("bearish_signals", [])[:3]:
        risks.append(f"Technical: {sig}")

    # Debt risk
    health = fundamental.get("financial_health", {})
    de = health.get("debt_to_equity")
    if de and isinstance(de, (int, float)) and de > 200:
        risks.append(f"High debt-to-equity ratio ({de:.0f}%)")

    # Valuation risk
    val = fundamental.get("valuation", {})
    if val.get("rating") == "Overvalued":
        risks.append("Stock appears overvalued based on P/E and P/B ratios")

    # Wave risks
    wave_est = wave.get("wave_estimate", {})
    pos = wave_est.get("position", "")
    if "wave 5" in pos.lower() or "late" in pos.lower():
        risks.append("Elliott Wave suggests potential late-stage move — watch for reversal")

    # Beta / volatility
    beta = get_safe(info, "beta")
    if beta and beta > 1.5:
        risks.append(f"High beta ({beta:.2f}) — stock is significantly more volatile than the market")

    if not risks:
        risks.append("No major risk flags detected — but always conduct your own due diligence.")

    return risks


# ── News ───────────────────────────────────────────────────────────────────────

def _format_news(news: list) -> list[dict]:
    formatted = []
    for item in news[:8]:  # Show max 8 articles
        formatted.append({
            "title": item.get("title", ""),
            "publisher": item.get("publisher", ""),
            "link": item.get("link", ""),
            "time": item.get("providerPublishTime", 0),
        })
    return formatted
