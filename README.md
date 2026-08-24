# 🏦 Financial Compliance & Risk Monitor - 
https://mwpeery-financial-compliance-monitor.streamlit.app/

An automated data pipeline that extracts financial risk factors from SEC EDGAR filings and visualizes them in a professional dashboard.

## 🚀 Overview
This project automates the manual process of auditing 10-K filings. It identifies key regulatory risks (e.g., Litigation, Cybersecurity) to assist in compliance monitoring.

## 🛠️ Features
- **Data Pipeline:** Extracts live XBRL data using the SEC EDGAR API.
- **Interactive Dashboard:** Built with Streamlit to display company metrics and risks, across three tabs:
  - **Overview** — the latest 10-K for one company: revenue, risk-keyword chips, and filing context snippets.
  - **Trend** — pulls the last N years of 10-Ks for a company and charts how often each risk keyword shows up, filing over filing, alongside a revenue trend.
  - **Peer Comparison** — a grouped bar chart of risk mentions and revenue across every tracked ticker at once.
- **Automated Reporting:** Generates structured JSON reports (`{TICKER}_report.json`, `{TICKER}_history.json`) for audit trails.
- **Caching:** Filing text and computed reports are cached locally (`.cache/`, keyed by ticker + accession number) so re-running the app doesn't re-hit EDGAR for a filing it's already processed.
- **Resilience:** SEC/EDGAR calls retry with backoff and fail with a clear message instead of crashing the app.

## 🧪 Running the tests
```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest
```
The suite covers the keyword-counting, HTML-cleaning, revenue-extraction, and caching logic in `script1.py` with no network calls — it runs in CI on every push/PR (see `.github/workflows/tests.yml`).

## 📊 Pulling a multi-year trend from the CLI
```bash
python script1.py --history SSNC        # last 5 years (default)
python script1.py --history SSNC BLK    # multiple tickers
```

## 📈 Tech Stack
- **Python** (Core Analysis)
- **Streamlit** (Visualization)
- **Pandas** (Data Formatting)
- **Altair** (Charting)
- **pytest** (Testing)
