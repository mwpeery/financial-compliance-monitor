# Financial Compliance & Risk Monitor

Live app: https://mwpeery-financial-compliance-monitor.streamlit.app/

A Streamlit dashboard that pulls a company's 10-K filings straight from SEC EDGAR and counts how often it mentions five common risk topics: litigation, regulatory, cybersecurity, debt, and competition. Almost every 10-K touches on all five somewhere in the boilerplate, so a plain yes/no check doesn't tell you much... how often a topic comes up, and where, is more useful.

## What it does

- Pulls the latest 10-K for a ticker and shows revenue plus risk-keyword counts, with the surrounding sentence for context.
- Pulls the last several years of filings for one company and charts how those keyword counts move over time.
- Compares risk mentions and revenue across companies that YOU pick.
- Caches processed filings locally so it isn't re-downloading the same filing from EDGAR every time.
- Retries EDGAR requests a couple times before giving up instead of just crashing.

## Running it

```bash
pip install -r requirements.txt
streamlit run app.py
```

To pull a report from the command line instead of the UI:

```bash
python script1.py SSNC
python script1.py --history SSNC   # last 5 years of filings
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

No network calls in the test suite... just the keyword-matching, HTML-cleaning, and caching logic. Runs in CI on every push and PR.

## Built with

Python, Streamlit, pandas, Altair, edgartools, pytest.
