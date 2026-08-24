import json
import time

import pytest

import script1
from script1 import (
    clean_filing_text,
    count_risk_keywords,
    extract_revenue,
    build_report,
    _cache_key,
    _read_cache,
    _write_cache,
)


# ---------------------------------------------------------------------------
# clean_filing_text
# ---------------------------------------------------------------------------

def test_clean_filing_text_strips_html_and_lowercases():
    raw = "<html><body><p>We face <b>LITIGATION</b> risk.</p></body></html>"
    assert clean_filing_text(raw) == "we face litigation risk."


def test_clean_filing_text_collapses_whitespace():
    raw = "<div>Line one</div>\n\n\n<div>   Line   two</div>"
    cleaned = clean_filing_text(raw)
    assert "  " not in cleaned
    assert "line one" in cleaned and "line two" in cleaned


def test_clean_filing_text_excludes_hidden_xbrl_tag_substrings():
    # The tag name itself contains "debt" but isn't visible filing text —
    # BeautifulSoup's get_text() should not surface tag attribute values.
    raw = '<span data-tag="longtermdebtandcapitalleaseobligations">Total: $5</span>'
    cleaned = clean_filing_text(raw)
    assert "debt" not in cleaned


# ---------------------------------------------------------------------------
# count_risk_keywords
# ---------------------------------------------------------------------------

def test_count_risk_keywords_basic_counts():
    text = "litigation litigation regulatory debt debt debt"
    counts, snippets = count_risk_keywords(text)
    assert counts == {"litigation": 2, "regulatory": 1, "debt": 3}
    assert "cybersecurity" not in counts
    assert "competition" not in counts


def test_count_risk_keywords_word_boundaries():
    # "indebtedness" and "competitive" should NOT count as "debt"/"competition"
    text = "our indebtedness is high and the competitive landscape is tough"
    counts, _ = count_risk_keywords(text)
    assert counts == {}


def test_count_risk_keywords_is_case_sensitive_on_pre_lowered_text():
    # count_risk_keywords assumes the caller already lowercased (clean_filing_text
    # does this) — verify it matches lowercase input as expected.
    text = "debt debt debt"
    counts, _ = count_risk_keywords(text)
    assert counts["debt"] == 3


def test_count_risk_keywords_snippet_captures_context():
    text = "some padding text here " + "cybersecurity incident occurred" + " more padding text"
    counts, snippets = count_risk_keywords(text)
    assert counts["cybersecurity"] == 1
    assert "cybersecurity incident occurred" in snippets["cybersecurity"]
    assert snippets["cybersecurity"].startswith("...")
    assert snippets["cybersecurity"].endswith("...")


def test_count_risk_keywords_custom_keyword_list():
    text = "fraud fraud waste"
    counts, _ = count_risk_keywords(text, keywords=["fraud", "waste", "abuse"])
    assert counts == {"fraud": 2, "waste": 1}


def test_count_risk_keywords_empty_text_returns_empty():
    counts, snippets = count_risk_keywords("")
    assert counts == {}
    assert snippets == {}


# ---------------------------------------------------------------------------
# extract_revenue
# ---------------------------------------------------------------------------

class _StubFactSeries:
    def __init__(self, values):
        import pandas as pd
        self.data = pd.DataFrame({"val": values})


class _StubFacts:
    def __init__(self, available):
        # available: dict of tag -> list of values, or tag missing entirely
        self._available = available

    def get_fact(self, tag):
        if tag not in self._available:
            raise KeyError(tag)
        return _StubFactSeries(self._available[tag])


def test_extract_revenue_uses_first_matching_tag():
    facts = _StubFacts({"Revenues": [100, 200, 12345]})
    formatted, raw = extract_revenue(facts)
    assert formatted == "$12,345"
    assert raw == 12345


def test_extract_revenue_falls_back_to_later_tag():
    facts = _StubFacts({"SalesRevenueNet": [999]})
    formatted, raw = extract_revenue(facts)
    assert formatted == "$999"
    assert raw == 999


def test_extract_revenue_no_matching_tag():
    facts = _StubFacts({})
    formatted, raw = extract_revenue(facts)
    assert formatted == "Check 10-K Manual (Custom Revenue Tag)"
    assert raw is None


# ---------------------------------------------------------------------------
# build_report
# ---------------------------------------------------------------------------

def test_build_report_shape():
    report = build_report("SSNC", "$1,000", {"debt": 3}, {"debt": "...snippet..."},
                           "https://example.com/filing", filing_date="2024-02-01")
    assert report["Company"] == "SSNC"
    assert report["Revenue"] == "$1,000"
    assert report["Risk_Keyword_Counts"] == {"debt": 3}
    assert report["Source_URL"] == "https://example.com/filing"
    assert report["Filing_Date"] == "2024-02-01"
    assert report["Status"] == "Verified via Fact-Check"


def test_build_report_omits_filing_date_when_not_given():
    report = build_report("SSNC", "$1,000", {}, {}, "https://example.com/filing")
    assert "Filing_Date" not in report


# ---------------------------------------------------------------------------
# cache helpers
# ---------------------------------------------------------------------------

def test_cache_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(script1, "CACHE_DIR", tmp_path / ".cache")
    key = _cache_key("SSNC", "0001-24-000123")
    assert _read_cache(key) is None

    _write_cache(key, {"Company": "SSNC"})
    cached = _read_cache(key)
    assert cached == {"Company": "SSNC"}


def test_cache_respects_ttl(tmp_path, monkeypatch):
    monkeypatch.setattr(script1, "CACHE_DIR", tmp_path / ".cache")
    key = _cache_key("SSNC", "0001-24-000123")
    _write_cache(key, {"Company": "SSNC"})

    # Fresh write should be readable with a generous TTL...
    assert _read_cache(key, ttl_seconds=3600) is not None
    # ...but treated as stale once it's older than the TTL.
    path = script1._cache_path(key)
    old_time = time.time() - 10
    import os
    os.utime(path, (old_time, old_time))
    assert _read_cache(key, ttl_seconds=1) is None


def test_cache_key_differs_by_accession_number():
    key_a = _cache_key("SSNC", "0001-24-000123")
    key_b = _cache_key("SSNC", "0001-24-000999")
    assert key_a != key_b


def test_cache_key_differs_by_ticker():
    key_a = _cache_key("SSNC", "0001-24-000123")
    key_b = _cache_key("BLK", "0001-24-000123")
    assert key_a != key_b


def test_read_cache_survives_corrupt_json(tmp_path, monkeypatch):
    monkeypatch.setattr(script1, "CACHE_DIR", tmp_path / ".cache")
    key = _cache_key("SSNC", "acc")
    path = script1._cache_path(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not valid json")
    assert _read_cache(key) is None
