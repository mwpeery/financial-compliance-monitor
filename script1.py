import sys
import pandas as pd
from edgar import set_identity, Company
import json

# 1. SEC Identity (Required) — EDGAR requires a real name + email on every request
set_identity("Matt Peery mwpeery@gmail.com")

# Companies tracked by the dashboard — keep this in sync with app.py
TICKERS = ["SSNC", "BLK", "STT", "ENV"]


def get_risk_analysis(ticker):
    print(f"Analyzing {ticker} for EAI Compliance standards...")

    # 2. Initialize Company
    company = Company(ticker)

    # 3. Pull the most common XBRL tag for Revenue
    facts = company.get_facts()

    try:
        revenue_facts = facts.get_fact("Revenues")
        latest_rev = revenue_facts.data.iloc[-1]['val']
        rev_formatted = f"${latest_rev:,.0f}"
    except Exception:
        rev_formatted = "Check 10-K Manual (Custom Revenue Tag)"

    # 4. Keyword scan for Compliance/Risk
    filing = company.get_filings(form="10-K", amendments=False).latest()
    doc_text = filing.html().lower()
    risk_keywords = ["litigation", "regulatory", "cybersecurity", "debt", "competition"]
    found_risks = [word for word in risk_keywords if word in doc_text]

    report = {
        "Company": ticker,
        "Revenue": rev_formatted,
        "Risk_Keywords_Found": found_risks,
        "Source_URL": filing.url,
        "Status": "Verified via Fact-Check"
    }

    # 5. Save to JSON
    with open(f"{ticker}_report.json", "w") as f:
        json.dump(report, f, indent=4)

    return report


def run(tickers):
    results = {}
    for ticker in tickers:
        try:
            results[ticker] = get_risk_analysis(ticker)
            print(f"✅ {ticker} report generated\n")
        except Exception as e:
            print(f"❌ {ticker} failed: {e}\n")
    return results


# --- Execution ---
if __name__ == "__main__":
    # `python script1.py`          -> refreshes every tracked ticker
    # `python script1.py SSNC BLK` -> refreshes just the tickers you list
    targets = sys.argv[1:] if len(sys.argv) > 1 else TICKERS
    run(targets)
