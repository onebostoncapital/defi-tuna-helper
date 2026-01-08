import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import smtplib
import time
from email.mime.text import MIMEText
from streamlit_autorefresh import st_autorefresh
from data_engine import fetch_base_data

# 1. CORE HEARTBEAT (30s REFRESH)
st.set_page_config(page_title="Sreejan Perp Sentinel Pro", layout="wide")
st_autorefresh(interval=30000, key="sentinel_pulse")

if 'chart_tf' not in st.session_state: st.session_state.chart_tf = "1h"
if 'last_trade_time' not in st.session_state: st.session_state.last_trade_time = 0

theme = st.sidebar.radio("Theme Mode", ["Dark Mode", "Light Mode"], index=0)
bg, txt, accent = ("#000", "#FFF", "#D4AF37") if theme == "Dark Mode" else ("#FFF", "#000", "#D4AF37")
st.markdown(f"<style>.stApp {{ background-color: {bg}; color: {txt} !important; }} h1, h2, h3 {{ color: {accent} !important; }}</style>", unsafe_allow_html=True)

# 2. STATUS & REFRESH COUNTER
with st.expander("🔐 Sentinel & Drift Wallet Status"):
    sender = st.text_input("Gmail Address", value="sreejan@onebostoncapital.com")
    pwd = st.text_input("App Password", type="password", help="Use Gmail App Password, not regular password.")
    auto_pilot = st.toggle("🚀 ENABLE AUTO-PILOT (5/7 Logic Active)")
    
    time_left = 30 - int(time.time() % 30)
    st.info(f"Next Sync: {time_left}s | Rule: 5/7 alignment from 5m+ timeframe triggers trade.")

# 3. ANALYSIS & CONSENSUS ENGINE
df, btc_p, err, status = fetch_base_data(st.session_state.chart_tf)

if status:
    price = df['close'].iloc[-1]
    c1, c2, c3 = st.columns(3)
    c1.metric("₿ BTC Price", f"${btc_p:,.2f}")
    c2.metric(f"S SOL Price ({st.session_state.chart_tf})", f"${price:,.2f}")

    # THE 8 JUDGES
    st.markdown("---")
    tfs = ["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d"]
    mcols = st.columns(8)
    trigger_longs, trigger_shorts = 0, 0

    for i, t in enumerate(tfs):
        dm, _, _, sm = fetch_base_data(t)
        if sm:
            p, e, s = dm['close'].iloc[-1], dm['20_ema'].iloc[-1], dm['200_sma'].iloc[-1]
            if p > s and p > e: 
                sig, clr = "🟢 LONG", "#0ff0"
                if i >= 1: trigger_longs += 1 # 5m to 1d
            elif p < s and p < e: 
                sig, clr = "🔴 SHORT", "#f44"
                if i >= 1: trigger_shorts += 1 # 5m to 1d
            else: sig, clr = "🟡 WAIT", "#888"
            mcols[i].markdown(f"**{t}**\n\n<span style='color:{clr};'>{sig}</span>", unsafe_allow_html=True)

    # RE-ADDED CONSENSUS TAB
    trigger_count = max(trigger_longs, trigger_shorts)
    conv_status = "🔥 TRIGGER READY" if trigger_count >= 5 else "⏳ SCANNING"
    c3.metric("5/7 Execution Judge", f"{trigger_count}/7 Align", conv_status)

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
    st.subheader("✍️ War Room: Drift Strategy")
    wc1, wc2, wc3 = st.columns(3)
    entry_trigger = wc1.number_input("Entry Price Trigger", value=float(price))
    tp_val = wc2.number_input("Predefined TP ($)", value=float(price*1.05))
    sl_val = wc3.number_input("Predefined SL ($)", value=float(price*0.97))
    
    # EMAIL FUNCTION
    def send_sentinel_email(side, entry, tp, sl, consensus):
        try:
            content = f"SENTINEL SIGNAL\nSide: {side}\nEntry: {entry}\nTP: {tp}\nSL: {sl}\nJudges: {consensus}/7"
            msg = MIMEText(content); msg['Subject'] = f"🛡️ {side} Alert Executed"; msg['From'] = sender; msg['To'] = sender
            server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            server.login(sender, pwd)
            server.send_message(msg)
            server.quit()
            return True
        except Exception as e:
            st.error(f"Mail Error: {e}")
            return False

    # --- AUTO-PILOT LOGIC (5/7 RULE) ---
    if auto_pilot:
        is_long = trigger_longs >= 5
        is_short = trigger_shorts >= 5
        if (is_long or is_short) and (time.time() - st.session_state.last_trade_time > 300):
            side = "LONG" if is_long else "SHORT"
            if (side == "LONG" and price >= entry_trigger) or (side == "SHORT" and price <= entry_trigger):
                if send_sentinel_email(side, price, tp_val, sl_val, trigger_count):
                    st.session_state.last_trade_time = time.time()
                    st.success(f"Auto-Trade {side} Dispatched!")

    # MANUAL TRIGGER FIX
    if st.button("🚀 MANUAL: Trigger Alert Now"):
        side = "LONG" if trigger_longs > trigger_shorts else "SHORT"
        if send_sentinel_email(side, price, tp_val, sl_val, trigger_count):
            st.success("Manual Email Sentinel Triggered Successfully!")
