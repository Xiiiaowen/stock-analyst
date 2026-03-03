"""
Fundamental analysis — valuation, profitability, growth, financial health.
"""

import pandas as pd
from data.fetcher import get_safe


def analyze(data: dict) -> dict:
    """
    Compute fundamental metrics from fetched stock data.

    Returns a structured dict with ratings and values.
    """
    info = data.get("info", {})
    financials = data.get("financials", pd.DataFrame())
    balance = data.get("balance_sheet", pd.DataFrame())
    cashflow = data.get("cashflow", pd.DataFrame())

    result = {
        "valuation": _valuation(info),
        "profitability": _profitability(info, financials),
        "growth": _growth(financials),
        "financial_health": _financial_health(info, balance, cashflow),
        "dividends": _dividends(info),
        "summary": {},
    }

    result["summary"] = _summarize(result)
    return result


# ── Valuation ──────────────────────────────────────────────────────────────────

def _valuation(info: dict) -> dict:
    pe = get_safe(info, "trailingPE")
    fwd_pe = get_safe(info, "forwardPE")
    pb = get_safe(info, "priceToBook")
    ps = get_safe(info, "priceToSalesTrailing12Months")
    peg = get_safe(info, "pegRatio")
    ev_ebitda = get_safe(info, "enterpriseToEbitda")
    market_cap = get_safe(info, "marketCap")

    return {
        "trailing_pe": pe,
        "forward_pe": fwd_pe,
        "price_to_book": pb,
        "price_to_sales": ps,
        "peg_ratio": peg,
        "ev_to_ebitda": ev_ebitda,
        "market_cap": market_cap,
        "rating": _rate_valuation(pe, pb, peg),
    }


def _rate_valuation(pe, pb, peg) -> str:
    score = 0
    checks = 0

    if pe is not None:
        checks += 1
        if pe < 15:
            score += 2
        elif pe < 25:
            score += 1
        elif pe > 40:
            score -= 1

    if pb is not None:
        checks += 1
        if pb < 1.5:
            score += 2
        elif pb < 3:
            score += 1
        elif pb > 5:
            score -= 1

    if peg is not None:
        checks += 1
        if 0 < peg < 1:
            score += 2
        elif peg < 2:
            score += 1
        elif peg > 3:
            score -= 1

    if checks == 0:
        return "N/A"
    ratio = score / (checks * 2)
    if ratio >= 0.6:
        return "Undervalued"
    elif ratio >= 0.3:
        return "Fair Value"
    else:
        return "Overvalued"


# ── Profitability ──────────────────────────────────────────────────────────────

def _profitability(info: dict, financials: pd.DataFrame) -> dict:
    gross_margin = get_safe(info, "grossMargins")
    op_margin = get_safe(info, "operatingMargins")
    net_margin = get_safe(info, "profitMargins")
    roe = get_safe(info, "returnOnEquity")
    roa = get_safe(info, "returnOnAssets")
    ebitda = get_safe(info, "ebitda")

    return {
        "gross_margin": _pct(gross_margin),
        "operating_margin": _pct(op_margin),
        "net_margin": _pct(net_margin),
        "roe": _pct(roe),
        "roa": _pct(roa),
        "ebitda": ebitda,
        "rating": _rate_profitability(op_margin, net_margin, roe),
    }


def _rate_profitability(op_margin, net_margin, roe) -> str:
    score = 0
    checks = 0

    if op_margin is not None:
        checks += 1
        if op_margin > 0.20:
            score += 2
        elif op_margin > 0.10:
            score += 1
        elif op_margin < 0:
            score -= 1

    if net_margin is not None:
        checks += 1
        if net_margin > 0.15:
            score += 2
        elif net_margin > 0.05:
            score += 1
        elif net_margin < 0:
            score -= 1

    if roe is not None:
        checks += 1
        if roe > 0.20:
            score += 2
        elif roe > 0.10:
            score += 1
        elif roe < 0:
            score -= 1

    if checks == 0:
        return "N/A"
    ratio = score / (checks * 2)
    if ratio >= 0.6:
        return "Strong"
    elif ratio >= 0.3:
        return "Moderate"
    else:
        return "Weak"


# ── Growth ─────────────────────────────────────────────────────────────────────

