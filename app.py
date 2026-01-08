import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from datetime import datetime
import streamlit.components.v1 as components
import smtplib
from email.mime.text import MIMEText
from data_engine import fetch_base_data

# 1. CORE IDENTITY & STYLE
st.set_page_config(page_title="Sreejan Perp Sentinel Pro", layout="wide")

# Master Lock for Settings
if 'perp_entry' not in st.session_state: st.session_state.perp_entry = 0.0
if 'perp_tp' not in st.session_state: st.session_state.perp_tp = 0.0
if 'perp_sl' not in st.session_state: st.session_state.perp_sl = 0.0
if 'chart_tf' not in st.session_state: st.session_state.chart_tf = "1h"
if 'last_alert_time' not in st.session_state: st.session_state.last_alert_time = None

theme = st.sidebar.radio("Theme Mode", ["Dark Mode", "Light Mode"], index=0)
bg = "#000000" if theme == "Dark Mode" else "#FFFFFF"
txt = "#FFFFFF" if theme == "Dark Mode" else "#000000"
accent = "#D4AF37"

st.markdown(f"""
<style>
    .stApp {{ background-color: {bg}; color: {txt} !important; }} 
    h1, h2, h3 {{ color: {accent} !important; }}
    .signal-card {{ padding: 25px; border-radius: 15px; border: 2px solid {accent}; background: {"#050505" if theme=="Dark Mode" else "#f9f9f9"}; margin-bottom: 25px; }}
    .alarm-active {{ border: 2px solid #ff0000 !important; animation: blinker 1s linear infinite; }}
    @keyframes blinker {{ 50% {{ opacity: 0.5; }} }}
    .guide-box {{ padding: 15px; border-radius: 10px; background: #1a1a1a; border-left: 5px solid {accent}; margin-bottom: 20px; color: white; }}
</style>
""", unsafe_allow_html=True)

# 2. EMAIL SENTINEL SETUP
with st.expander("🔐 Email Sentinel Setup (Gmail Only)"):
    sender_email = st.text_input("Your Gmail Address", placeholder="example@gmail.com")
    app_password = st.text_input("16-Digit App Password", type="password")
    if st.button("Save & Test Connection"):
        try:
            msg = MIMEText("Testing the Magic Robot Guard! Your Battle Alerts are now active.")
            msg['Subject'] = "✅ Robot Guard Test"
            msg['From'] = sender_email
            msg['To'] = sender_email
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(sender_email, app_password)
                server.send_message(msg)
            st.success("Connection Settings Saved! Check your inbox.")
        except Exception as e:
            st.error(f"Error: {e}")

def send_battle_alert(tf, direction, price):
    if sender_email and app_password:
        try:
            msg = MIMEText(f"🚨 STRATEGY ALERT!\n\nSignal: {direction}\nTimeframe: {tf}\nPrice: ${price:,.2f}")
            msg['Subject'] = f"🔥 {direction} Signal on {tf}"
            msg['From'] = sender_email
            msg['To'] = sender_email
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(sender_email, app_password)
                server.send_message(msg)
            return True
        except: return False
    return False

# 3. ALARM ENGINE
def trigger_alarm(tf_desc, direction, price):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    if st.session_state.last_alert_time != current_time:
        send_battle_alert(tf_desc, direction, price)
        st.session_state.last_alert_time = current_time
    components.html(f"<script>new Audio('https://actions.google.com/sounds/v1/alarms/emergency_siren.ogg').play(); alert('🚨 EMMANUEL SIGNAL: {direction} on {tf_desc}!');</script>", height=0)

# 4. NAVIGATION
st.title("🛡️ Sreejan Perp Forecaster Sentinel")
tfs = ["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d"]
nav_cols = st.columns(len(tfs))
for i, tf_option in enumerate(tfs):
    if nav_cols[i].button(tf_option, key=f"btn_{tf_option}"):
        st.session_state.chart_tf = tf_option

# 5. DATA FETCH WITH LOADING SPINNER
with st.spinner('Gathering Market Intelligence...'):
    df, btc_p, err_msg, status = fetch_base_data(st.session_state.chart_tf)

if not status:
    st.error(f"⚠️ Market Connection Lost: {err_msg if err_msg else 'Check your Internet'}")
    if st.button("Force Reconnect"):
        st.rerun()
