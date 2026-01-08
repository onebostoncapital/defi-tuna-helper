import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from datetime import datetime
import streamlit.components.v1 as components
import smtplib
from email.mime.text import MIMEText
from data_engine import fetch_base_data

# 1. CORE IDENTITY
st.set_page_config(page_title="Sreejan Perp Sentinel Pro", layout="wide")

# Master Lock
if 'perp_entry' not in st.session_state: st.session_state.perp_entry = 0.0
if 'perp_tp' not in st.session_state: st.session_state.perp_tp = 0.0
if 'perp_sl' not in st.session_state: st.session_state.perp_sl = 0.0
if 'chart_tf' not in st.session_state: st.session_state.chart_tf = "1h"

theme = st.sidebar.radio("Theme Mode", ["Dark Mode", "Light Mode"], index=0)
bg = "#000000" if theme == "Dark Mode" else "#FFFFFF"
txt = "#FFFFFF" if theme == "Dark Mode" else "#000000"
accent = "#D4AF37"

st.markdown(f"<style>.stApp {{ background-color: {bg}; color: {txt} !important; }} h1, h2, h3 {{ color: {accent} !important; }} .guide-box {{ padding: 15px; border-radius: 10px; background: #1a1a1a; border-left: 5px solid {accent}; margin-bottom: 20px; color: white; }}</style>", unsafe_allow_html=True)

# 2. EMAIL SETUP
with st.expander("🔐 Email Sentinel Setup (Gmail Only)"):
    sender_email = st.text_input("Your Gmail Address")
    app_password = st.text_input("16-Digit App Password", type="password")
    if st.button("Save & Test Connection"):
        try:
            msg = MIMEText("Testing the Magic Robot Guard!")
            msg['Subject'] = "✅ Robot Guard Test"; msg['From'] = sender_email; msg['To'] = sender_email
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(sender_email, app_password); server.send_message(msg)
            st.success("Connection Saved!")
        except Exception as e: st.error(f"Error: {e}")

# 3. DATA FETCHING
st.title("🛡️ Sreejan Perp Forecaster Sentinel")
tfs = ["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d"]
nav_cols = st.columns(8)
for i, tf_opt in enumerate(tfs):
    if nav_cols[i].button(tf_opt): st.session_state.chart_tf = tf_opt

with st.spinner('Gathering Market Intelligence...'):
    df, btc_p, err, status = fetch_base_data(st.session_state.chart_tf)

if not status:
    st.warning(f"⚠️ Binance is busy or Cloud server is blocked. Error: {err}")
    if st.button("Try Reconnecting to Binance"): st.rerun()
else:
    price = df['close'].iloc[-1]
    c1, c2, c3 = st.columns(3)
    c1.metric("₿ BTC", f"${btc_p:,.2f}")
    c2.metric(f"S SOL ({st.session_state.chart_tf})", f"${price:,.2f}")

    # 4. STRATEGY GUIDE
    st.markdown("---")
    with st.expander("📖 How to Find the Strongest Signals", expanded=True):
        st.markdown(f'<div class="guide-box"><strong>Look for Alignment:</strong> Judges agree! <br>⚪ 1-3: Low | 🟡 4-5: Moderate | 🔥 6-8: <strong>Strong Power Signal!</strong></div>', unsafe_allow_html=True)

    # 5. RADAR & CHART
    mcols = st.columns(8); longs, shorts = 0, 0
    for i, t in enumerate(tfs):
        try:
            d_m, _, _, s_m = fetch_base_data(t)
            if s_m:
                pm, e20, s200 = d_m['close'].iloc[-1], d_m['20_ema'].iloc[-1], d_m['200_sma'].iloc[-1]
                if pm > s200 and pm > e20: sig, color, longs = "🟢 LONG", "#0ff0", longs + 1
                elif pm < s200 and pm < e20: sig, color, shorts = "🔴 SHORT", "#f44", shorts + 1
                else: sig, color = "🟡 WAIT", "#888"
                mcols[i].markdown(f"**{t}**\n\n<span style='color:{color};'>{sig}</span>", unsafe_allow_html=True)
        except: pass

    conv = "STRONG" if (longs >= 6 or shorts >= 6) else "MODERATE"
    c3.metric("Consensus", f"{max(longs, shorts)}/8 Alignment", conv)

    fig = go.Figure(data=[go.Candlestick(x=df['date'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
    fig.add_trace(go.Scatter(x=df['date'], y=df['20_ema'], name="20 EMA", line=dict(color="#854CE6")))
    fig.add_trace(go.Scatter(x=df['date'], y=df['200_sma'], name="200 SMA", line=dict(color="#FF9900", dash='dot')))
    fig.update_layout(template="plotly_dark" if theme=="Dark Mode" else "plotly_white", paper_bgcolor=bg, plot_bgcolor=bg, height=500, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)
