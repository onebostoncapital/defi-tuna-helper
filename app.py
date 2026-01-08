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

# Persistent State for "Separate Positions" Visibility
if 'chart_tf' not in st.session_state: st.session_state.chart_tf = "1h"
if 'last_trade_time' not in st.session_state: st.session_state.last_trade_time = 0
if 'active_trades' not in st.session_state: st.session_state.active_trades = []

theme = st.sidebar.radio("Theme Mode", ["Dark Mode", "Light Mode"], index=0)
bg, txt, accent = ("#000", "#FFF", "#D4AF37") if theme == "Dark Mode" else ("#FFF", "#000", "#D4AF37")
st.markdown(f"<style>.stApp {{ background-color: {bg}; color: {txt} !important; }} h1, h2, h3 {{ color: {accent} !important; }}</style>", unsafe_allow_html=True)

# 2. WALLET & CAPITAL CONFIG
with st.expander("🔐 Sentinel & Drift Wallet Status"):
    sender = st.text_input("Gmail Address", value="sreejan@onebostoncapital.com")
    pwd = st.text_input("App Password", type="password")
    total_capital = st.number_input("Current Drift Equity ($)", value=1000.0, help="Total available capital in your Drift sub-account.")
    trade_size = total_capital * 0.05
    st.write(f"💰 **Sentinel Rule:** Each trade will use **$ {trade_size:,.2f}** (5% of Capital)")
    auto_pilot = st.toggle("🚀 ENABLE AUTO-PILOT")

# 3. ANALYSIS & CONSENSUS
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
    tr_longs, tr_shorts = 0, 0
    for i, t in enumerate(tfs):
        dm, _, _, sm = fetch_base_data(t)
        if sm:
            p, e, s = dm['close'].iloc[-1], dm['20_ema'].iloc[-1], dm['200_sma'].iloc[-1]
            if p > s and p > e: 
                sig, clr = "🟢 LONG", "#0ff0"
                if i >= 1: tr_longs += 1
            elif p < s and p < e: 
                sig, clr = "🔴 SHORT", "#f44"
                if i >= 1: tr_shorts += 1
            else: sig, clr = "🟡 WAIT", "#888"
            mcols[i].markdown(f"**{t}**\n\n<span style='color:{clr};'>{sig}</span>", unsafe_allow_html=True)

    # TIERED LEVERAGE
    tr_count = max(tr_longs, tr_shorts)
    lev_map = {4: 2, 5: 3, 6: 4, 7: 5}
    cur_lev = lev_map.get(tr_count, 0) if tr_count >= 4 else 0
    c3.metric("Consensus", f"{tr_count}/7 Judges", f"TARGET: {cur_lev}x" if cur_lev > 0 else "WAIT")

    # 4. CHART & POSITION TRACKER
    st.plotly_chart(go.Figure(data=[go.Candlestick(x=df['date'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])]).update_layout(template="plotly_dark", height=400), use_container_width=True)
    
    # SEPARATE POSITION VISUALIZER
    st.subheader("📊 Sentinel Active Entries (Non-Consolidated View)")
    if st.session_state.active_trades:
        trade_df = pd.DataFrame(st.session_state.active_trades)
        st.table(trade_df)
    else:
        st.info("No separate entries currently recorded by Sentinel.")

    # 5. WAR ROOM
    st.markdown("---")
    wc1, wc2, wc3 = st.columns(3)
    entry_trig = wc1.number_input("Entry Price Trigger", value=float(price))
    tp_val = wc2.number_input("Predefined TP ($)", value=float(price*1.05))
    sl_val = wc3.number_input("Predefined SL ($)", value=float(price*0.97))
    
    def execute_and_log(side, entry, tp, sl, consensus, leverage):
        try:
            # 1. Email Alert
            content = f"SENTINEL SEPARATE ENTRY\nSide: {side}\nCapital Used: 5% (${trade_size})\nLev: {leverage}x\nTP/SL: {tp}/{sl}"
            msg = MIMEText(content); msg['Subject'] = f"🛡️ {side} {leverage}x Entry Logged"; msg['From'] = sender; msg['To'] = sender
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
                s.login(sender, pwd); s.send_message(msg)
            
            # 2. Local State Storage (To show 3 positions separately)
            st.session_state.active_trades.append({
                "ID": len(st.session_state.active_trades) + 1,
                "Time": time.strftime("%H:%M:%S"),
                "Side": side,
                "Entry": f"${entry:,.2f}",
                "Lev": f"{leverage}x",
                "Size ($)": f"${trade_size * leverage:,.2f}"
            })
            return True
        except Exception as e: st.error(f"Error: {e}"); return False

    # --- EXECUTION GATE ---
    if cur_lev > 0:
        side = "LONG" if tr_longs >= 4 else "SHORT"
        if auto_pilot and (side == "LONG" and price >= entry_trig or side == "SHORT" and price <= entry_trig):
            if time.time() - st.session_state.last_trade_time > 300:
                if execute_and_log(side, price, tp_val, sl_val, tr_count, cur_lev):
                    st.session_state.last_trade_time = time.time()
                    st.success("Auto-Pilot: Separate position logged and executed.")

        if st.button("🚀 Execute Manual Entry (Separate)"):
            if execute_and_log(side, price, tp_val, sl_val, tr_count, cur_lev):
                st.success("Manual separate position entry added.")
