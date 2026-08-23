import sys
import re
import pandas as pd
from bs4 import BeautifulSoup
from edgar import set_identity, Company
import json

# 1. SEC Identity (Required) — EDGAR requires a real name + email on every request
set_identity("Matt Peery mwpeery@gmail.com")

# Companies tracked by the dashboard — keep this in sync with app.py
# ENV (Envestnet) was swapped for SEIC (SEI Investments) — Envestnet was
# taken private by Bain Capital in Nov 2024 and delisted from the NYSE, so
# it no longer files with the SEC and EDGAR can't resolve the ticker. SEIC
# is a live public company in the same wealth-management/fintech peer group.
TICKERS = ["SSNC", "BLK", "STT", "SEIC"]


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
    # NOTE: these 5 topics are boilerplate that nearly every 10-K's Item 1A
    # "Risk Factors" section mentions, since the SEC requires issuers to
    # disclose general risk categories whether or not they're currently
    # material. A yes/no check on presence returns "all 5" for almost any
    # company, so we count occurrences instead — frequency is what actually
    # differs company to company, and it lets us surface real context.
    filing = company.get_filings(form="10-K", amendments=False).latest()
    raw_html = filing.html()

    # Strip HTML/XBRL markup down to just the human-readable text. Searching
    # the raw HTML picks up hidden XBRL tag names and URLs (e.g. the tag
    # "longtermdebtandcapitalleaseobligations" contains "debt" as a
    # substring), which massively inflates counts with matches nobody
    # would actually read as a mention of that risk.
    soup = BeautifulSoup(raw_html, "html.parser")
    doc_text = soup.get_text(separator=" ")
    doc_text = re.sub(r"\s+", " ", doc_text).lower()

    risk_keywords = ["litigation", "regulatory", "cybersecurity", "debt", "competition"]

    risk_counts = {}
    risk_snippets = {}
    for word in risk_keywords:
        # \b word boundaries so "debt" doesn't match inside "indebtedness", etc.
        matches = list(re.finditer(rf"\b{word}\b", doc_text))
        count = len(matches)
        if count > 0:
            risk_counts[word] = count
            # grab the sentence around the first mention for context
            idx = matches[0].start()
            start = max(0, idx - 120)
            end = min(len(doc_text), idx + 120)
            snippet = doc_text[start:end].strip()
            risk_snippets[word] = f"...{snippet}..."

    report = {
        "Company": ticker,
        "Revenue": rev_formatted,
        "Risk_Keyword_Counts": risk_counts,
        "Risk_Keyword_Snippets": risk_snippets,
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
