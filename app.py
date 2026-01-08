import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import smtplib
import time
from email.mime.text import MIMEText
from streamlit_autorefresh import st_autorefresh
from data_engine import fetch_base_data

# 1. THE HEARTBEAT (30s AUTO-REFRESH)
st.set_page_config(page_title="Sreejan Perp Sentinel Pro", layout="wide")
st_autorefresh(interval=30000, key="sentinel_pulse")

# Persistent State
if 'chart_tf' not in st.session_state: st.session_state.chart_tf = "1h"
if 'last_trade_time' not in st.session_state: st.session_state.last_trade_time = 0
if 'trade_history' not in st.session_state: st.session_state.trade_history = []

theme = st.sidebar.radio("Theme Mode", ["Dark Mode", "Light Mode"], index=0)
bg, txt, accent = ("#000", "#FFF", "#D4AF37") if theme == "Dark Mode" else ("#FFF", "#000", "#D4AF37")
st.markdown(f"<style>.stApp {{ background-color: {bg}; color: {txt} !important; }} h1, h2, h3 {{ color: {accent} !important; }}</style>", unsafe_allow_html=True)

# 2. STATUS & COUNTDOWN
with st.sidebar:
    st.header("🔐 Wallet & Settings")
    sender = st.text_input("Gmail", value="sreejan@onebostoncapital.com")
    pwd = st.text_input("App Password", type="password")
    total_cap = st.number_input("Drift Equity ($)", value=1000.0)
    auto_pilot = st.toggle("🚀 ENABLE AUTO-PILOT")
    
    # Visual Heartbeat
    time_left = 30 - int(time.time() % 30)
    st.write(f"⏱️ Next Refresh in: **{time_left}s**")

# 3. ANALYSIS & CONSENSUS (4/7 - 7/7 Tiered)
df, btc_p, err, status = fetch_base_data(st.session_state.chart_tf)

if status:
    price = df['close'].iloc[-1]
    c1, c2, c3 = st.columns(3)
    c1.metric("₿ BTC", f"${btc_p:,.2f}")
    c2.metric(f"S SOL ({st.session_state.chart_tf})", f"${price:,.2f}")

    # THE 8 JUDGES (1m visible, 5m+ used for logic)
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

    # RESTORED CONSENSUS TAB
    tr_count = max(tr_longs, tr_shorts)
    lev_map = {4: 2, 5: 3, 6: 4, 7: 5}
    cur_lev = lev_map.get(tr_count, 0) if tr_count >= 4 else 0
    conv_txt = f"⚡ TIER {tr_count} ({cur_lev}x)" if cur_lev > 0 else "🛑 NO CONSENSUS"
    c3.metric("Execution Judge", f"{tr_count}/7 Align", conv_txt)

    # 4. CHART WITH 20 EMA & 200 SMA
    fig = go.Figure(data=[go.Candlestick(x=df['date'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="Price")])
    fig.add_trace(go.Scatter(x=df['date'], y=df['20_ema'], name="20 EMA", line=dict(color="#854CE6", width=2)))
    fig.add_trace(go.Scatter(x=df['date'], y=df['200_sma'], name="200 SMA", line=dict(color="#FF9900", width=2, dash='dot')))
    
    fig.update_layout(template="plotly_dark", paper_bgcolor=bg, plot_bgcolor=bg, height=500, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    # NAV BUTTONS
    nav_cols = st.columns(len(tfs))
    for i, tf_opt in enumerate(tfs):
        if nav_cols[i].button(tf_opt):
            st.session_state.chart_tf = tf_opt
            st.rerun()

    # 5. WAR ROOM & EMAIL TRIGGER
    st.markdown("---")
    st.subheader("✍️ War Room: Strategy Execution")
    wc1, wc2, wc3 = st.columns(3)
    entry_req = wc1.number_input("Entry Trigger", value=float(price))
    tp_val = wc2.number_input("Predefined TP", value=float(price*1.05))
    sl_val = wc3.number_input("Predefined SL", value=float(price*0.97))
    
    trade_size = total_cap * 0.05

    def send_trade_email(side, lev, consensus):
        try:
            content = f"SENTINEL ALERT\nSide: {side}\nSize: 5% (${trade_size})\nLev: {lev}x\nConsensus: {consensus}/7\nTP: {tp_val}\nSL: {sl_val}"
            msg = MIMEText(content); msg['Subject'] = f"🛡️ {side} {lev}x Executed"; msg['From'] = sender; msg['To'] = sender
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
                s.login(sender, pwd); s.send_message(msg)
            return True
        except Exception as e:
            st.error(f"Email Failed: {e}"); return False

    # TRIGGER LOGIC
    if cur_lev > 0:
        side = "LONG" if tr_longs >= 4 else "SHORT"
        # Auto-Pilot
        if auto_pilot and (time.time() - st.session_state.last_trade_time > 300):
            if (side == "LONG" and price >= entry_req) or (side == "SHORT" and price <= entry_req):
                if send_trade_email(side, cur_lev, tr_count):
                    st.session_state.last_trade_time = time.time()
                    st.session_state.trade_history.append({"Time": time.strftime("%H:%M"), "Side": side, "Lev": cur_lev})
                    st.success("Auto-Pilot Signal Sent!")

        # RESTORED MANUAL EMAIL TRIGGER
        if st.button("🚀 MANUAL: Execute Email Alert Now"):
            if send_trade_email(side, cur_lev, tr_count):
                st.session_state.trade_history.append({"Time": time.strftime("%H:%M"), "Side": side, "Lev": cur_lev})
                st.success("Manual Alert Sent Successfully!")
    else:
        st.warning("Min 4/7 Consensus required for Manual or Auto trade.")

    # POSITION TRACKER
    if st.session_state.trade_history:
        st.write("### 📜 Recent Entries (Separate)")
        st.table(pd.DataFrame(st.session_state.trade_history))
