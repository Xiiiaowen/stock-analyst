# XW Stock Analyst

A personal investment research tool built with Python and Streamlit — combining **fundamental analysis**, **technical indicators**, **Elliott Wave / trend detection**, and an optional **AI-powered narrative** via the Claude API.

![XW Stock Analyst](<screenshots/app 2026-03-03 220440.png>)

---

## Features

### Stock Analysis
- **Fundamental** — Valuation (P/E, P/B, PEG, EV/EBITDA), profitability (margins, ROE, ROA), YoY revenue & earnings growth, financial health (current ratio, D/E, free cash flow), dividends
- **Technical** — RSI, MACD, Bollinger Bands, Stochastic Oscillator, moving averages (SMA 20/50/200, EMA 12/26), ATR, volume confirmation, support & resistance levels
- **Wave & Trend** — Elliott Wave position estimate, trend phase classification, Fibonacci retracement levels
- **AI Narrative** — When an `ANTHROPIC_API_KEY` is provided, Claude generates a concise, data-grounded analyst report (bull/bear case, risks)
- **Interactive Charts** — Candlestick chart with overlaid indicators, MACD histogram, RSI gauge, volume bars (Plotly)
- **Overall Verdict** — Aggregated Strong Buy / Buy / Hold / Sell / Strong Sell signal

### My Portfolio
- Add, track, and remove holdings (ticker, quantity, entry price, date, notes)
- Live P&L ($ and %) per position with color-coded gain/loss
- Per-holding recommendation: ADD / HOLD / SELL badge with stop-loss, hold range, and target price
- Rule-based rationale combining technical signals, fundamental score, and position P&L

---

## Tech Stack

| Layer | Library |
|---|---|
| UI | [Streamlit](https://streamlit.io) |
| Market Data | [yfinance](https://github.com/ranaroussi/yfinance) |
| Technical Indicators | [ta](https://github.com/bukosabino/ta) |
| Charts | [Plotly](https://plotly.com/python/) |
| AI Narrative | [Anthropic Claude API](https://docs.anthropic.com) |
| Portfolio Storage | SQLite (via `sqlite3`) |
| Data Processing | pandas, numpy |

---

## Getting Started

### 1. Clone the repo
```bash
git clone https://github.com/Xiiiaowen/stock-analyst.git
cd stock-analyst
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. (Optional) Set your Anthropic API key for AI narratives
```bash
# Windows
set ANTHROPIC_API_KEY=sk-ant-...

# macOS / Linux
export ANTHROPIC_API_KEY=sk-ant-...
```
Without the key the app runs fully on rule-based analysis — no API required.

### 4. Run
```bash
streamlit run app.py
```

---

## Project Structure

```
stock-analyst/
├── app.py                  # Main Streamlit app
├── requirements.txt
├── data/
│   ├── fetcher.py          # yfinance data layer
│   └── portfolio_db.py     # SQLite CRUD for holdings
├── analysis/
│   ├── fundamental.py      # Valuation, profitability, growth, health
│   ├── technical.py        # Indicators & signal generation
│   ├── wave.py             # Elliott Wave & Fibonacci
│   └── portfolio.py        # Per-holding recommendation engine
└── report/
    └── builder.py          # Report synthesis (rule-based + AI)
```

---

## Deploying to Streamlit Community Cloud

1. Push this repo to GitHub (public)
2. Go to [share.streamlit.io](https://share.streamlit.io) and connect the repo
3. Set `ANTHROPIC_API_KEY` in the **Secrets** panel if you want AI narratives
4. Your app will be live at `https://xiiiaowen-stock-analyst.streamlit.app` (or similar)

---

## Disclaimer

> For informational purposes only — not financial advice.
> Always conduct your own research before making investment decisions.
