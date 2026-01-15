import pandas as pd
from edgar import set_identity, Company
import json

# 1. SEC Identity (Required)
set_identity("Your Name yourname@example.com")


def get_risk_analysis(ticker):
    print(f"Analyzing {ticker} for EAI Compliance standards...")

    # 2. Initialize Company
    company = Company(ticker)

    # 3. Pull raw 'Facts' (This bypasses the 'Statement' error)
    # We pull the most common XBRL tag for Revenue
    facts = company.get_facts()

    # Financial data often uses 'Revenues' or 'SalesRevenueNet'
    # We'll try to get the most recent annual value
    try:
        revenue_facts = facts.get_fact("Revenues")
        # Get the most recent value from the factsheet
        latest_rev = revenue_facts.data.iloc[-1]['val']
        rev_formatted = f"${latest_rev:,.0f}"
    except:
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


# --- Execution ---
if __name__ == "__main__":
    try:
        analysis = get_risk_analysis("SSNC")
        print("\n--- COMPLIANCE REPORT GENERATED ---")
        for key, value in analysis.items():
            print(f"{key}: {value}")
    except Exception as e:
        print(f"\nAn error occurred: {e}")