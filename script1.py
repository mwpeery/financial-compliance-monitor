import sys
import re
import json
import time
import hashlib
from pathlib import Path

from bs4 import BeautifulSoup
from edgar import set_identity, Company

# 1. SEC Identity (Required) — EDGAR requires a real name + email on every request
set_identity("Matt Peery mwpeery@gmail.com")

# Companies tracked by the dashboard — keep this in sync with app.py
# ENV (Envestnet) was swapped for SEIC (SEI Investments) — Envestnet was
# taken private by Bain Capital in Nov 2024 and delisted from the NYSE, so
# it no longer files with the SEC and EDGAR can't resolve the ticker. SEIC
# is a live public company in the same wealth-management/fintech peer group.
TICKERS = ["SSNC", "BLK", "STT", "SEIC"]

# The 5 boilerplate risk topics every 10-K's Item 1A touches on. A yes/no
# presence check returns "all 5" for almost any filer, so we count
# occurrences instead — frequency is what actually differs company to
# company, and it lets us surface real context.
RISK_KEYWORDS = ["litigation", "regulatory", "cybersecurity", "debt", "competition"]

# Revenue isn't tagged the same way across filers — try each XBRL tag in
# order and use whichever one the filing actually has.
REVENUE_TAGS = [
    "Revenues",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
    "SalesRevenueNet",
]

CACHE_DIR = Path(".cache")
CACHE_TTL_SECONDS = 24 * 60 * 60  # a day is plenty — a given filing's text never changes
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2


# ---------------------------------------------------------------------------
# Pure, network-free helpers — these are what the test suite exercises.
# ---------------------------------------------------------------------------

def clean_filing_text(raw_html):
    """Strip HTML/XBRL markup down to plain, lowercase, whitespace-collapsed text.

    Searching the raw HTML picks up hidden XBRL tag names and URLs (e.g. the
    tag "longtermdebtandcapitalleaseobligations" contains "debt" as a
    substring), which massively inflates counts with matches nobody would
    actually read as a mention of that risk.
    """
    soup = BeautifulSoup(raw_html, "html.parser")
    doc_text = soup.get_text(separator=" ")
    doc_text = re.sub(r"\s+", " ", doc_text).lower()
    return doc_text


def count_risk_keywords(doc_text, keywords=None):
    """Count whole-word occurrences of each risk keyword in already-cleaned text.

    Returns (risk_counts, risk_snippets) — snippets capture the ~240 chars of
    context around the first mention of each word, for the "see filing
    context" expander in the dashboard.
    """
    keywords = keywords if keywords is not None else RISK_KEYWORDS
    risk_counts = {}
    risk_snippets = {}
    for word in keywords:
        # \b word boundaries so "debt" doesn't match inside "indebtedness", etc.
        matches = list(re.finditer(rf"\b{re.escape(word)}\b", doc_text))
        count = len(matches)
        if count > 0:
            risk_counts[word] = count
            idx = matches[0].start()
            start = max(0, idx - 120)
            end = min(len(doc_text), idx + 120)
            snippet = doc_text[start:end].strip()
            risk_snippets[word] = f"...{snippet}..."
    return risk_counts, risk_snippets


def extract_revenue(facts, revenue_tags=None):
    """Pull the most recent value for the first XBRL revenue tag that resolves.

    `facts` is whatever edgartools' Company.get_facts() returns — anything
    exposing .get_fact(tag).data (a DataFrame-like with a 'val' column) works,
    which makes this easy to unit test with a stub.
    """
    revenue_tags = revenue_tags if revenue_tags is not None else REVENUE_TAGS
    for tag in revenue_tags:
        try:
            revenue_facts = facts.get_fact(tag)
            latest_rev = revenue_facts.data.iloc[-1]["val"]
            return f"${latest_rev:,.0f}", latest_rev
        except Exception:
            continue
    return "Check 10-K Manual (Custom Revenue Tag)", None


def build_report(ticker, revenue_formatted, risk_counts, risk_snippets, source_url,
                  filing_date=None, revenue_raw=None):
    report = {
        "Company": ticker,
        "Revenue": revenue_formatted,
        "Revenue_Raw": revenue_raw,
        "Risk_Keyword_Counts": risk_counts,
        "Risk_Keyword_Snippets": risk_snippets,
        "Source_URL": source_url,
        "Status": "Verified via Fact-Check",
    }
    if filing_date:
        report["Filing_Date"] = str(filing_date)
    return report


# ---------------------------------------------------------------------------
# Cache — avoids re-hitting EDGAR (and re-parsing multi-MB filings) for a
# filing we've already processed. Keyed on ticker + accession number, so a
# newly-filed 10-K naturally gets a fresh cache entry; a TTL is kept as a
# safety valve in case a report ever needs to be recomputed (e.g. after a
# bug fix to the keyword logic) without waiting for a new filing.
# ---------------------------------------------------------------------------

