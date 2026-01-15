import streamlit as st
import json
import os

# 1. Page Configuration
st.set_page_config(page_title="EAI Compliance Monitor", page_icon="🏦", layout="wide")

# 2. Sidebar for Controls
st.sidebar.header("Control Panel")
st.sidebar.markdown("Use this panel to switch between tracked companies.")

# Let the user pick a ticker
ticker_list = ["SSNC", "BLK", "STT", "ENV"]
selected_ticker = st.sidebar.selectbox("Select Target Company", ticker_list)

st.sidebar.divider()
st.sidebar.write("Developed for EAI Compliance Standards")

# 3. Main Dashboard Area
st.title("🏦 Financial Compliance Monitor")
st.markdown(f"Currently viewing: **{selected_ticker}**")

# 4. Load Data based on selection
report_file = f"{selected_ticker}_report.json"

if os.path.exists(report_file):
    with open(report_file, 'r') as f:
        data = json.load(f)

    # UI Layout
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="Ticker Symbol", value=data['Company'])
        st.write(f"🔗 [Access Original SEC Filing]({data['Source_URL']})")
    with col2:
        st.metric(label="Calculated Revenue", value=data['Revenue'])

    st.subheader("⚠️ Regulatory Risk Analysis")
    for risk in data['Risk_Keywords_Found']:
        st.warning(f"Detected keyword: **{risk.capitalize()}**")

    st.divider()
    st.info(f"**Audit Status:** {data['Status']}")

else:
    st.error(f"No report found for {selected_ticker}.")
    st.write(f"Please run `python script1.py` for {selected_ticker} to generate the data.")