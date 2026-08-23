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
