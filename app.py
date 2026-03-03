"""
Stock Analyst — main Streamlit application.

Run with:
    streamlit run app.py
"""

import os
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime
import yfinance as yf

from data.fetcher import fetch_stock_data
from data.portfolio_db import init_db, get_holdings, add_holding, delete_holding
from analysis import fundamental, technical, wave
from analysis.portfolio import generate_recommendation
from report import builder

# ── Page Config ────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="XW Stock Analyst",
    page_icon="💹",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global Styles (light, professional) ────────────────────────────────────────

st.markdown("""
<style>
    /* ── Base ─────────────────────────────── */
    .stApp {
        background-color: #f8fafc;
        font-family: "Inter", "Segoe UI", sans-serif;
    }

    /* ── Sidebar ──────────────────────────── */
    section[data-testid="stSidebar"] {
        background: #ffffff;
        border-right: 1px solid #e2e8f0;
    }
    section[data-testid="stSidebar"] .stMarkdown p {
        color: #64748b;
        font-size: 0.82em;
    }

    /* ── Sidebar nav radio ────────────────── */
    div[data-testid="stRadio"] > label { display: none; }
    div[data-testid="stRadio"] div[role="radiogroup"] {
        gap: 4px;
    }
    div[data-testid="stRadio"] label[data-testid="stWidgetLabel"] {
        display: none;
    }
    div[data-testid="stRadio"] div[data-baseweb="radio"] label {
        padding: 8px 12px;
        border-radius: 8px;
        font-weight: 600;
        font-size: 0.95em;
        color: #475569;
        transition: background 0.15s;
    }
    div[data-testid="stRadio"] div[data-baseweb="radio"] label:hover {
        background: #f1f5f9;
    }

    /* ── Headings ─────────────────────────── */
    h1 { font-size: 1.7em !important; font-weight: 700; color: #0f172a; }
    h2 { font-size: 1.2em !important; font-weight: 600; color: #1e293b; }
    h3 { font-size: 1.05em !important; font-weight: 600; color: #334155; }

    /* ── Metric cards ─────────────────────── */
    [data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 14px 16px;
        box-shadow: 0 1px 3px rgba(15,23,42,0.06);
    }
    [data-testid="stMetricLabel"] { color: #64748b; font-size: 0.78em; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; }
    [data-testid="stMetricValue"] { color: #0f172a; font-weight: 700; font-size: clamp(0.85rem, 1.5vw, 1.15rem) !important; }

    /* ── Tabs ─────────────────────────────── */
    button[data-baseweb="tab"] {
        font-weight: 600;
        font-size: 0.88em;
        color: #64748b;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #2563eb;
        border-bottom-color: #2563eb;
    }

    /* ── Verdict box ──────────────────────── */
    .verdict-box {
        text-align: center;
        padding: 18px 22px;
        border-radius: 12px;
        font-size: 1.2em;
        font-weight: 700;
        margin: 4px 0;
        line-height: 1.4;
    }

    /* ── Signal labels ────────────────────── */
    .signal-bull   { color: #16a34a; font-weight: 500; }
    .signal-bear   { color: #dc2626; font-weight: 500; }
    .signal-neutral{ color: #64748b; font-weight: 500; }

    /* ── Card container ───────────────────── */
    .info-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 16px;
        box-shadow: 0 1px 3px rgba(15,23,42,0.06);
    }

    /* ── Divider ──────────────────────────── */
    hr { border-color: #e2e8f0; margin: 20px 0; }

    /* ── Portfolio action badges ──────────── */
    .badge-add    { background:#eff6ff; color:#2563eb; border:1px solid #bfdbfe; border-radius:6px; padding:3px 10px; font-weight:700; font-size:0.83em; white-space:nowrap; }
    .badge-hold   { background:#f0fdf4; color:#16a34a; border:1px solid #bbf7d0; border-radius:6px; padding:3px 10px; font-weight:700; font-size:0.83em; white-space:nowrap; }
    .badge-sell   { background:#fef2f2; color:#dc2626; border:1px solid #fecaca; border-radius:6px; padding:3px 10px; font-weight:700; font-size:0.83em; white-space:nowrap; }
    .badge-warn   { background:#fffbeb; color:#d97706; border:1px solid #fde68a; border-radius:6px; padding:3px 10px; font-weight:700; font-size:0.83em; white-space:nowrap; }

    /* ── Reason sections ──────────────────── */
    .reason-block {
        background: #f8fafc;
        border-left: 3px solid #e2e8f0;
        border-radius: 0 8px 8px 0;
        padding: 10px 14px;
        margin: 8px 0;
        font-size: 0.9em;
        color: #334155;
        line-height: 1.6;
    }
    .reason-block.tech  { border-left-color: #3b82f6; }
    .reason-block.fund  { border-left-color: #8b5cf6; }
    .reason-block.wave  { border-left-color: #06b6d4; }
    .reason-block.pnl   { border-left-color: #f59e0b; }

    /* ── Portfolio holdings row ───────────── */
    .holding-row {
        display: flex;
        align-items: center;
        padding: 14px 18px;
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        margin-bottom: 8px;
        box-shadow: 0 1px 3px rgba(15,23,42,0.04);
    }
    .pnl-gain { color: #16a34a; font-weight: 700; font-size: 1.05em; }
    .pnl-loss { color: #dc2626; font-weight: 700; font-size: 1.05em; }
    .col-label {
        color: #64748b;
        font-size: 0.72em;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 2px;
    }

    /* ── Plotly chart containers: always fill width ── */
    .stPlotlyChart {
        width: 100% !important;
    }
    .stPlotlyChart > div,
    .stPlotlyChart iframe {
        width: 100% !important;
    }

    /* ── Main content: constrain max-width and padding ── */
    .main .block-container {
        max-width: 100% !important;
        padding-left: 1.5rem !important;
        padding-right: 1.5rem !important;
        padding-top: 1rem !important;
    }

    /* ── Mobile / small viewport (phones ≤ 640px) ──────── */
    @media (max-width: 640px) {
        h1 { font-size: 1.3em !important; }
        h2 { font-size: 1.05em !important; }
        h3 { font-size: 0.95em !important; }

        .main .block-container {
            padding-left: 0.75rem !important;
            padding-right: 0.75rem !important;
        }

        /* Metric cards: smaller padding on mobile */
        [data-testid="stMetric"] {
            padding: 10px 12px;
        }
        [data-testid="stMetricLabel"] { font-size: 0.7em; }

        /* Verdict box: smaller on mobile */
        .verdict-box {
            font-size: 0.95em;
            padding: 12px 14px;
        }

        /* Tabs: smaller text */
        button[data-baseweb="tab"] {
            font-size: 0.78em;
            padding: 6px 8px;
        }

        /* Badge text on mobile */
        .badge-add, .badge-hold, .badge-sell, .badge-warn {
            font-size: 0.72em;
            padding: 2px 7px;
        }

        /* Reason blocks */
        .reason-block { font-size: 0.82em; }
    }

    /* ── Tablet (641px – 1024px) ────────────────────── */
    @media (min-width: 641px) and (max-width: 1024px) {
        .main .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        h1 { font-size: 1.5em !important; }
    }
</style>
""", unsafe_allow_html=True)

