import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import smtplib
import json
import time
from email.mime.text import MIMEText
from streamlit_autorefresh import st_autorefresh
from data_engine import fetch_base_data

# 1. THE HEARTBEAT (30s Auto-Refresh)
st.set_page_config(page_title="Sreejan Perp Sentinel Pro", layout="wide")
refresh_interval = 30000 # 30 seconds
st_autorefresh(interval=refresh_interval, key="sentinel_heartbeat")

# Persistent State
if 'chart_tf' not in st.session_state: st.session_state.chart_tf = "1h"
if 'last_trade_time' not in st.session_state: st.session_state.last_trade_time = 0

theme = st.sidebar.radio("Theme Mode", ["Dark Mode", "Light Mode"], index=0)
bg, txt, accent = ("#000", "#FFF", "#D4AF37") if theme == "Dark Mode" else ("#FFF", "#000", "#D4AF37")

st.markdown(f"<style>.stApp {{ background-color: {bg}; color: {txt} !important; }} h1, h2, h3 {{ color: {accent} !important; }}</style>", unsafe_allow_html=True)

# 2. STATUS & SECRETS
with st.expander("🔐 Sentinel & Drift Wallet Status"):
    sender = st.text_input("Gmail Address", value="sreejan@onebostoncapital.com")
    pwd = st.text_input("App Password", type="password")
    auto_pilot = st.toggle("🚀 ENABLE AUTO-PILOT")
    
    # COUNTDOWN TIMER VISUAL
    time_passed = int(time.time() % 30)
    remaining = 30 - time_passed
    st.write(f"⏱️ Next Market Scan in: **{remaining} seconds**")

# 3. HEADER & JUDGE SYSTEM (The 8 Consensus Judges)
df, btc_p, err, status = fetch_base_data(st.session_state.chart_tf)

if status:
    price = df['close'].iloc[-1]
    c1, c2, c3 = st.columns(3)
    c1.metric("₿ BTC Benchmark", f"${btc_p:,.2f}")
    c2.metric(f"S SOL Price ({st.session_state.chart_tf})", f"${price:,.2f}")

    st.markdown("---")
    tfs = ["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d"]
    mcols = st.columns(8); longs, shorts = 0, 0
    
    # Gathering Consensus
    for i, t in enumerate(tfs):
        d_m, _, _, s_m = fetch_base_data(t)
        if s_m:
            pm, e20, s200 = d_m['close'].iloc[-1], d_m['20_ema'].iloc[-1], d_m['200_sma'].iloc[-1]
            if pm > s200 and pm > e20: sig, color, longs = "🟢 LONG", "#0ff0", longs + 1
            elif pm < s200 and pm < e20: sig, color, shorts = "🔴 SHORT", "#f44", shorts + 1
            else: sig, color = "🟡 WAIT", "#888"
            mcols[i].markdown(f"**{t}**\n\n<span style='color:{color};'>{sig}</span>", unsafe_allow_html=True)

    consensus_score = max(longs, shorts)
    conv = "STRONG" if consensus_score >= 6 else "MODERATE"
    c3.metric("Consensus", f"{consensus_score}/8 Judges", conv)

    # 4. CHART
    fig = go.Figure(data=[go.Candlestick(x=df['date'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
    fig.add_trace(go.Scatter(x=df['date'], y=df['20_ema'], name="20 EMA", line=dict(color="#854CE6", width=2)))
    fig.add_trace(go.Scatter(x=df['date'], y=df['200_sma'], name="200 SMA", line=dict(color="#FF9900", dash='dot', width=2)))
    fig.update_layout(template="plotly_dark" if theme=="Dark Mode" else "plotly_white", paper_bgcolor=bg, plot_bgcolor=bg, height=450, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    # 5. NAVIGATION (BELOW CHART)
    nav_cols = st.columns(len(tfs))
    for i, tf_opt in enumerate(tfs):
        if nav_cols[i].button(tf_opt, key=f"nav_{tf_opt}"):
            st.session_state.chart_tf = tf_opt
            st.rerun()

    # 6. WAR ROOM
    st.markdown("---")
    st.subheader("✍️ War Room: Sentinel Deployment")
    lev = st.sidebar.slider("Leverage", 1.0, 50.0, 5.0)
    
    wc1, wc2, wc3 = st.columns(3)
    entry_req = wc1.number_input("Entry Price Trigger", value=float(price))
    tp_req = wc2.number_input("Take Profit", value=float(price*1.05))
    sl_req = wc3.number_input("Stop Loss", value=float(price*0.97))
    
    # AUTO-PILOT ENGINE
    if auto_pilot and conv == "STRONG":
        side = "LONG" if longs >= 6 else "SHORT"
        if ((side == "LONG" and price >= entry_req) or (side == "SHORT" and price <= entry_req)):
            if (time.time() - st.session_state.last_trade_time) > 300:
                try:
                    st.warning(f"🚀 AUTO-TRADE SIGNAL DETECTED: {side}")
                    content = f"SENTINEL DEPLOYED\nSide: {side}\nPrice: {price}\nJudges: {consensus_score}/8"
                    msg = MIMEText(content); msg['Subject'] = "🔥 Drift Auto-Pilot Log"; msg['From'] = sender; msg['To'] = sender
                    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
                        s.login(sender, pwd); s.send_message(msg)
                    st.session_state.last_trade_time = time.time()
                except Exception as e: st.error(f"Signal Fail: {e}")

    if st.button("🚀 Execute Manual Trade Alert"):
        st.success("Trade alert dispatched to your email.")