def _growth(financials: pd.DataFrame) -> dict:
    if financials.empty or financials.shape[1] < 2:
        return {"revenue_yoy": None, "earnings_yoy": None, "rating": "N/A"}

    rev_growth = None
    earn_growth = None

    try:
        if "Total Revenue" in financials.index:
            rev = financials.loc["Total Revenue"]
            rev_growth = (rev.iloc[0] - rev.iloc[1]) / abs(rev.iloc[1]) if rev.iloc[1] != 0 else None
    except Exception:
        pass

    try:
        for label in ["Net Income", "Net Income Common Stockholders"]:
            if label in financials.index:
                earn = financials.loc[label]
                earn_growth = (earn.iloc[0] - earn.iloc[1]) / abs(earn.iloc[1]) if earn.iloc[1] != 0 else None
                break
    except Exception:
        pass

    return {
        "revenue_yoy": _pct(rev_growth),
        "earnings_yoy": _pct(earn_growth),
        "rating": _rate_growth(rev_growth, earn_growth),
    }


def _rate_growth(rev_growth, earn_growth) -> str:
    score = 0
    checks = 0
    for g in [rev_growth, earn_growth]:
        if g is not None:
            checks += 1
            if g > 0.20:
                score += 2
            elif g > 0.05:
                score += 1
            elif g < 0:
                score -= 1
    if checks == 0:
        return "N/A"
    ratio = score / (checks * 2)
    if ratio >= 0.6:
        return "High Growth"
    elif ratio >= 0.3:
        return "Moderate Growth"
    else:
        return "Declining"


# ── Financial Health ───────────────────────────────────────────────────────────

def _financial_health(info: dict, balance: pd.DataFrame, cashflow: pd.DataFrame) -> dict:
    current_ratio = get_safe(info, "currentRatio")
    quick_ratio = get_safe(info, "quickRatio")
    debt_to_equity = get_safe(info, "debtToEquity")
    total_cash = get_safe(info, "totalCash")
    total_debt = get_safe(info, "totalDebt")
    fcf = get_safe(info, "freeCashflow")

    return {
        "current_ratio": current_ratio,
        "quick_ratio": quick_ratio,
        "debt_to_equity": debt_to_equity,
        "total_cash": total_cash,
        "total_debt": total_debt,
        "free_cash_flow": fcf,
        "rating": _rate_health(current_ratio, debt_to_equity, fcf),
    }


def _rate_health(current_ratio, debt_to_equity, fcf) -> str:
    score = 0
    checks = 0

    if current_ratio is not None:
        checks += 1
        if current_ratio > 2:
            score += 2
        elif current_ratio > 1:
            score += 1
        else:
            score -= 1

    if debt_to_equity is not None:
        checks += 1
        if debt_to_equity < 50:
            score += 2
        elif debt_to_equity < 100:
            score += 1
        elif debt_to_equity > 200:
            score -= 1

    if fcf is not None:
        checks += 1
        if fcf > 0:
            score += 2
        else:
            score -= 1

    if checks == 0:
        return "N/A"
    ratio = score / (checks * 2)
    if ratio >= 0.6:
        return "Healthy"
    elif ratio >= 0.3:
        return "Moderate"
    else:
        return "Stressed"


# ── Dividends ─────────────────────────────────────────────────────────────────

def _dividends(info: dict) -> dict:
    yield_ = get_safe(info, "dividendYield")
    rate = get_safe(info, "dividendRate")
    payout = get_safe(info, "payoutRatio")
    ex_date = get_safe(info, "exDividendDate")

    return {
        "yield": _pct(yield_),
        "rate": rate,
        "payout_ratio": _pct(payout),
        "ex_date": ex_date,
        "pays_dividend": rate is not None and rate > 0,
    }


# ── Summary ────────────────────────────────────────────────────────────────────

def _summarize(result: dict) -> dict:
    ratings = {
        "Valuation": result["valuation"]["rating"],
        "Profitability": result["profitability"]["rating"],
        "Growth": result["growth"]["rating"],
        "Financial Health": result["financial_health"]["rating"],
    }

    positives = [k for k, v in ratings.items() if v in ("Undervalued", "Strong", "High Growth", "Healthy", "Fair Value", "Moderate Growth", "Moderate")]
    negatives = [k for k, v in ratings.items() if v in ("Overvalued", "Weak", "Declining", "Stressed")]

    return {
        "ratings": ratings,
        "positives": positives,
        "negatives": negatives,
        "overall": "Bullish" if len(positives) > len(negatives) else ("Bearish" if len(negatives) > len(positives) else "Neutral"),
    }


# ── Helpers ────────────────────────────────────────────────────────────────────

def _pct(val) -> str | None:
    if val is None:
        return None
    return f"{val * 100:.2f}%"
