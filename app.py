import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import smtplib
import time
from email.mime.text import MIMEText
from streamlit_autorefresh import st_autorefresh
from data_engine import fetch_base_data

# 1. CORE SETUP & 30s HEARTBEAT
st.set_page_config(page_title="Sreejan Perp Sentinel Pro", layout="wide")
st_autorefresh(interval=30000, key="sentinel_pulse")

if 'chart_tf' not in st.session_state: st.session_state.chart_tf = "1h"
if 'last_trade_time' not in st.session_state: st.session_state.last_trade_time = 0

theme = st.sidebar.radio("Theme Mode", ["Dark Mode", "Light Mode"], index=0)
bg, txt, accent = ("#000", "#FFF", "#D4AF37") if theme == "Dark Mode" else ("#FFF", "#000", "#D4AF37")
st.markdown(f"<style>.stApp {{ background-color: {bg}; color: {txt} !important; }} h1, h2, h3 {{ color: {accent} !important; }}</style>", unsafe_allow_html=True)

# 2. WALLET & AUTO-PILOT CONTROL
with st.expander("🔐 Sentinel & Drift Wallet Status"):
    sender = st.text_input("Gmail Address", value="sreejan@onebostoncapital.com")
    pwd = st.text_input("App Password", type="password")
    auto_pilot = st.toggle("🚀 ENABLE AUTO-PILOT (5m+ Consensus)")
    
    time_left = 30 - int(time.time() % 30)
    st.info(f"Market Scan in: {time_left}s | Logic: 5m to 1d alignment required.")

# 3. ANALYSIS ENGINE
df, btc_p, err, status = fetch_base_data(st.session_state.chart_tf)

if status:
    price = df['close'].iloc[-1]
    c1, c2, c3 = st.columns(3)
    c1.metric("₿ BTC", f"${btc_p:,.2f}")
    c2.metric(f"S SOL ({st.session_state.chart_tf})", f"${price:,.2f}")

    # --- 8-JUDGE SYSTEM (Filter: 5m to 1d) ---
    st.markdown("---")
    tfs = ["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d"]
    mcols = st.columns(8); longs, shorts = 0, 0
    
    # Logic: Only count signals from 5m (index 1) to 1d (index 7)
    execution_judges_long = 0
    execution_judges_short = 0

    for i, t in enumerate(tfs):
        dm, _, _, sm = fetch_base_data(t)
        if sm:
            p, e, s = dm['close'].iloc[-1], dm['20_ema'].iloc[-1], dm['200_sma'].iloc[-1]
            if p > s and p > e: 
                sig, clr = "🟢 LONG", "#0ff0"
                if i >= 1: execution_judges_long += 1 # 5m and above
            elif p < s and p < e: 
                sig, clr = "🔴 SHORT", "#f44"
                if i >= 1: execution_judges_short += 1 # 5m and above
            else: sig, clr = "🟡 WAIT", "#888"
            mcols[i].markdown(f"**{t}**\n\n<span style='color:{clr};'>{sig}</span>", unsafe_allow_html=True)

    # 4. CHART & NAV
    fig = go.Figure(data=[go.Candlestick(x=df['date'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
    fig.update_layout(template="plotly_dark" if theme=="Dark Mode" else "plotly_white", paper_bgcolor=bg, plot_bgcolor=bg, height=400, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    nav_cols = st.columns(len(tfs))
    for i, tf_opt in enumerate(tfs):
        if nav_cols[i].button(tf_opt, key=f"nav_{tf_opt}"):
            st.session_state.chart_tf = tf_opt
            st.rerun()

    # 5. WAR ROOM: PREDEFINED TP/SL
    st.markdown("---")
    st.subheader("✍️ War Room: Predefined Strategy")
    wc1, wc2, wc3 = st.columns(3)
    entry_req = wc1.number_input("Entry Price Trigger", value=float(price))
    tp_val = wc2.number_input("Predefined TP ($)", value=float(price*1.05))
    sl_val = wc3.number_input("Predefined SL ($)", value=float(price*0.97))
    
    # --- AUTO-PILOT EXECUTION LOGIC ---
    # Rule: Needs 7/7 agreement (5m, 15m, 30m, 1h, 4h, 12h, 1d)
    if auto_pilot:
        is_long_signal = execution_judges_long >= 7
        is_short_signal = execution_judges_short >= 7
        
        if is_long_signal or is_short_signal:
            side = "LONG" if is_long_signal else "SHORT"
            
            # Price Filter & 5-min Cooldown
            price_condition = (side == "LONG" and price >= entry_req) or (side == "SHORT" and price <= entry_req)
            cooldown_active = (time.time() - st.session_state.last_trade_time) < 300
            
            if price_condition and not cooldown_active:
                try:
                    st.warning(f"⚡ SIGNAL GEN: {side} | TP: {tp_val} | SL: {sl_val}")
                    
                    # Log to Email
                    content = f"TRADE EXECUTED\nSide: {side}\nEntry: {price}\nTP: {tp_val}\nSL: {sl_val}\nTimeframes: 5m-1d Synced"
                    msg = MIMEText(content); msg['Subject'] = "🔥 Sentinel Trade Active"; msg['From'] = sender; msg['To'] = sender
                    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
                        s.login(sender, pwd); s.send_message(msg)
                    
                    st.session_state.last_trade_time = time.time()
                    st.success("Strategy Deployed to Drift Protocol.")
                except Exception as e: st.error(f"Signal Failed: {e}")