# ── Color palette ──────────────────────────────────────────────────────────────

C_BUY    = "#16a34a"
C_SELL   = "#dc2626"
C_BLUE   = "#2563eb"
C_AMBER  = "#d97706"
C_VIOLET = "#7c3aed"
C_PINK   = "#db2777"
C_SLATE  = "#94a3b8"
C_GRID   = "#f1f5f9"


def _chart_layout(fig, height=460, right_margin=80):
    fig.update_layout(
        height=height,
        autosize=True,
        template="plotly_white",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    font=dict(size=11, color="#475569")),
        margin=dict(l=0, r=right_margin, t=10, b=0),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font=dict(color="#334155", size=12),
        xaxis_rangeslider_visible=False,
    )
    fig.update_xaxes(gridcolor=C_GRID, linecolor="#e2e8f0", showgrid=True)
    fig.update_yaxes(gridcolor=C_GRID, linecolor="#e2e8f0", showgrid=True)


# ── Cached data loading ────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def load_data(ticker: str, period: str) -> dict:
    return fetch_stock_data(ticker, period=period)


@st.cache_data(ttl=300, show_spinner=False)
def run_analysis(ticker: str, period: str) -> tuple:
    data = load_data(ticker, period)
    if data["history"].empty:
        return data, None, None, None, None
    fund   = fundamental.analyze(data)
    tech   = technical.analyze(data)
    wav    = wave.analyze(data)
    rep    = builder.build(ticker, data, fund, tech, wav)
    return data, fund, tech, wav, rep


@st.cache_data(ttl=120, show_spinner=False)
def get_current_price(ticker: str) -> float | None:
    """
    Lightweight direct price lookup using yfinance fast_info.
    Used as a final fallback when run_analysis can't surface a price
    (e.g. OTC stocks with no 1y history but a live quote).
    """
    try:
        fi = yf.Ticker(ticker).fast_info
        for attr in ("last_price", "previous_close", "regular_market_previous_close"):
            try:
                val = getattr(fi, attr, None)
                if val:
                    return float(val)
            except Exception:
                continue
    except Exception:
        pass
    return None


# ── Init DB ────────────────────────────────────────────────────────────────────

init_db()

# ── Sidebar ────────────────────────────────────────────────────────────────────

PERIOD_OPTIONS = ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "max"]
PERIOD_LABELS  = {
    "1d": "1 Day", "5d": "5 Days", "1mo": "1 Month", "3mo": "3 Months",
    "6mo": "6 Months", "1y": "1 Year", "2y": "2 Years",
    "5y": "5 Years", "10y": "10 Years", "max": "Max",
}

ticker_input = "AAPL"
period       = "1y"

with st.sidebar:
    st.markdown("""
<div style="display:flex;align-items:center;gap:12px;padding:6px 0 18px 0">
  <svg width="52" height="52" viewBox="0 0 52 52" xmlns="http://www.w3.org/2000/svg">
    <rect x="0" y="0" width="52" height="52" rx="13" fill="#0f172a"/>
    <text x="26" y="20" text-anchor="middle"
          font-family="Georgia,'Times New Roman',serif"
          font-size="14" font-weight="700" fill="#f8fafc" letter-spacing="1.5">XW</text>
    <line x1="9" y1="25" x2="43" y2="25" stroke="#1e293b" stroke-width="0.8"/>
    <polygon points="9,45 16,39 23,42 33,32 43,27 43,45"
             fill="#2563eb" fill-opacity="0.12"/>
    <polyline points="9,45 16,39 23,42 33,32 43,27"
              stroke="#2563eb" stroke-width="2.2" fill="none"
              stroke-linecap="round" stroke-linejoin="round"/>
    <circle cx="43" cy="27" r="2.6" fill="#2563eb"/>
  </svg>
  <div>
    <div style="font-size:1.1em;font-weight:800;color:#0f172a;letter-spacing:-0.4px;line-height:1.2">
      Stock Analyst
    </div>
    <div style="font-size:0.68em;font-weight:700;color:#2563eb;letter-spacing:1.3px;text-transform:uppercase;margin-top:2px">
      XW &middot; Personal
    </div>
  </div>
</div>
""", unsafe_allow_html=True)
    st.markdown("---")

    view = st.radio(
        "Navigation",
        options=["📈  Stock Analysis", "💼  My Portfolio"],
        label_visibility="collapsed",
    )

    st.markdown("---")

    if view == "📈  Stock Analysis":
        ticker_input = st.text_input(
            "Stock Ticker",
            value="AAPL",
            placeholder="e.g. AAPL, TSLA, NVDA",
            help="Enter a valid stock ticker symbol — updates automatically",
        ).strip().upper()

        period = st.select_slider(
            "Time Period",
            options=PERIOD_OPTIONS,
            value="1y",
            format_func=lambda x: PERIOD_LABELS[x],
        )

        st.markdown("---")

        api_key = st.text_input(
            "Anthropic API Key (optional)",
            type="password",
            placeholder="sk-ant-...",
            help="Enables AI-powered narrative in the Full Report tab",
        )
        if api_key:
            os.environ["ANTHROPIC_API_KEY"] = api_key

        st.markdown("---")
        st.caption("Data from Yahoo Finance · Auto-refreshes every 5 min")
        st.caption("Add Claude API key for AI-powered narrative")
    else:
        st.caption("Data from Yahoo Finance · Auto-refreshes every 5 min")


