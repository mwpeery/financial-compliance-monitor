import streamlit as st
import json
import os
from datetime import datetime

from script1 import get_risk_analysis, TICKERS

# 1. Page Configuration
st.set_page_config(page_title="EAI Compliance Monitor", page_icon="🏦", layout="wide")

# 2. Styling — pill-style risk badges and a status tag instead of stacked warning boxes
st.markdown("""
<style>
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

# 4. Main Dashboard Area
st.title("🏦 Financial Compliance Monitor")
st.markdown(f"Currently viewing: **{selected_ticker}**")

# 5. Load Data based on selection
if os.path.exists(report_file):
    with open(report_file, 'r') as f:
        data = json.load(f)

    risk_counts = data.get('Risk_Keyword_Counts', {})
    risk_snippets = data.get('Risk_Keyword_Snippets', {})

    col1, col2, col3 = st.columns(3)
    col1.metric("Ticker Symbol", data['Company'])
    col2.metric("Calculated Revenue", data['Revenue'])
    col3.metric("Total Risk Mentions", sum(risk_counts.values()))

    st.markdown(f"🔗 [Access Original SEC Filing]({data['Source_URL']})")

    st.subheader("⚠️ Regulatory Risk Analysis")
    st.caption(
        "Mention frequency, not presence — most 10-Ks touch on all of these "
        "boilerplate risk categories, so counting mentions is what actually "
        "differentiates one filing from another."
    )
    if risk_counts:
        sorted_risks = sorted(risk_counts.items(), key=lambda x: x[1], reverse=True)

        chips = "".join(
            f"<span class='risk-chip'>{word.capitalize()} × {count}</span>"
            for word, count in sorted_risks
        )
        st.markdown(chips, unsafe_allow_html=True)

        st.bar_chart({word.capitalize(): count for word, count in sorted_risks})

        with st.expander("See filing context for each keyword"):
            for word, count in sorted_risks:
                st.markdown(f"**{word.capitalize()}** ({count} mentions)")
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
