import streamlit as st
import json
import os
from datetime import datetime

from script1 import get_risk_analysis, TICKERS

# 1. Page Configuration
st.set_page_config(page_title="EAI Compliance Monitor", page_icon="🏦", layout="wide")

# Icon per risk category — used in chips, the expander, and context snippets
RISK_ICONS = {
    "litigation": "⚖️",
    "regulatory": "📋",
    "cybersecurity": "🔒",
    "debt": "💰",
    "competition": "🥊",
}

# 2. Styling
st.markdown("""
<style>
.hero {
    background: linear-gradient(135deg, #1e3a5f 0%, #2c5282 50%, #1a365d 100%);
    padding: 2rem 2.2rem;
    border-radius: 14px;
    margin-bottom: 1.6rem;
    border: 1px solid rgba(255,255,255,0.08);
}
.hero h1 {
    margin: 0;
    font-size: 2rem;
    color: #ffffff;
}
.hero p {
    margin: 0.4rem 0 0 0;
    color: #cbd5e1;
    font-size: 1rem;
}
.metric-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px;
    padding: 1.1rem 1.3rem;
    text-align: left;
}
.metric-card .label {
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: #94a3b8;
    margin-bottom: 0.3rem;
}
.metric-card .value {
    font-size: 1.6rem;
    font-weight: 700;
    color: #f1f5f9;
}
.risk-chip {
    display: inline-block;
    padding: 6px 14px;
    margin: 4px 6px 4px 0;
    border-radius: 999px;
    background: #fff3cd;
    color: #7a5b00;
    font-weight: 600;
    font-size: 0.85rem;
    border: 1px solid #ffe08a;
}
.severity-badge {
    display: inline-block;
    padding: 5px 14px;
    border-radius: 999px;
    font-weight: 700;
    font-size: 0.85rem;
    letter-spacing: 0.02em;
}
.severity-low { background: #d4edda; color: #155724; }
.severity-medium { background: #fff3cd; color: #7a5b00; }
.severity-high { background: #f8d7da; color: #721c24; }
.status-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 6px;
    background: #d4edda;
    color: #155724;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

# 3. Sidebar for Controls
st.sidebar.header("Control Panel")
st.sidebar.markdown("Type any ticker to look it up, or use a quick pick below.")

# Free-text entry — works for any public company, not just the tracked list
if "active_ticker" not in st.session_state:
    st.session_state.active_ticker = TICKERS[0]

typed = st.sidebar.text_input("Enter Ticker Symbol", value=st.session_state.active_ticker).strip().upper()
st.session_state.active_ticker = typed

st.sidebar.caption("Quick picks:")
quick_cols = st.sidebar.columns(len(TICKERS))
for col, t in zip(quick_cols, TICKERS):
    if col.button(t, use_container_width=True):
        st.session_state.active_ticker = t
        st.rerun()

selected_ticker = st.session_state.active_ticker
report_file = f"{selected_ticker}_report.json"

if st.sidebar.button("🔄 Generate / Refresh Report", use_container_width=True, disabled=not selected_ticker):
    with st.spinner(f"Pulling latest 10-K data for {selected_ticker}..."):
        try:
            get_risk_analysis(selected_ticker)
            st.sidebar.success(f"{selected_ticker} report updated.")
        except Exception as e:
            st.sidebar.error(f"Couldn't fetch {selected_ticker}: {e}")

if os.path.exists(report_file):
    updated = datetime.fromtimestamp(os.path.getmtime(report_file)).strftime("%b %d, %Y %I:%M %p")
    st.sidebar.caption(f"Last updated: {updated}")

st.sidebar.divider()
st.sidebar.write("Developed for EAI Compliance Standards")

# 4. Hero Header
st.markdown(f"""
<div class="hero">
    <h1>🏦 Financial Compliance Monitor</h1>
    <p>Automated risk-factor analysis from live SEC 10-K filings — currently viewing <strong>{selected_ticker}</strong></p>
</div>
""", unsafe_allow_html=True)

with st.expander("ℹ️ How to read this dashboard", expanded=False):
    st.markdown("""
    1. **Pick a company** in the sidebar (ticker symbol, e.g. `AAPL`, `SSNC`) and hit **Generate/Refresh Report**.
    2. The app pulls that company's **most recent annual report (10-K)** directly from the SEC.
    3. **Calculated Revenue** comes straight from the company's official reported financial data (XBRL "Revenues" tag).
    4. **Risk Mentions** counts how often the filing's text uses each risk-category word below — it's a
       *frequency count of the raw filing text*, not a proprietary risk score. Nearly every 10-K touches on
       all five categories (it's required disclosure), so what matters is *how often*, not whether it's mentioned at all.
    5. The **Low / Medium / High** badge is a simple total-count threshold, meant as a quick visual cue —
       not a calibrated risk model.
    """)

# 5. Load Data based on selection
if os.path.exists(report_file):
    with open(report_file, 'r') as f:
        data = json.load(f)

    risk_counts = data.get('Risk_Keyword_Counts', {})
    risk_snippets = data.get('Risk_Keyword_Snippets', {})
    total_mentions = sum(risk_counts.values())

    # simple severity banding purely on total mention count — a rough visual cue, not a scored risk model
    if total_mentions < 100:
        severity, sev_class = "Low", "severity-low"
    elif total_mentions < 400:
        severity, sev_class = "Medium", "severity-medium"
    else:
        severity, sev_class = "High", "severity-high"

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""<div class="metric-card"><div class="label">Ticker Symbol</div>
        <div class="value">{data['Company']}</div></div>""", unsafe_allow_html=True)
        st.caption("The company currently loaded below.")
    with col2:
        st.markdown(f"""<div class="metric-card"><div class="label">Calculated Revenue</div>
        <div class="value">{data['Revenue']}</div></div>""", unsafe_allow_html=True)
        st.caption("Most recently reported annual revenue, from the company's official SEC data.")
    with col3:
        st.markdown(f"""<div class="metric-card"><div class="label">Total Risk Mentions</div>
        <div class="value">{total_mentions} <span class="severity-badge {sev_class}">{severity}</span></div></div>""",
        unsafe_allow_html=True)
        st.caption("Combined count of all 5 risk keywords across the filing's text — see below for the breakdown.")

    st.markdown("")
    st.markdown(f"🔗 [Access Original SEC Filing]({data['Source_URL']})")

    st.subheader("⚠️ Regulatory Risk Analysis")
    st.caption(
        "Each badge below shows how many times that word appears in the filing "
        "(e.g. \"Debt × 334\" means the word \"debt\" appears 334 times) — it's a "
        "raw mention count, not a severity score. Mention frequency, not presence, "
        "is what differentiates one filing from another, since almost every 10-K "
        "touches on all five boilerplate risk categories at least once."
    )
    if risk_counts:
        sorted_risks = sorted(risk_counts.items(), key=lambda x: x[1], reverse=True)

        chips = "".join(
            f"<span class='risk-chip'>{RISK_ICONS.get(word, '')} {word.capitalize()} × {count}</span>"
            for word, count in sorted_risks
        )
        st.markdown(chips, unsafe_allow_html=True)

        st.caption("Ranked by mention count, highest first:")
        st.bar_chart({word.capitalize(): count for word, count in sorted_risks})

        with st.expander("See filing context for each keyword"):
            st.caption("The sentence surrounding the first mention of each word in the filing.")
            for word, count in sorted_risks:
                st.markdown(f"**{RISK_ICONS.get(word, '')} {word.capitalize()}** ({count} mentions)")
                st.caption(risk_snippets.get(word, ""))
    else:
        st.write("No flagged keywords found in the latest filing.")

    st.divider()
    st.markdown(f"<span class='status-badge'>Audit Status: {data['Status']}</span>", unsafe_allow_html=True)

else:
    st.warning(f"No report found for **{selected_ticker}** yet.")
    st.write(
        "Click **Generate / Refresh Report** in the sidebar to pull live data, "
        f"or run `python script1.py {selected_ticker}` from the terminal."
    )
