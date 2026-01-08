import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import smtplib
import time
from email.mime.text import MIMEText
from streamlit_autorefresh import st_autorefresh
from data_engine import fetch_base_data

# 1. DUAL HEARTBEAT SYSTEM
st.set_page_config(page_title="Sreejan Perp Sentinel Pro", layout="wide")

# Heartbeat A: 1-second UI refresh for the LIVE TIMER
st_autorefresh(interval=1000, key="ui_counter") 

# Heartbeat B: 30-second logic refresh for MARKET DATA
if 'last_market_update' not in st.session_state:
    st.session_state.last_market_update = time.time()

# Persistent States
if 'chart_tf' not in st.session_state: st.session_state.chart_tf = "1h"
if 'last_trade_time' not in st.session_state: st.session_state.last_trade_time = 0
if 'trade_history' not in st.session_state: st.session_state.trade_history = []

theme = st.sidebar.radio("Theme Mode", ["Dark Mode", "Light Mode"], index=0)
bg, txt, accent = ("#000", "#FFF", "#D4AF37") if theme == "Dark Mode" else ("#FFF", "#000", "#D4AF37")
st.markdown(f"<style>.stApp {{ background-color: {bg}; color: {txt} !important; }} h1, h2, h3 {{ color: {accent} !important; }}</style>", unsafe_allow_html=True)

# 2. LIVE COUNTDOWN LOGIC
elapsed = time.time() - st.session_state.last_market_update
time_to_refresh = max(0, int(30 - elapsed))

if time_to_refresh <= 0:
    st.session_state.last_market_update = time.time()
    st.rerun()

# 3. SIDEBAR CONTROLS
with st.sidebar:
    st.header("🔐 Wallet & Settings")
    sender = st.text_input("Gmail", value="sreejan@onebostoncapital.com")
    pwd = st.text_input("App Password", type="password")
    total_cap = st.number_input("Drift Equity ($)", value=1000.0)
    auto_pilot = st.toggle("🚀 ENABLE AUTO-PILOT")
    
    st.markdown("---")
    st.subheader(f"⏱️ Next Market Sync: {time_to_refresh}s")
    st.progress(time_to_refresh / 30)

# 4. ANALYSIS & 8-JUDGE CONSENSUS
df, btc_p, err, status = fetch_base_data(st.session_state.chart_tf)

if status:
    price = df['close'].iloc[-1]
    c1, c2, c3 = st.columns(3)
    c1.metric("₿ BTC Price", f"${btc_p:,.2f}")
    c2.metric(f"S SOL ({st.session_state.chart_tf})", f"${price:,.2f}")

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
                if i >= 1: tr_longs += 1 # Exclude 1m from logic
            elif p < s and p < e: 
                sig, clr = "🔴 SHORT", "#f44"
                if i >= 1: tr_shorts += 1
            else: sig, clr = "🟡 WAIT", "#888"
            mcols[i].markdown(f"**{t}**\n\n<span style='color:{clr};'>{sig}</span>", unsafe_allow_html=True)

    # TIERED LEVERAGE LOGIC
    tr_count = max(tr_longs, tr_shorts)
    lev_map = {4: 2, 5: 3, 6: 4, 7: 5}
    cur_lev = lev_map.get(tr_count, 0) if tr_count >= 4 else 0
    conv_txt = f"⚡ TIER {tr_count} ({cur_lev}x)" if cur_lev > 0 else "🛑 NO CONSENSUS"
    c3.metric("Execution Judge", f"{tr_count}/7 Align", conv_txt)

    # 5. CHART WITH INDICATORS
    # Restoring the 20 EMA and 200 SMA visibility
    fig = go.Figure(data=[go.Candlestick(x=df['date'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="Price")])
    fig.add_trace(go.Scatter(x=df['date'], y=df['20_ema'], name="20 EMA", line=dict(color="#854CE6", width=2)))
    fig.add_trace(go.Scatter(x=df['date'], y=df['200_sma'], name="200 SMA", line=dict(color="#FF9900", width=2, dash='dot')))
    
    fig.update_layout(template="plotly_dark", paper_bgcolor=bg, plot_bgcolor=bg, height=450, xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

    # Timeframe Navigation
    nav_cols = st.columns(len(tfs))
    for i, tf_opt in enumerate(tfs):
        if nav_cols[i].button(tf_opt, key=f"nav_{tf_opt}"):
            st.session_state.chart_tf = tf_opt
            st.rerun()

    # 6. WAR ROOM & EMAIL DISPATCH
    st.markdown("---")
    st.subheader("✍️ War Room: Execution Details")
    wc1, wc2, wc3 = st.columns(3)
    entry_req = wc1.number_input("Entry Trigger Price", value=float(price))
    tp_val = wc2.number_input("Predefined Take Profit", value=float(price*1.05))
    sl_val = wc3.number_input("Predefined Stop Loss", value=float(price*0.97))
    
    trade_size_usd = total_cap * 0.05 # 5% Capital Rule

    def send_trade_email(side, lev, consensus):
        try:
            content = (f"SENTINEL DISPATCH\n"
                       f"Side: {side}\n"
                       f"Base Size (5%): ${trade_size_usd:,.2f}\n"
                       f"Leverage: {lev}x\n"
                       f"Total Position: ${trade_size_usd * lev:,.2f}\n"
                       f"Consensus: {consensus}/7\n"
                       f"TP: {tp_val} | SL: {sl_val}")
            msg = MIMEText(content); msg['Subject'] = f"🛡️ {side} {lev}x Executed"; msg['From'] = sender; msg['To'] = sender
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
                s.login(sender, pwd); s.send_message(msg)
            return True
        except Exception as e:
            st.error(f"Email Error: {e}"); return False

    # 7. EXECUTION GATEWAY (MIN 4/7)
    if cur_lev > 0:
        side = "LONG" if tr_longs >= 4 else "SHORT"
        
        # Auto-Pilot Logic
        if auto_pilot and (time.time() - st.session_state.last_trade_time > 300):
            price_condition = (side == "LONG" and price >= entry_req) or (side == "SHORT" and price <= entry_req)
            if price_condition:
                if send_trade_email(side, cur_lev, tr_count):
                    st.session_state.last_trade_time = time.time()
                    st.session_state.trade_history.append({"Time": time.strftime("%H:%M:%S"), "Side": side, "Lev": f"{cur_lev}x", "Status": "Auto"})
                    st.success(f"Auto-Pilot: {side} {cur_lev}x Dispatched.")

        # Manual Trigger
        if st.button("🚀 MANUAL: Trigger Separate Entry Alert"):
            if send_trade_email(side, cur_lev, tr_count):
                st.session_state.trade_history.append({"Time": time.strftime("%H:%M:%S"), "Side": side, "Lev": f"{cur_lev}x", "Status": "Manual"})
                st.success(f"Manual Alert Sent at {cur_lev}x Leverage.")
    else:
        st.warning("⚠️ Min 4/7 Consensus required to enable Manual/Auto triggers.")

    # 8. POSITION TRACKER (NON-CONSOLIDATED VIEW)
    if st.session_state.trade_history:
        st.write("### 📜 Active Entry Logs")
        st.table(pd.DataFrame(st.session_state.trade_history).tail(5))
