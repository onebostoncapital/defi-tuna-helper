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

# 1. CORE IDENTITY & STYLE (Rule 14 & Rule 5)
st.set_page_config(page_title="Sreejan Perp Sentinel Pro", layout="wide")

# Persistent Settings Vault (Master Lock - Rule 15)
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
    .stButton>button {{ width: 100%; border-radius: 5px; height: 3em; background-color: #111; color: white; border: 1px solid #333; }}
    .stButton>button:hover {{ border-color: {accent}; color: {accent}; }}
</style>
""", unsafe_allow_html=True)

# 2. EMAIL SENTINEL LOGIC (Rule 22: The Secret Mailbox)
with st.expander("🔐 Email Sentinel Setup (Gmail Only)"):
    sender_email = st.text_input("Your Gmail Address", placeholder="example@gmail.com")
    app_password = st.text_input("16-Digit App Password", type="password")
    if st.button("Save & Test Connection"):
        st.success("Connection Settings Saved!")

def send_battle_alert(tf, direction, price):
    if sender_email and app_password:
        try:
            msg = MIMEText(f"🚨 STRATEGY ALERT!\n\nSignal: {direction}\nTimeframe: {tf}\nPrice: ${price:,.2f}\n\nYour Magic Robot Guard has detected a strong alignment!")
            msg['Subject'] = f"🔥 {direction} Signal on {tf}"
            msg['From'] = sender_email
            msg['To'] = sender_email
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(sender_email, app_password)
                server.send_message(msg)
            return True
        except: return False
    return False

# 3. ALARM ENGINE (Rule: Loud Alarm + 5x Popups)
def trigger_alarm(tf_desc, direction, price):
    # Only send email once per signal event to avoid spam
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    if st.session_state.last_alert_time != current_time:
        send_battle_alert(tf_desc, direction, price)
        st.session_state.last_alert_time = current_time

    alarm_js = f"""
    <script>
    var audio = new Audio('https://actions.google.com/sounds/v1/alarms/emergency_siren.ogg');
    audio.play();
    for (let i = 0; i < 5; i++) {{
        setTimeout(() => {{ alert("🚨 EMMANUEL SIGNAL: STRONG CONVICTION on {tf_desc}!"); }}, i * 1500);
    }}
    </script>
    """
    components.html(alarm_js, height=0)

# 4. INTERACTIVE TIMEFRAME NAVIGATION
st.title("🛡️ Sreejan Perp Forecaster Sentinel")
tfs = ["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d"]
nav_cols = st.columns(len(tfs))
for i, tf_option in enumerate(tfs):
    if nav_cols[i].button(tf_option, key=f"btn_{tf_option}"):
        st.session_state.chart_tf = tf_option

# 5. PRIMARY DATA FETCH
try:
    df, btc_p, _, status = fetch_base_data(st.session_state.chart_tf)
except Exception as e:
    st.error("Connecting to Market Data...")
    status = False

if status:
    price = df['close'].iloc[-1]
    
    # Init Sliders if Empty (Master Lock)
    if st.session_state.perp_entry == 0.0: st.session_state.perp_entry = float(price)
    if st.session_state.perp_tp == 0.0: st.session_state.perp_tp = float(price * 1.05)
    if st.session_state.perp_sl == 0.0: st.session_state.perp_sl = float(price * 0.98)

    # 6. HEADER METRICS
    c1, c2, c3 = st.columns(3)
    c1.metric("₿ BTC", f"${btc_p:,.2f}")
    c2.metric(f"S SOL ({st.session_state.chart_tf})", f"${price:,.2f}")

    # 7. DYNAMIC MTF RADAR DISPLAY (Rule: Background Scanning)
    st.markdown("---")
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
        except: mcols[i].markdown(f"**{t}**\n\n<span style='color:orange;'>SCAN...</span>", unsafe_allow_html=True)

    # 8. CONVICTION & AUTOMATIC ALARM
    conviction = "STRONG" if (longs >= 6 or shorts >= 6) else "MODERATE"
    c3.metric("Consensus", f"{max(longs, shorts)}/8 Alignment", conviction)
    
    if conviction == "STRONG":
        dir_text = "LONG" if longs >= 6 else "SHORT"
        trigger_alarm(st.session_state.chart_tf, dir_text, price)

    st.markdown("---")

    # 9. INTERACTIVE PLOTLY CHART
    fig = go.Figure(data=[go.Candlestick(x=df['date'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="SOL")])
    fig.add_trace(go.Scatter(x=df['date'], y=df['20_ema'], name="20 EMA", line=dict(color="#854CE6", width=2)))
    fig.add_trace(go.Scatter(x=df['date'], y=df['200_sma'], name="200 SMA", line=dict(color="#FF9900", dash='dot', width=2)))
    fig.update_layout(template="plotly_dark" if theme=="Dark Mode" else "plotly_white", paper_bgcolor=bg, plot_bgcolor=bg, height=500, xaxis=dict(rangeslider=dict(visible=False), type="date"), yaxis=dict(fixedrange=False), hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

    # 10. MANUAL WAR ROOM (Rule 11/14/15 - Master Lock)
    st.markdown(f'<div class="signal-card {"alarm-active" if conviction=="STRONG" else ""}">', unsafe_allow_html=True)
    st.subheader("✍️ War Room: Manual Entry & Safety Soul")
    lev = st.sidebar.slider("Leverage", 1.0, 50.0, 5.0)
    cap = st.sidebar.number_input("Total Capital ($)", value=10000.0)
    
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

    net_pnl = (((m_tp - m_entry) / m_entry) * lev * cap) - (cap * 0.0003 * 3)
    liq_p = price * (1 - (1/lev)*0.45) if longs >= shorts else price * (1 + (1/lev)*0.45)
    st.markdown(f"**Net Profit Target:** ${net_pnl:,.2f} | **Liquidation Safety Floor:** ${liq_p:,.2f}")
    st.markdown('</div>', unsafe_allow_html=True)