# ══════════════════════════════════════════════════════════════════════════════
# ── MY PORTFOLIO VIEW ─────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

if view == "💼  My Portfolio":

    st.markdown("# 💼 My Portfolio")

    # ── Add position form ──────────────────────────────────────────────────────
    with st.expander("➕  Add New Position", expanded=False):
        with st.form("add_holding_form", clear_on_submit=True):
            fc1, fc2, fc3 = st.columns(3)
            new_ticker = fc1.text_input("Ticker", placeholder="e.g. AAPL").strip().upper()
            new_entry  = fc2.number_input("Entry Price ($)", min_value=0.01, step=0.01, format="%.2f")
            new_qty    = fc3.number_input("Quantity (shares)", min_value=0.001, step=1.0, format="%.4f")

            fd1, fd2 = st.columns(2)
            new_date  = fd1.date_input("Entry Date (optional)", value=None)
            new_notes = fd2.text_input("Notes (optional)", placeholder="e.g. Long-term hold")

            submitted = st.form_submit_button("Add to Portfolio", type="primary")
            if submitted:
                if not new_ticker:
                    st.error("Ticker is required.")
                else:
                    add_holding(
                        ticker=new_ticker,
                        entry_price=float(new_entry),
                        quantity=float(new_qty),
                        entry_date=str(new_date) if new_date else None,
                        notes=new_notes or None,
                    )
                    st.success(f"Added {new_ticker} · {new_qty:g} shares @ ${new_entry:.2f}")
                    st.rerun()

    st.markdown("---")

    # ── Load holdings ──────────────────────────────────────────────────────────
    holdings = get_holdings()

    if not holdings:
        st.markdown(
            '<div style="text-align:center;padding:60px 20px;color:#94a3b8">'
            '<p style="font-size:2.5em;margin-bottom:8px">📂</p>'
            '<p style="font-size:1.2em;font-weight:600;color:#64748b;margin-bottom:6px">No positions yet</p>'
            '<p>Use the form above to add your first holding.</p>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        # ── Fetch data for all holdings ────────────────────────────────────────
        loaded      = []
        total_value = 0.0
        total_cost  = 0.0

        with st.spinner("Refreshing portfolio data…"):
            for h in holdings:
                cur_p = None
                _d = _f = _t = _w = _r = None
                try:
                    _d, _f, _t, _w, _r = run_analysis(h["ticker"], "1y")
                    # Primary: price from the built report's company dict
                    if _r:
                        cur_p = _r["company"].get("current_price")
                    # Fallback 1: pull directly from yfinance info dict
                    if cur_p is None and _d:
                        info = _d.get("info", {})
                        cur_p = info.get("currentPrice") or info.get("regularMarketPrice")
                    # Fallback 2: last closing bar in history
                    if cur_p is None and _d and not _d["history"].empty:
                        hist_df = _d["history"]
                        close_col = "Close" if "Close" in hist_df.columns else "close"
                        if close_col in hist_df.columns:
                            cur_p = float(hist_df[close_col].iloc[-1])
                except Exception:
                    pass

                # Fallback 3: direct fast_info lookup (works for OTC / low-data stocks)
                if cur_p is None:
                    cur_p = get_current_price(h["ticker"])

                rec = None
                if cur_p:
                    total_value += cur_p * h["quantity"]
                    total_cost  += h["entry_price"] * h["quantity"]
                    try:
                        rec = generate_recommendation(h, cur_p, _t, _f, _w)
                    except Exception:
                        pass

                loaded.append((h, cur_p, rec))

        total_pnl     = total_value - total_cost
        total_pnl_pct = (total_pnl / total_cost * 100) if total_cost else 0

        # ── Summary strip ──────────────────────────────────────────────────────
        sm1, sm2, sm3, sm4 = st.columns(4)
        sm1.metric("Portfolio Value",  f"${total_value:,.2f}")
        sm2.metric("Total Cost Basis", f"${total_cost:,.2f}")
        sm3.metric(
            "Unrealized P&L",
            f"${total_pnl:+,.2f}",
            f"{total_pnl_pct:+.2f}%",
        )
        sm4.metric("Open Positions", str(len(holdings)))

        st.markdown("---")

        # ── Holdings list header ───────────────────────────────────────────────
        st.markdown("### Holdings")

        _lbl = '<p class="col-label">{}</p>'
        hc = st.columns([2, 1.2, 1.8, 1.6, 1.6, 1.6, 2])
        hc[0].markdown(_lbl.format("Ticker"), unsafe_allow_html=True)
        hc[1].markdown(_lbl.format("Shares"), unsafe_allow_html=True)
        hc[2].markdown(_lbl.format("Entry → Current"), unsafe_allow_html=True)
        hc[3].markdown(_lbl.format("P&L ($)"), unsafe_allow_html=True)
        hc[4].markdown(_lbl.format("P&L (%)"), unsafe_allow_html=True)
        hc[5].markdown(_lbl.format("Mkt Value"), unsafe_allow_html=True)
        hc[6].markdown(_lbl.format("Action"), unsafe_allow_html=True)

        st.markdown('<hr style="border-color:#e2e8f0;margin:6px 0 12px 0">', unsafe_allow_html=True)

        # ── Per-holding rows ───────────────────────────────────────────────────
        for h, cur_p, rec in loaded:
            if rec:
                pnl_pct = rec["pnl_pct"]
                pnl_usd = rec["pnl_usd"]
                cur_val = rec["current_value"]
                action  = rec["action"]
            elif cur_p:
                # rec failed but we have a price — compute basic P/L directly
                pnl_usd = round((cur_p - h["entry_price"]) * h["quantity"], 2)
                pnl_pct = round(((cur_p - h["entry_price"]) / h["entry_price"]) * 100, 2) if h["entry_price"] else 0.0
                cur_val = round(cur_p * h["quantity"], 2)
                action  = "—"
            else:
                pnl_pct = 0.0
                pnl_usd = 0.0
                cur_val = 0.0
                action  = "—"

            pnl_color = C_BUY if pnl_pct >= 0 else C_SELL
            pnl_arrow = "▲" if pnl_pct >= 0 else "▼"

            if "ADD" in action:
                badge_cls = "badge-add"
            elif "SELL" in action:
                badge_cls = "badge-sell"
            elif "CONSIDER" in action:
                badge_cls = "badge-warn"
            else:
                badge_cls = "badge-hold"

            # Summary row (always visible)
            rc = st.columns([2, 1.2, 1.8, 1.6, 1.6, 1.6, 2])

            rc[0].markdown(f"**{h['ticker']}**")
            rc[1].markdown(f"{h['quantity']:g}")
            cur_p_str = f"&#36;{cur_p:,.2f}" if cur_p else "N/A"
            rc[2].markdown(
                f'<span style="color:#64748b">&#36;{h["entry_price"]:.2f}</span>'
                f' &rarr; '
                f'<span style="font-weight:600;color:#0f172a">{cur_p_str}</span>',
                unsafe_allow_html=True,
            )
            rc[3].markdown(
                f'<span style="color:{pnl_color};font-weight:700">'
                f'{pnl_arrow} &#36;{abs(pnl_usd):,.2f}</span>',
                unsafe_allow_html=True,
            )
            rc[4].markdown(
                f'<span style="color:{pnl_color};font-weight:700">'
                f'{pnl_pct:+.1f}%</span>',
                unsafe_allow_html=True,
            )
            rc[5].markdown(f"${cur_val:,.2f}" if cur_val else "—")
            rc[6].markdown(
                f'<span class="{badge_cls}">{action}</span>',
                unsafe_allow_html=True,
            )

            # Analysis detail expander
            with st.expander(f"Analysis details — {h['ticker']}", expanded=False):
                if rec:
                    dm1, dm2, dm3, dm4 = st.columns(4)
                    dm1.metric("Entry Price",    f"${h['entry_price']:.2f}")
                    dm2.metric("Current Price",  f"${cur_p:,.2f}" if cur_p else "N/A")
                    dm3.metric("Unrealized P&L", f"${pnl_usd:+,.2f}")
                    dm4.metric("Market Value",   f"${cur_val:,.2f}")

                    st.markdown("**Analysis breakdown:**")
                    st.markdown(
                        f'<div class="reason-block pnl">'
                        f'<strong>💰 P&L context:</strong> {rec["pnl_reason"]}'
                        f'</div>', unsafe_allow_html=True)
                    st.markdown(
                        f'<div class="reason-block tech">'
                        f'<strong>📊 Technically:</strong> {rec["technical_reason"]}'
                        f'</div>', unsafe_allow_html=True)
                    st.markdown(
                        f'<div class="reason-block fund">'
                        f'<strong>📈 Fundamentally:</strong> {rec["fundamental_reason"]}'
                        f'</div>', unsafe_allow_html=True)
                    st.markdown(
                        f'<div class="reason-block wave">'
                        f'<strong>🌊 Wave context:</strong> {rec["wave_reason"]}'
                        f'</div>', unsafe_allow_html=True)

                    st.markdown("---")
                    t1, t2, t3 = st.columns(3)
                    t1.metric("Stop-Loss",   f"${rec['stop_loss']:,.2f}")
                    t2.metric("Hold Range",  f"${rec['hold_range'][0]:,.2f} – ${rec['hold_range'][1]:,.2f}")
                    t3.metric("Sell Target", f"${rec['target_price']:,.2f}")

                    st.markdown(
                        f'<div class="info-card" style="padding:14px 18px;margin-top:12px">'
                        f'<strong>Overall:</strong> {rec["overall_summary"].replace("$", "&#36;")}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.warning("Could not retrieve current data for this position.")

                meta_row = []
                if h.get("entry_date"):
                    meta_row.append(f"📅 Entry date: {h['entry_date']}")
                if h.get("notes"):
                    meta_row.append(f"📝 {h['notes']}")
                if meta_row:
                    st.caption("  ·  ".join(meta_row))

                st.markdown("")
                if st.button("🗑 Remove position", key=f"del_{h['id']}", type="secondary"):
                    delete_holding(h["id"])
                    st.rerun()

            st.markdown('<hr style="border-color:#f1f5f9;margin:2px 0 10px 0">', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# ── STOCK ANALYSIS VIEW ───────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

else:
    if not ticker_input:
        st.markdown("""
<div style="display:flex;align-items:center;gap:16px;padding:24px 0 8px 0">
  <svg width="64" height="64" viewBox="0 0 52 52" xmlns="http://www.w3.org/2000/svg">
    <rect x="0" y="0" width="52" height="52" rx="13" fill="#0f172a"/>
    <text x="26" y="20" text-anchor="middle"
          font-family="Georgia,'Times New Roman',serif"
          font-size="14" font-weight="700" fill="#f8fafc" letter-spacing="1.5">XW</text>
    <line x1="9" y1="25" x2="43" y2="25" stroke="#1e293b" stroke-width="0.8"/>
    <polygon points="9,45 16,39 23,42 33,32 43,27 43,45"
             fill="#2563eb" fill-opacity="0.12"/>
    <polyline points="9,45 16,39 23,42 33,32 43,27"
              stroke="#2563eb" stroke-width="2.2" fill="none"
              stroke-linecap="round" stroke-linejoin="round"/>
    <circle cx="43" cy="27" r="2.6" fill="#2563eb"/>
  </svg>
  <div>
    <div style="font-size:1.8em;font-weight:800;color:#0f172a;letter-spacing:-0.5px;line-height:1.1">
      Stock Analyst
    </div>
    <div style="font-size:0.78em;font-weight:700;color:#2563eb;letter-spacing:1.5px;text-transform:uppercase;margin-top:4px">
      XW &middot; Personal Dashboard
    </div>
  </div>
</div>
""", unsafe_allow_html=True)
        st.info("Enter a ticker symbol in the sidebar to begin.")
        st.stop()

    with st.spinner(f"Loading {ticker_input} · {PERIOD_LABELS[period]}…"):
        data, fund_result, tech_result, wave_result, report = run_analysis(ticker_input, period)

    if data["history"].empty:
        st.error(f"No price data found for **{ticker_input}**. Check the ticker symbol.")
        st.stop()

    if report is None:
        st.error("Analysis failed — not enough data.")
        st.stop()

    company     = report["company"]
    verdict     = report["verdict"]
    narrative   = report["narrative"]
    is_intraday = data.get("is_intraday", False)

    # ── Header ─────────────────────────────────────────────────────────────────

    col_header, col_verdict = st.columns([3, 1])

    with col_header:
        name     = company.get("name", ticker_input)
        price    = company.get("current_price")
        chg      = company.get("day_change")
        currency = company.get("currency", "USD")

        st.title(f"{name}  ({ticker_input})")

        if price:
            chg_str = ""
            if chg is not None:
                chg_color = C_BUY if chg >= 0 else C_SELL
                arrow     = "▲" if chg >= 0 else "▼"
                chg_str   = (
                    f' <span style="color:{chg_color};font-size:0.65em;font-weight:600">'
                    f'{arrow} {chg:+.2f}%</span>'
                )
            st.markdown(
                f'<p style="font-size:1.8em;font-weight:700;color:#0f172a;margin:0">'
                f'{currency} {price:,.2f}{chg_str}</p>',
                unsafe_allow_html=True,
            )

        meta_parts = [v for k in ("sector", "industry", "exchange")
                      if (v := company.get(k, "")) and v != "N/A"]
        if meta_parts:
            st.caption(" · ".join(meta_parts))

    with col_verdict:
        _v_styles = {
            "green":      ("#f0fdf4", "#16a34a"),
            "lightgreen": ("#f7fee7", "#65a30d"),
            "yellow":     ("#fffbeb", "#d97706"),
            "orange":     ("#fff7ed", "#ea580c"),
            "red":        ("#fef2f2", "#dc2626"),
        }
        v_bg, v_color = _v_styles.get(verdict["color"], ("#f8fafc", "#64748b"))
        st.markdown(
            f'<div class="verdict-box" style="background:{v_bg};'
            f'border:2px solid {v_color};color:{v_color}">'
            f'{verdict["label"]}</div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # ── Chart controls ─────────────────────────────────────────────────────────

    hist = data["history"].copy()
    hist.columns = [c.lower() for c in hist.columns]

    ctrl_left, ctrl_mid, ctrl_right = st.columns([2, 3, 3])
    with ctrl_left:
        chart_type = st.radio("Chart type", ["Candlestick", "Line"], horizontal=True)
    with ctrl_mid:
        show_mas = st.multiselect(
            "Moving averages",
            ["SMA 20", "SMA 50", "SMA 200"],
            default=["SMA 50", "SMA 200"],
        )
    with ctrl_right:
        c1, c2 = st.columns(2)
        show_bb  = c1.checkbox("Bollinger Bands", value=True)
        show_fib = c2.checkbox("Fibonacci levels", value=False)

    # ── Main price chart ────────────────────────────────────────────────────────

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.75, 0.25],
    )

    if chart_type == "Candlestick":
        fig.add_trace(go.Candlestick(
            x=hist.index,
            open=hist["open"], high=hist["high"],
            low=hist["low"],  close=hist["close"],
            name="Price",
            increasing_line_color=C_BUY,
            decreasing_line_color=C_SELL,
            increasing_fillcolor=C_BUY,
            decreasing_fillcolor=C_SELL,
        ), row=1, col=1)
    else:
        fig.add_trace(go.Scatter(
            x=hist.index, y=hist["close"],
            line=dict(color=C_BLUE, width=2),
            name="Close",
            fill="tozeroy",
            fillcolor="rgba(37,99,235,0.06)",
        ), row=1, col=1)

    ma_colors = {"SMA 20": C_AMBER, "SMA 50": C_VIOLET, "SMA 200": C_PINK}
    for ma in show_mas:
        period_val = int(ma.split()[1])
        if len(hist) >= period_val:
            fig.add_trace(go.Scatter(
                x=hist.index,
                y=hist["close"].rolling(period_val).mean(),
                line=dict(color=ma_colors[ma], width=1.5, dash="dot"),
                name=ma,
            ), row=1, col=1)

    ind = tech_result.get("indicators", {}) if tech_result else {}
    if show_bb:
        bb_upper = ind.get("_bb_upper_series")
        bb_lower = ind.get("_bb_lower_series")
        if bb_upper is not None and bb_lower is not None:
            fig.add_trace(go.Scatter(
                x=hist.index, y=bb_upper,
                line=dict(color=C_SLATE, width=1, dash="dash"),
                name="BB Upper",
            ), row=1, col=1)
            fig.add_trace(go.Scatter(
                x=hist.index, y=bb_lower,
                line=dict(color=C_SLATE, width=1, dash="dash"),
                name="BB Lower",
                fill="tonexty", fillcolor="rgba(148,163,184,0.07)",
            ), row=1, col=1)

    if show_fib:
        fib_data = wave_result.get("fibonacci", {}) if wave_result else {}
        if fib_data and fib_data.get("levels"):
            for lbl, lvl in fib_data["levels"].items():
                fig.add_hline(
                    y=lvl, line_dash="dot", line_color=C_AMBER, opacity=0.5,
                    annotation_text=f"Fib {lbl}", annotation_position="right",
                    row=1, col=1,
                )

    bar_colors = [C_BUY if c >= o else C_SELL
                  for c, o in zip(hist["close"], hist["open"])]
    fig.add_trace(go.Bar(
        x=hist.index, y=hist["volume"],
        marker_color=bar_colors, name="Volume",
        showlegend=False, opacity=0.5,
    ), row=2, col=1)

    _chart_layout(fig, height=460)
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)

    st.plotly_chart(fig, use_container_width=True)

    # ── Elliott Wave Chart ──────────────────────────────────────────────────────

    if wave_result:
        chart_data = wave_result.get("chart_data", {}) or {}
        if chart_data.get("applicable"):
            st.markdown("---")

            ew_head, ew_meta = st.columns([2, 3])
            ew_head.markdown("### Elliott Wave Analysis")
            confidence    = chart_data.get("confidence", "Low")
            swing_count   = chart_data.get("swing_count", 0)
            primary_trend = chart_data.get("primary_trend", "")
            ew_meta.caption(
                f"Confidence: **{confidence}** · Swings: {swing_count} · "
                f"Trend: {primary_trend} · "
                "_Estimates only — EW is inherently subjective_"
            )

            labeled_points = chart_data.get("labeled_points", [])
            zigzag_x  = chart_data.get("zigzag_x", [])
            zigzag_y  = chart_data.get("zigzag_y", [])
            scenarios = chart_data.get("scenarios", [])

            fig_wave = go.Figure()

            cutoff = labeled_points[0]["date"] if labeled_points else hist.index[0]
            hist_ctx = hist[hist.index >= cutoff]
            fig_wave.add_trace(go.Scatter(
                x=hist_ctx.index, y=hist_ctx["close"],
                line=dict(color="#cbd5e1", width=1),
                name="Price", showlegend=False,
            ))

            if zigzag_x and zigzag_y:
                fig_wave.add_trace(go.Scatter(
                    x=zigzag_x, y=zigzag_y,
                    line=dict(color="#94a3b8", width=1.5),
                    mode="lines",
                    name="Wave structure", showlegend=False,
                ))

            for pt in labeled_points:
                fig_wave.add_trace(go.Scatter(
                    x=[pt["date"]], y=[pt["price"]],
                    mode="markers+text",
                    marker=dict(color=pt["color"], size=10, symbol="circle",
                                line=dict(color="#ffffff", width=1.5)),
                    text=[pt["label"]],
                    textposition="top center" if pt["is_high"] else "bottom center",
                    textfont=dict(color=pt["color"], size=13, family="monospace"),
                    name=f"Wave {pt['label']}", showlegend=False,
                ))

            for scenario in scenarios:
                pts = scenario.get("points", [])
                if len(pts) < 2:
                    continue
                fig_wave.add_trace(go.Scatter(
                    x=[p["date"] for p in pts],
                    y=[p["price"] for p in pts],
                    mode="lines+markers",
                    line=dict(color=scenario["color"], width=2, dash=scenario["dash"]),
                    marker=dict(color=scenario["color"], size=7,
                                line=dict(color="#ffffff", width=1)),
                    name=scenario["name"],
                    cliponaxis=False,
                ))
                # Place label above for upward scenarios, below for downward
                last_pt = pts[-1]
                going_up = last_pt["price"] >= pts[0]["price"]
                ay_offset = -22 if going_up else 22
                fig_wave.add_annotation(
                    x=last_pt["date"],
                    y=last_pt["price"],
                    text=scenario["target_label"],
                    showarrow=True,
                    arrowhead=1,
                    arrowsize=0.7,
                    arrowcolor=scenario["color"],
                    arrowwidth=1,
                    ax=0, ay=ay_offset,
                    font=dict(color=scenario["color"], size=11),
                    xanchor="center",
                    xref="x", yref="y",
                    align="center",
                )

            # "Now" vertical divider (workaround: add_shape + add_annotation)
            now_date = str(hist.index[-1])
            y_min = min(zigzag_y) * 0.97 if zigzag_y else None
            y_max = max(zigzag_y) * 1.03 if zigzag_y else None
            if y_min and y_max:
                fig_wave.add_shape(
                    type="line", x0=now_date, x1=now_date, y0=0, y1=1, yref="paper",
                    line=dict(dash="dot", color="#94a3b8", width=1.5), opacity=0.8,
                )
                fig_wave.add_annotation(
                    x=now_date, y=1, yref="paper", text="Now", showarrow=False,
                    font=dict(color="#64748b", size=11), yanchor="bottom",
                )

            _chart_layout(fig_wave, height=340, right_margin=60)
            fig_wave.update_yaxes(title_text="Price")
            st.plotly_chart(fig_wave, use_container_width=True)

            if scenarios:
                st.markdown("**Projected targets from current level:**")
                cols = st.columns(len(scenarios))
                current_p = hist["close"].iloc[-1]
                for i, s in enumerate(scenarios):
                    pts = s.get("points", [])
                    if pts:
                        final_price = pts[-1]["price"]
                        pct = (final_price - current_p) / current_p * 100
                        cols[i].metric(s["name"], f"${final_price:,.2f}", f"{pct:+.1f}%")

    # ── Analysis Tabs (5 tabs — no portfolio tab) ──────────────────────────────

    st.markdown("---")
    tab_fund, tab_tech, tab_wave, tab_report, tab_news = st.tabs([
        "📊 Fundamental", "📉 Technical", "🌊 Wave & Trend",
        "📋 Full Report", "📰 News",
    ])

    # ── Fundamental Tab ─────────────────────────────────────────────────────────

    with tab_fund:
        if is_intraday:
            st.info("Fundamental data is not shown for intraday periods. Switch to 1 Month or longer.")
        elif fund_result:
            fund_summary = fund_result.get("summary", {})
            ratings = fund_summary.get("ratings", {})

            r_cols = st.columns(len(ratings) or 4)
            for i, (area, rating) in enumerate(ratings.items()):
                r_cols[i].metric(area, rating)

            st.markdown("---")
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Valuation")
                val = fund_result.get("valuation", {})
                for label, key in [
                    ("Trailing P/E", "trailing_pe"), ("Forward P/E", "forward_pe"),
                    ("Price/Book", "price_to_book"), ("Price/Sales", "price_to_sales"),
                    ("PEG Ratio", "peg_ratio"), ("EV/EBITDA", "ev_to_ebitda"),
                ]:
                    v = val.get(key)
                    if v is not None:
                        st.metric(label, f"{v:.2f}" if isinstance(v, float) else v)

                st.markdown("---")
                st.subheader("Growth")
                growth = fund_result.get("growth", {})
                st.metric("Revenue YoY", growth.get("revenue_yoy", "N/A"))
                st.metric("Earnings YoY", growth.get("earnings_yoy", "N/A"))

            with col2:
                st.subheader("Profitability")
                prof = fund_result.get("profitability", {})
                for label, key in [
                    ("Gross Margin", "gross_margin"), ("Operating Margin", "operating_margin"),
                    ("Net Margin", "net_margin"), ("ROE", "roe"), ("ROA", "roa"),
                ]:
                    v = prof.get(key)
                    if v:
                        st.metric(label, v)

                st.markdown("---")
                st.subheader("Financial Health")
                health = fund_result.get("financial_health", {})
                for label, key in [
                    ("Current Ratio", "current_ratio"), ("Quick Ratio", "quick_ratio"),
                    ("Debt/Equity", "debt_to_equity"),
                ]:
                    v = health.get(key)
                    if v is not None:
                        st.metric(label, f"{v:.2f}" if isinstance(v, float) else v)
                fcf = health.get("free_cash_flow")
                if fcf:
                    st.metric("Free Cash Flow",
                              f"${fcf/1e9:.2f}B" if abs(fcf) >= 1e9 else f"${fcf/1e6:.0f}M")

            div = fund_result.get("dividends", {})
            if div.get("pays_dividend"):
                st.markdown("---")
                st.subheader("Dividends")
                d_cols = st.columns(3)
                d_cols[0].metric("Yield", div.get("yield", "N/A"))
                d_cols[1].metric("Annual Rate",
                                 f"${div.get('rate', 0):.2f}" if div.get("rate") else "N/A")
                d_cols[2].metric("Payout Ratio", div.get("payout_ratio", "N/A"))

    # ── Technical Tab ───────────────────────────────────────────────────────────

    with tab_tech:
        if tech_result and not tech_result.get("error"):
            tech_summary = tech_result.get("summary", {})
            ind_t    = tech_result.get("indicators", {})
            signals  = tech_result.get("signals", {})
            sr       = tech_result.get("support_resistance", {})

            col_trend, col_score = st.columns([2, 1])
            with col_trend:
                st.metric("Technical Trend", tech_summary.get("trend", "N/A"))
            with col_score:
                score = tech_summary.get("score", 0)
                st.metric("Signal Score", f"{score:+d}")

            st.markdown("---")
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Key Indicators")

                rsi = ind_t.get("rsi")
                if rsi:
                    rsi_bar = C_BUY if rsi < 40 else C_SELL if rsi > 60 else C_AMBER
                    fig_rsi = go.Figure(go.Indicator(
                        mode="gauge+number",
                        value=rsi,
                        number={"font": {"color": "#0f172a", "size": 32}},
                        gauge={
                            "axis": {"range": [0, 100], "tickcolor": "#94a3b8"},
                            "bar": {"color": rsi_bar},
                            "bgcolor": "#f8fafc",
                            "bordercolor": "#e2e8f0",
                            "steps": [
                                {"range": [0,  30], "color": "#dcfce7"},
                                {"range": [30, 70], "color": "#f8fafc"},
                                {"range": [70, 100], "color": "#fee2e2"},
                            ],
                            "threshold": {
                                "line": {"color": "#334155", "width": 2},
                                "value": rsi,
                            },
                        }
                    ))
                    fig_rsi.update_layout(
                        height=220, autosize=True, template="plotly_white",
                        margin=dict(t=36, b=5, l=20, r=20),
                        paper_bgcolor="#ffffff",
                        title=dict(text="RSI (14)", font=dict(color="#334155", size=13),
                                   x=0.5, xanchor="center"),
                    )
                    st.plotly_chart(fig_rsi, use_container_width=True)

                macd_line_s = ind_t.get("_macd_series")
                macd_sig_s  = ind_t.get("_macd_signal_series")
                macd_hist_s = ind_t.get("_macd_hist_series")
                if macd_line_s is not None and macd_sig_s is not None:
                    fig_macd = go.Figure()
                    fig_macd.add_trace(go.Scatter(
                        x=hist.index, y=macd_line_s, name="MACD",
                        line=dict(color=C_BLUE, width=1.5)))
                    fig_macd.add_trace(go.Scatter(
                        x=hist.index, y=macd_sig_s, name="Signal",
                        line=dict(color=C_AMBER, width=1.5)))
                    if macd_hist_s is not None:
                        hc_colors = [C_BUY if (not pd.isna(v) and v >= 0) else C_SELL
                              for v in macd_hist_s]
                        fig_macd.add_trace(go.Bar(
                            x=hist.index, y=macd_hist_s,
                            name="Histogram", marker_color=hc_colors, opacity=0.6))
                    fig_macd.update_layout(
                        height=180, autosize=True, template="plotly_white",
                        margin=dict(t=30, b=0, l=0, r=0),
                        paper_bgcolor="#ffffff", plot_bgcolor="#ffffff",
                        title=dict(text="MACD", font=dict(color="#334155", size=13)),
                    )
                    fig_macd.update_xaxes(gridcolor=C_GRID)
                    fig_macd.update_yaxes(gridcolor=C_GRID)
                    st.plotly_chart(fig_macd, use_container_width=True)

            with col2:
                st.subheader("Signals")
                for sig in signals.values():
                    bullish = sig.get("bullish")
                    lbl     = sig.get("label", "")
                    if bullish is True:
                        st.markdown(
                            f'<div class="reason-block tech">'
                            f'<span class="signal-bull">▲</span> {lbl}</div>',
                            unsafe_allow_html=True)
                    elif bullish is False:
                        st.markdown(
                            f'<div class="reason-block" style="border-left-color:#dc2626">'
                            f'<span class="signal-bear">▼</span> {lbl}</div>',
                            unsafe_allow_html=True)
                    else:
                        st.markdown(
                            f'<div class="reason-block">'
                            f'<span class="signal-neutral">●</span> {lbl}</div>',
                            unsafe_allow_html=True)

                st.markdown("---")
                st.subheader("Support / Resistance")
                if sr:
                    for r in sr.get("resistance", []):
                        st.markdown(
                            f'<span class="signal-bear" style="font-size:0.95em">'
                            f'▲ Resistance: <strong>${r:,.2f}</strong></span>',
                            unsafe_allow_html=True)
                    st.markdown(
                        f'<span style="color:#0f172a;font-weight:600">'
                        f'◆ Current: ${sr.get("current_price", "N/A"):,.2f}</span>',
                        unsafe_allow_html=True)
                    for s in sr.get("support", []):
                        st.markdown(
                            f'<span class="signal-bull" style="font-size:0.95em">'
                            f'▼ Support: <strong>${s:,.2f}</strong></span>',
                            unsafe_allow_html=True)
        else:
            st.info(tech_result.get("error", "Technical analysis unavailable.")
                    if tech_result else "Technical analysis unavailable.")

    # ── Wave Tab ────────────────────────────────────────────────────────────────

    with tab_wave:
        if wave_result:
            trend_phase = wave_result.get("trend_phase", {})
            wave_est    = wave_result.get("wave_estimate", {})
            fib_data    = wave_result.get("fibonacci", {})

            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Market Phase")
                st.info(trend_phase.get("phase", "Unknown"))

                st.subheader("Trend Alignment")
                t_cols = st.columns(3)
                t_cols[0].metric("Primary",      trend_phase.get("primary", "N/A"))
                t_cols[1].metric("Intermediate", trend_phase.get("intermediate", "N/A"))
                t_cols[2].metric("Short-term",   trend_phase.get("short_term", "N/A"))

                st.markdown("---")
                st.subheader("Swing Structure (Dow Theory)")
                st.write(trend_phase.get("swing_structure", "N/A"))

                st.subheader("Elliott Wave Estimate")
                st.write(wave_est.get("position", "N/A"))
                st.caption(
                    f"Confidence: {wave_est.get('confidence', 'N/A')} · "
                    f"Swings detected: {wave_est.get('swing_count', 0)}"
                )
                st.caption(wave_est.get("note", ""))

            with col2:
                st.subheader("Fibonacci Retracement")
                if fib_data and fib_data.get("levels"):
                    levels = fib_data["levels"]
                    st.caption(
                        f"Based on {fib_data.get('direction', '')}: "
                        f"${fib_data.get('swing_low', '')} → ${fib_data.get('swing_high', '')}"
                    )
                    for lbl, pv in reversed(list(levels.items())):
                        is_cur = lbl == fib_data.get("nearest_level")
                        style  = "font-weight:700;color:#d97706" if is_cur else "color:#334155"
                        marker = " ◀ Current" if is_cur else ""
                        st.markdown(
                            f'<div style="display:flex;justify-content:space-between;'
                            f'padding:4px 0;border-bottom:1px solid #f1f5f9;{style}">'
                            f'<span>{lbl}</span><span>${pv}{marker}</span></div>',
                            unsafe_allow_html=True,
                        )
                else:
                    st.write("Fibonacci data not available.")

            st.markdown("---")
            wave_summary = wave_result.get("summary", "")
            if wave_summary:
                st.markdown(wave_summary)
        else:
            st.info("Wave analysis unavailable — need at least 50 data points.")

    # ── Report Tab ──────────────────────────────────────────────────────────────

    with tab_report:
        _price    = company.get("current_price")
        high52    = company.get("52w_high")
        low52     = company.get("52w_low")
        a_target  = company.get("analyst_target")
        a_rating  = company.get("analyst_rating")

        stat_cols = st.columns(5)
        stat_cols[0].metric("Price",           f"${_price:,.2f}"   if _price    else "N/A")
        stat_cols[1].metric("52W High",        f"${high52:,.2f}"   if high52    else "N/A")
        stat_cols[2].metric("52W Low",         f"${low52:,.2f}"    if low52     else "N/A")
        stat_cols[3].metric("Analyst Target",  f"${a_target:,.2f}" if a_target  else "N/A")
        stat_cols[4].metric("Analyst Rating",  a_rating or "N/A")

        st.markdown("---")

        if narrative.get("ai_powered"):
            st.success("AI-powered analysis by Claude")
        else:
            st.info("Rule-based analysis · Add Claude API key in sidebar for AI synthesis")
            if narrative.get("ai_error"):
                st.caption(f"AI error: {narrative['ai_error']}")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Fundamental Analysis")
            st.markdown(narrative.get("fundamental", "N/A"))
            st.subheader("Technical Analysis")
            st.markdown(narrative.get("technical", "N/A"))
            st.subheader("Wave & Trend Analysis")
            st.markdown(narrative.get("wave", "N/A"))

        with col2:
            st.subheader("Bull Case")
            for line in (narrative.get("bull_case") or "").split(";"):
                line = line.strip()
                if line:
                    st.markdown(f"✅ {line}")
            st.subheader("Bear Case")
            for line in (narrative.get("bear_case") or "").split(";"):
                line = line.strip()
                if line:
                    st.markdown(f"⚠️ {line}")
            st.subheader("Risk Flags")
            for risk in report.get("risks", []):
                st.markdown(f"🔸 {risk}")

        st.markdown("---")
        st.subheader("About")
        desc = company.get("description", "")
        if len(desc) > 600:
            with st.expander("Show full description"):
                st.write(desc)
            st.write(desc[:600] + "…")
        else:
            st.write(desc)

    # ── News Tab ─────────────────────────────────────────────────────────────────

    with tab_news:
        news_items = report.get("news", [])
        if not news_items:
            st.info("No recent news found.")
        else:
            for item in news_items:
                title     = item.get("title", "")
                publisher = item.get("publisher", "")
                link      = item.get("link", "")
                ts        = item.get("time", 0)
                date_str  = datetime.fromtimestamp(ts).strftime("%b %d, %Y") if ts else ""

                with st.container():
                    if title and link:
                        st.markdown(
                            f'<a href="{link}" target="_blank" style="font-weight:600;'
                            f'color:#0f172a;text-decoration:none;font-size:0.97em">{title}</a>',
                            unsafe_allow_html=True,
                        )
                    elif title:
                        st.markdown(f"**{title}**")
                    st.caption(f"{publisher}  ·  {date_str}")
                    st.markdown('<hr style="border-color:#f1f5f9;margin:10px 0">', unsafe_allow_html=True)


# ── Footer ─────────────────────────────────────────────────────────────────────

st.markdown("""
<div style="text-align:center;color:#94a3b8;font-size:0.8em;margin-top:48px;
padding-top:20px;border-top:1px solid #e2e8f0">
⚠️ For informational purposes only — not financial advice.
Always conduct your own research before making investment decisions.
</div>
""", unsafe_allow_html=True)
