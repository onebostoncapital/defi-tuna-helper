import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import smtplib
import time
from email.mime.text import MIMEText
from streamlit_autorefresh import st_autorefresh
from data_engine import fetch_base_data

# 1. PAGE CONFIG & UI REFRESH
st.set_page_config(page_title="Sreejan Perp Sentinel Pro", layout="wide")

# This 1s refresh only updates the TIMER, not the data (keeps it fast)
st_autorefresh(interval=1000, key="ui_counter") 

if 'last_market_update' not in st.session_state:
    st.session_state.last_market_update = time.time()
if 'chart_tf' not in st.session_state: st.session_state.chart_tf = "1h"
if 'trade_history' not in st.session_state: st.session_state.trade_history = []

theme = st.sidebar.radio("Theme Mode", ["Dark Mode", "Light Mode"], index=0)
bg, txt, accent = ("#000", "#FFF", "#D4AF37") if theme == "Dark Mode" else ("#FFF", "#000", "#D4AF37")
st.markdown(f"<style>.stApp {{ background-color: {bg}; color: {txt} !important; }} h1, h2, h3 {{ color: {accent} !important; }}</style>", unsafe_allow_html=True)

# 2. LIVE TIMER LOGIC
elapsed = time.time() - st.session_state.last_market_update
time_to_refresh = max(0, int(30 - elapsed))

if time_to_refresh <= 0:
    st.session_state.last_market_update = time.time()
    st.cache_data.clear() # Force fresh data every 30s
    st.rerun()

# 3. SIDEBAR
with st.sidebar:
    st.header("🔐 Settings")
    sender = st.text_input("Gmail", value="sreejan@onebostoncapital.com")
    pwd = st.text_input("App Password", type="password")
    total_cap = st.number_input("Drift Equity ($)", value=1000.0)
    auto_pilot = st.toggle("🚀 ENABLE AUTO-PILOT")
    st.subheader(f"⏱️ Next Sync: {time_to_refresh}s")
    st.progress(time_to_refresh / 30)

# 4. ANALYSIS & CONSENSUS MATRIX (RESTORED)
df, btc_p, err, status = fetch_base_data(st.session_state.chart_tf)

if status:
    price = df['close'].iloc[-1]
    c1, c2, c3 = st.columns(3)
    c1.metric("₿ BTC", f"${btc_p:,.2f}")
    c2.metric(f"S SOL ({st.session_state.chart_tf})", f"${price:,.2f}")

    # CONSENSUS MATRIX BOXES
    st.markdown("### 🏛️ Consensus Judge Matrix (8-Judges)")
    tfs = ["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d"]
    mcols = st.columns(8)
    tr_longs, tr_shorts = 0, 0

    for i, t in enumerate(tfs):
        dm, _, _, sm = fetch_base_data(t)
        if sm:
            p, e, s = dm['close'].iloc[-1], dm['20_ema'].iloc[-1], dm['200_sma'].iloc[-1]
            if p > s and p > e: 
                sig, clr, box_bg = "🟢 LONG", "#0ff0", "rgba(0, 255, 0, 0.1)"
                tr_longs += 1
            elif p < s and p < e: 
                sig, clr, box_bg = "🔴 SHORT", "#f44", "rgba(255, 0, 0, 0.1)"
                tr_shorts += 1
            else: 
                sig, clr, box_bg = "🟡 WAIT", "#888", "rgba(128, 128, 128, 0.1)"
            
            mcols[i].markdown(
                f"<div style='border:1px solid {clr}; border-radius:5px; padding:10px; background-color:{box_bg}; text-align:center;'>"
                f"<b>{t}</b><br><span style='color:{clr}; font-weight:bold;'>{sig}</span>"
                f"</div>", unsafe_allow_html=True
            )

    # TIERED LEVERAGE LOGIC
    tr_count = max(tr_longs, tr_shorts)
    lev_map = {4: 2, 5: 3, 6: 4, 7: 5, 8: 5} 
    cur_lev = lev_map.get(tr_count, 0) if tr_count >= 4 else 0
    c3.metric("Execution Judge", f"{tr_count}/8 Align", f"{cur_lev}x Leverage" if cur_lev > 0 else "WAIT")

    # 5. CHART WITH INDICATORS (20 EMA / 200 SMA)
    fig = go.Figure(data=[go.Candlestick(x=df['date'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="Price")])
    fig.add_trace(go.Scatter(x=df['date'], y=df['20_ema'], name="20 EMA", line=dict(color="#854CE6", width=2)))
    fig.add_trace(go.Scatter(x=df['date'], y=df['200_sma'], name="200 SMA", line=dict(color="#FF9900", width=2, dash='dot')))
    fig.update_layout(template="plotly_dark", height=450, xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig, use_container_width=True)

    # Timeframe Selection
    nav_cols = st.columns(len(tfs))
    for i, tf_opt in enumerate(tfs):
        if nav_cols[i].button(tf_opt):
            st.session_state.chart_tf = tf_opt
            st.rerun()

    # 6. WAR ROOM
    st.markdown("---")
    wc1, wc2, wc3 = st.columns(3)
    entry_req = wc1.number_input("Trigger Price", value=float(price))
    tp_val = wc2.number_input("Predefined TP", value=float(price*1.05))
    sl_val = wc3.number_input("Predefined SL", value=float(price*0.97))
    
    trade_size_usd = total_cap * 0.05 

    def send_trade_email(side, lev, consensus):
        try:
            content = f"SENTINEL ALERT\nSide: {side}\nSize: 5% (${trade_size_usd})\nLev: {lev}x\nConsensus: {consensus}/8"
            msg = MIMEText(content); msg['Subject'] = f"🛡️ {side} {lev}x Alert"; msg['From'] = sender; msg['To'] = sender
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
                s.login(sender, pwd); s.send_message(msg)
            return True
        except Exception: return False

    # 7. TRIGGER Logic
    if cur_lev > 0:
        side = "LONG" if tr_longs >= 4 else "SHORT"
        if st.button("🚀 MANUAL: Trigger Email Alert"):
            if send_trade_email(side, cur_lev, tr_count):
                st.session_state.trade_history.append({"Time": time.strftime("%H:%M"), "Side": side, "Lev": cur_lev})
                st.success("Alert Sent!")
    else:
        st.warning("⚠️ Min 4/8 Judges Required.")

    if st.session_state.trade_history:
        st.table(pd.DataFrame(st.session_state.trade_history).tail(3))
