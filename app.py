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

# 2. WALLET STATUS
with st.expander("🔐 Sentinel & Drift Wallet Status"):
    sender = st.text_input("Gmail Address", value="sreejan@onebostoncapital.com")
    pwd = st.text_input("App Password", type="password")
    auto_pilot = st.toggle("🚀 ENABLE AUTO-PILOT (Tiered Leverage Active)")
    time_left = 30 - int(time.time() % 30)
    st.info(f"Next Sync: {time_left}s | Scaling: 4/7=2x, 5/7=3x, 6/7=4x, 7/7=5x")

# 3. ANALYSIS & CONSENSUS ENGINE
df, btc_p, err, status = fetch_base_data(st.session_state.chart_tf)

if status:
    price = df['close'].iloc[-1]
    c1, c2, c3 = st.columns(3)
    c1.metric("₿ BTC Price", f"${btc_p:,.2f}")
    c2.metric(f"S SOL Price ({st.session_state.chart_tf})", f"${price:,.2f}")

    # THE 8 JUDGES (Monitoring from 1m up)
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
                if i >= 1: trigger_longs += 1 # 5m to 1d (7 judges total)
            elif p < s and p < e: 
                sig, clr = "🔴 SHORT", "#f44"
                if i >= 1: trigger_shorts += 1
            else: sig, clr = "🟡 WAIT", "#888"
            mcols[i].markdown(f"**{t}**\n\n<span style='color:{clr};'>{sig}</span>", unsafe_allow_html=True)

    # --- TIERED LEVERAGE LOGIC ---
    trigger_count = max(trigger_longs, trigger_shorts)
    
    # Mapping consensus to leverage
    lev_map = {4: 2, 5: 3, 6: 4, 7: 5}
    current_lev = lev_map.get(trigger_count, 0) if trigger_count >= 4 else 0
    
    conv_status = f"⚡ TIER {trigger_count} ({current_lev}x)" if current_lev > 0 else "⏳ SCANNING"
    c3.metric("Execution Target", f"{trigger_count}/7 Judges", conv_status)

    # 4. CHART & NAV
    fig = go.Figure(data=[go.Candlestick(x=df['date'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
    fig.update_layout(template="plotly_dark" if theme=="Dark Mode" else "plotly_white", paper_bgcolor=bg, plot_bgcolor=bg, height=400, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    nav_cols = st.columns(len(tfs))
    for i, tf_opt in enumerate(tfs):
        if nav_cols[i].button(tf_opt, key=f"nav_{tf_opt}"):
            st.session_state.chart_tf = tf_opt
            st.rerun()

    # 5. WAR ROOM
    st.markdown("---")
    st.subheader("✍️ War Room: Tiered Scaling Strategy")
    wc1, wc2, wc3 = st.columns(3)
    entry_trigger = wc1.number_input("Entry Price Trigger", value=float(price))
    tp_val = wc2.number_input("Predefined TP ($)", value=float(price*1.05))
    sl_val = wc3.number_input("Predefined SL ($)", value=float(price*0.97))
    
    def send_sentinel_email(side, entry, tp, sl, consensus, leverage):
        try:
            content = f"SENTINEL TIERED DISPATCH\nSide: {side}\nLev: {leverage}x\nEntry: {entry}\nTP: {tp}\nSL: {sl}\nJudges: {consensus}/7"
            msg = MIMEText(content); msg['Subject'] = f"🛡️ {side} ({leverage}x) - {consensus}/7 Consensus"; msg['From'] = sender; msg['To'] = sender
            server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            server.login(sender, pwd); server.send_message(msg); server.quit()
            return True
        except Exception as e:
            st.error(f"Mail Error: {e}"); return False

    # --- AUTO-PILOT TIERED EXECUTION ---
    if auto_pilot and current_lev > 0:
        side = "LONG" if trigger_longs >= 4 else "SHORT"
        price_met = (side == "LONG" and price >= entry_trigger) or (side == "SHORT" and price <= entry_trigger)
        cooldown_met = (time.time() - st.session_state.last_trade_time > 300)
        
        if price_met and cooldown_met:
            if send_sentinel_email(side, price, tp_val, sl_val, trigger_count, current_lev):
                st.session_state.last_trade_time = time.time()
                st.success(f"Tiered {current_lev}x {side} Trade Dispatched!")

    if st.button("🚀 Force Manual Tiered Alert"):
        if current_lev > 0:
            side = "LONG" if trigger_longs > trigger_shorts else "SHORT"
            send_sentinel_email(side, price, tp_val, sl_val, trigger_count, current_lev)
            st.success(f"Manual {current_lev}x Alert Sent based on {trigger_count}/7 consensus.")
        else: st.warning("Min 4/7 Consensus required for manual trigger.")