else:
    price = df['close'].iloc[-1]
    
    # 6. HEADER METRICS
    c1, c2, c3 = st.columns(3)
    c1.metric("₿ BTC", f"${btc_p:,.2f}")
    c2.metric(f"S SOL ({st.session_state.chart_tf})", f"${price:,.2f}")

    # 7. STRATEGY GUIDE
    st.markdown("---")
    with st.expander("📖 How to Find the Strongest Signals", expanded=True):
        st.markdown(f"""
        <div class="guide-box">
        <strong>Look for Alignment:</strong> This is when the judges (timeframes) agree with each other. <br><br>
        ⚪ <strong>Low Conviction (1-3 Greens/Reds):</strong> The judges are arguing. It is risky to trade here. <br>
        🟡 <strong>Moderate Conviction (4-5 Greens/Reds):</strong> Most judges agree. The trend is waking up. <br>
        🔥 <strong>Strong Conviction (6-8 Greens/Reds):</strong> <strong>This is the Power Signal!</strong> The Siren will scream and an Email will fly to your phone.
        </div>
        """, unsafe_allow_html=True)

    # 8. MTF RADAR
    st.subheader("🔭 Multi-Timeframe Radar")
    mcols = st.columns(8)
    longs, shorts = 0, 0
    for i, t in enumerate(tfs):
        try:
            d_mtf, _, _, s_mtf = fetch_base_data(t)
            if s_mtf:
                p_m, e20, s200 = d_mtf['close'].iloc[-1], d_mtf['20_ema'].iloc[-1], d_mtf['200_sma'].iloc[-1]
                if p_m > s200 and p_m > e20: sig, color, longs = "🟢 LONG", "#00ff00", longs + 1
                elif p_m < s200 and p_m < e20: sig, color, shorts = "🔴 SHORT", "#ff4b4b", shorts + 1
                else: sig, color = "🟡 WAIT", "#888"
                mcols[i].markdown(f"**{t}**\n\n<span style='color:{color};'>{sig}</span>", unsafe_allow_html=True)
        except: pass

    conviction = "STRONG" if (longs >= 6 or shorts >= 6) else "MODERATE"
    c3.metric("Consensus", f"{max(longs, shorts)}/8 Alignment", conviction)
    
    if conviction == "STRONG":
        dir_text = "LONG" if longs >= 6 else "SHORT"
        trigger_alarm(st.session_state.chart_tf, dir_text, price)

    # 9. CHART
    fig = go.Figure(data=[go.Candlestick(x=df['date'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
    fig.add_trace(go.Scatter(x=df['date'], y=df['20_ema'], name="20 EMA", line=dict(color="#854CE6", width=2)))
    fig.add_trace(go.Scatter(x=df['date'], y=df['200_sma'], name="200 SMA", line=dict(color="#FF9900", dash='dot', width=2)))
    fig.update_layout(template="plotly_dark" if theme=="Dark Mode" else "plotly_white", paper_bgcolor=bg, plot_bgcolor=bg, height=500, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    # 10. WAR ROOM
    st.markdown(f'<div class="signal-card {"alarm-active" if conviction=="STRONG" else ""}">', unsafe_allow_html=True)
    st.subheader("✍️ War Room: Manual Entry & Safety Soul")
    lev = st.sidebar.slider("Leverage", 1.0, 50.0, 5.0)
    
    wc1, wc2, wc3 = st.columns(3)
    with wc1:
        m_entry = st.slider("Manual Entry", float(price*0.5), float(price*1.5), value=st.session_state.perp_entry, key="p_entry")
        st.session_state.perp_entry = m_entry
    with wc2:
        m_tp = st.slider("Manual TP", float(price*0.5), float(price*1.5), value=st.session_state.perp_tp, key="p_tp")
        st.session_state.perp_tp = m_tp
    with wc3:
        m_sl = st.slider("Manual SL", float(price*0.5), float(price*1.5), value=st.session_state.perp_sl, key="p_sl")
        st.session_state.perp_sl = m_sl

    liq_p = price * (1 - (1/lev)*0.45) if longs >= shorts else price * (1 + (1/lev)*0.45)
    st.markdown(f"**Liquidation Safety Floor:** ${liq_p:,.2f}")
    st.markdown('</div>', unsafe_allow_html=True)
