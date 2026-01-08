import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import smtplib
import time
from email.mime.text import MIMEText
from streamlit_autorefresh import st_autorefresh
from data_engine import fetch_base_data

# 1. HEARTBEAT SETUP
st.set_page_config(page_title="Sreejan Perp Sentinel Pro", layout="wide")
st_autorefresh(interval=30000, key="sentinel_timer") # 30s Refresh

if 'chart_tf' not in st.session_state: st.session_state.chart_tf = "1h"
if 'last_trade_time' not in st.session_state: st.session_state.last_trade_time = 0

theme = st.sidebar.radio("Theme Mode", ["Dark Mode", "Light Mode"], index=0)
bg, txt, accent = ("#000", "#FFF", "#D4AF37") if theme == "Dark Mode" else ("#FFF", "#000", "#D4AF37")

st.markdown(f"<style>.stApp {{ background-color: {bg}; color: {txt} !important; }} h1, h2, h3 {{ color: {accent} !important; }}</style>", unsafe_allow_html=True)

# 2. WALLET STATUS
with st.expander("🔐 Sentinel & Drift Wallet Status"):
    sender = st.text_input("Gmail Address", value="sreejan@onebostoncapital.com")
    pwd = st.text_input("App Password", type="password")
    auto_pilot = st.toggle("🚀 ENABLE AUTO-PILOT")
    
    time_left = 30 - int(time.time() % 30)
    st.info(f"Next automated market scan in: {time_left}s")

# 3. ANALYSIS
df, btc_p, err, status = fetch_base_data(st.session_state.chart_tf)

if status:
    price = df['close'].iloc[-1]
    c1, c2, c3 = st.columns(3)
    c1.metric("₿ BTC", f"${btc_p:,.2f}")
    c2.metric(f"S SOL ({st.session_state.chart_tf})", f"${price:,.2f}")

    # THE 8 JUDGES
    st.markdown("---")
    tfs = ["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d"]
    mcols = st.columns(8); longs, shorts = 0, 0
    for i, t in enumerate(tfs):
        dm, _, _, sm = fetch_base_data(t)
        if sm:
            p, e, s = dm['close'].iloc[-1], dm['20_ema'].iloc[-1], dm['200_sma'].iloc[-1]
            if p > s and p > e: sig, clr, longs = "🟢 LONG", "#0ff0", longs + 1
            elif p < s and p < e: sig, clr, shorts = "🔴 SHORT", "#f44", shorts + 1
            else: sig, clr = "🟡 WAIT", "#888"
            mcols[i].markdown(f"**{t}**\n\n<span style='color:{clr};'>{sig}</span>", unsafe_allow_html=True)

    consensus = max(longs, shorts)
    conv = "STRONG" if consensus >= 6 else "MODERATE"
    c3.metric("Consensus", f"{consensus}/8 Judges", conv)

    # 4. CHART & NAV
    fig = go.Figure(data=[go.Candlestick(x=df['date'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
    fig.update_layout(template="plotly_dark" if theme=="Dark Mode" else "plotly_white", paper_bgcolor=bg, plot_bgcolor=bg, height=450, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    nav_cols = st.columns(len(tfs))
    for i, tf_opt in enumerate(tfs):
        if nav_cols[i].button(tf_opt, key=f"nav_{tf_opt}"):
            st.session_state.chart_tf = tf_opt
            st.rerun()

    # 5. EXECUTION LOGIC
    st.markdown("---")
    st.subheader("✍️ War Room: Drift Auto-Pilot Settings")
    wc1, wc2, wc3 = st.columns(3)
    entry_trigger = wc1.number_input("Target Entry Price", value=float(price))
    tp = wc2.number_input("Take Profit", value=float(price*1.05))
    sl = wc3.number_input("Stop Loss", value=float(price*0.97))

    # --- THE LOGIC GATE ---
    if auto_pilot and conv == "STRONG":
        side = "LONG" if longs >= 6 else "SHORT"
        
        # Check if price condition is met
        price_met = (side == "LONG" and price >= entry_trigger) or (side == "SHORT" and price <= entry_trigger)
        
        # Check if cooldown (5 mins) has passed
        cooldown_met = (time.time() - st.session_state.last_trade_time) > 300
        
        if price_met and cooldown_met:
            try:
                st.warning(f"⚡ AUTO-PILOT: Executing {side} on Drift...")
                # Alert Email
                msg = MIMEText(f"Trade Triggered: {side}\nPrice: {price}\nJudges: {consensus}/8"); msg['Subject'] = "🔥 Drift Auto-Trade Executed"; msg['From'] = sender; msg['To'] = sender
                with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
                    s.login(sender, pwd); s.send_message(msg)
                
                st.session_state.last_trade_time = time.time()
                st.success(f"Trade dispatched! Cooldown active for 5 minutes.")
            except Exception as e: st.error(f"Execution Error: {e}")
