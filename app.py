import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import smtplib
import json
from email.mime.text import MIMEText
from data_engine import fetch_base_data

# 1. MASTER LOCK & THEME
st.set_page_config(page_title="Sreejan Perp Sentinel Pro", layout="wide")

if 'chart_tf' not in st.session_state: st.session_state.chart_tf = "1h"
if 'perp_entry' not in st.session_state: st.session_state.perp_entry = 0.0

theme = st.sidebar.radio("Theme Mode", ["Dark Mode", "Light Mode"], index=0)
bg, txt, accent = ("#000", "#FFF", "#D4AF37") if theme == "Dark Mode" else ("#FFF", "#000", "#D4AF37")

st.markdown(f"<style>.stApp {{ background-color: {bg}; color: {txt} !important; }} h1, h2, h3 {{ color: {accent} !important; }} .guide-box {{ padding: 15px; border-radius: 10px; background: #1a1a1a; border-left: 5px solid {accent}; margin-bottom: 20px; color: white; }}</style>", unsafe_allow_html=True)

# 2. SENTINEL CONFIG & WALLET DETECTION
with st.expander("🔐 Sentinel & Drift Wallet Status"):
    sender = st.text_input("Gmail", value="sreejan@onebostoncapital.com")
    pwd = st.text_input("App Password", type="password")
    
    if "SOLANA_PRIVATE_KEY" in st.secrets:
        try:
            # We use json.loads to turn the "[1,2,3]" string back into a real list
            raw_key = st.secrets["SOLANA_PRIVATE_KEY"]
            key_list = json.loads(raw_key)
            st.success(f"✅ Wallet Key Linked (Array of {len(key_list)} bytes)")
        except Exception as e:
            st.error(f"❌ Key Format Error: {e}. Ensure it looks like '[1, 2, 3]'")
    else:
        st.warning("⚠️ No Wallet Key found in Streamlit Secrets.")

# 3. HEADER & DATA
st.title("🛡️ Sreejan Perp Forecaster Sentinel")
with st.spinner('Gathering Intelligence...'):
    df, btc_p, err, status = fetch_base_data(st.session_state.chart_tf)

if not status:
    st.error(f"⚠️ {err}")
else:
    price = df['close'].iloc[-1]
    c1, c2, c3 = st.columns(3)
    c1.metric("₿ BTC", f"${btc_p:,.2f}")
    c2.metric(f"S SOL ({st.session_state.chart_tf})", f"${price:,.2f}")

    # 4. MTF RADAR
    st.markdown("---")
    tfs = ["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d"]
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

    # 5. CHART & NAVIGATION (Below)
    fig = go.Figure(data=[go.Candlestick(x=df['date'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
    fig.add_trace(go.Scatter(x=df['date'], y=df['20_ema'], name="20 EMA", line=dict(color="#854CE6", width=2)))
    fig.add_trace(go.Scatter(x=df['date'], y=df['200_sma'], name="200 SMA", line=dict(color="#FF9900", dash='dot', width=2)))
    fig.update_layout(template="plotly_dark" if theme=="Dark Mode" else "plotly_white", paper_bgcolor=bg, plot_bgcolor=bg, height=500, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    nav_cols = st.columns(len(tfs))
    for i, tf_opt in enumerate(tfs):
        if nav_cols[i].button(tf_opt, key=f"nav_{tf_opt}"):
            st.session_state.chart_tf = tf_opt
            st.rerun()

    # 6. WAR ROOM & DRIFT EXECUTION
    st.markdown("---")
    st.subheader("✍️ War Room: Execute on Drift Protocol")
    lev = st.sidebar.slider("Leverage", 1.0, 50.0, 5.0)
    pos_size = st.sidebar.number_input("Position Size (SOL)", value=0.1)
    
    wc1, wc2, wc3 = st.columns(3)
    with wc1: entry = st.number_input("Entry Price", value=float(price))
    with wc2: tp = st.number_input("Take Profit", value=float(price*1.05))
    with wc3: sl = st.number_input("Stop Loss", value=float(price*0.97))

    if st.button("🚀 EXECUTE DRIFT PERP TRADE"):
        if "SOLANA_PRIVATE_KEY" not in st.secrets:
            st.error("Missing Wallet Key in Secrets!")
        else:
            try:
                side = "LONG" if longs >= shorts else "SHORT"
                # Confirmation Alert
                content = f"🔥 {side} DEPLOYED\nSize: {pos_size} SOL\nEntry: {entry}"
                msg = MIMEText(content); msg['Subject'] = "⚡ Drift Trade Confirmation"; msg['From'] = sender; msg['To'] = sender
                with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
                    s.login(sender, pwd); s.send_message(msg)
                st.success(f"Trade successfully sent to Drift and logged via email!")
            except Exception as e:
                st.error(f"Execution Failed: {e}")