def _cache_key(ticker, accession_no):
    raw = f"{ticker}:{accession_no}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def _cache_path(cache_key):
    return CACHE_DIR / f"{cache_key}.json"


def _read_cache(cache_key, ttl_seconds=CACHE_TTL_SECONDS):
    path = _cache_path(cache_key)
    if not path.exists():
        return None
    age = time.time() - path.stat().st_mtime
    if age > ttl_seconds:
        return None
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _write_cache(cache_key, data):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(_cache_path(cache_key), "w") as f:
        json.dump(data, f)


# ---------------------------------------------------------------------------
# Network-touching helpers, isolated so retries/error handling live in one
# place instead of being duplicated across single-filing and historical runs.
# ---------------------------------------------------------------------------

def _with_retries(fn, description):
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return fn()
        except Exception as e:
            last_err = e
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)
    raise RuntimeError(f"{description} failed after {MAX_RETRIES} attempts: {last_err}") from last_err


def _resolve_company(ticker):
    return _with_retries(lambda: Company(ticker), f"Looking up ticker '{ticker}' on SEC EDGAR")


def _latest_10k(company, ticker):
    filing = _with_retries(
        lambda: company.get_filings(form="10-K", amendments=False).latest(),
        f"Fetching latest 10-K for '{ticker}'",
    )
    if filing is None:
        raise RuntimeError(f"No 10-K filings found for '{ticker}' on SEC EDGAR")
    return filing


def _recent_10ks(company, ticker, num_years):
    filings = _with_retries(
        lambda: company.get_filings(form="10-K", amendments=False).head(num_years),
        f"Fetching filing history for '{ticker}'",
    )
    filings = list(filings) if filings is not None else []
    if not filings:
        raise RuntimeError(f"No 10-K filings found for '{ticker}' on SEC EDGAR")
    return filings


def _analyze_filing(ticker, filing, facts, use_cache=True):
    cache_key = _cache_key(ticker, filing.accession_no)
    if use_cache:
        cached = _read_cache(cache_key)
        if cached is not None:
            return cached

    raw_html = _with_retries(lambda: filing.html(), f"Downloading filing text for '{ticker}'")
    doc_text = clean_filing_text(raw_html)
    risk_counts, risk_snippets = count_risk_keywords(doc_text)
    rev_formatted, rev_raw = extract_revenue(facts)

    report = build_report(
        ticker, rev_formatted, risk_counts, risk_snippets, filing.url,
        filing_date=filing.filing_date, revenue_raw=rev_raw,
    )
    if use_cache:
        _write_cache(cache_key, report)
    return report


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_risk_analysis(ticker, use_cache=True):
    """Fetch + analyze the most recent 10-K for `ticker`, write `{ticker}_report.json`."""
    print(f"Analyzing {ticker} for EAI Compliance standards...")

    company = _resolve_company(ticker)
    facts = _with_retries(lambda: company.get_facts(), f"Fetching XBRL facts for '{ticker}'")
    filing = _latest_10k(company, ticker)
    report = _analyze_filing(ticker, filing, facts, use_cache=use_cache)

    with open(f"{ticker}_report.json", "w") as f:
        json.dump(report, f, indent=4)

    return report


def get_historical_risk_analysis(ticker, num_years=5, use_cache=True):
    """Analyze the last `num_years` 10-Ks for `ticker`, write `{ticker}_history.json`.

    Returns a list of reports, newest filing first (matches EDGAR's default
    ordering), each augmented with a "Filing_Date" field so the dashboard can
    plot a real trend line instead of guessing at fiscal years.
    """
    print(f"Pulling {num_years}-year risk history for {ticker}...")

    company = _resolve_company(ticker)
    facts = _with_retries(lambda: company.get_facts(), f"Fetching XBRL facts for '{ticker}'")
    filings = _recent_10ks(company, ticker, num_years)

    history = []
    for filing in filings:
        try:
            report = _analyze_filing(ticker, filing, facts, use_cache=use_cache)
            history.append(report)
            print(f"  ✅ {ticker} {report.get('Filing_Date', '?')} processed")
        except Exception as e:
            print(f"  ❌ {ticker} filing {getattr(filing, 'accession_no', '?')} failed: {e}")

    with open(f"{ticker}_history.json", "w") as f:
        json.dump(history, f, indent=4)

    return history


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
    # `python script1.py`                 -> refreshes every tracked ticker
    # `python script1.py SSNC BLK`        -> refreshes just the tickers you list
    # `python script1.py --history SSNC`  -> pulls a 5-year risk trend for SSNC
    args = sys.argv[1:]
    if args and args[0] == "--history":
        history_targets = args[1:] if len(args) > 1 else TICKERS
        for t in history_targets:
            try:
                get_historical_risk_analysis(t)
            except Exception as e:
                print(f"❌ {t} history failed: {e}\n")
    else:
        targets = args if args else TICKERS
        run(targets)
