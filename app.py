import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import smtplib
from email.mime.text import MIMEText
from data_engine import fetch_base_data

# 1. CORE SETUP & MASTER LOCK
st.set_page_config(page_title="Sreejan Perp Sentinel Pro", layout="wide")

# Persistent State Management
if 'chart_tf' not in st.session_state: st.session_state.chart_tf = "1h"
if 'perp_entry' not in st.session_state: st.session_state.perp_entry = 0.0
if 'perp_tp' not in st.session_state: st.session_state.perp_tp = 0.0
if 'perp_sl' not in st.session_state: st.session_state.perp_sl = 0.0

theme = st.sidebar.radio("Theme Mode", ["Dark Mode", "Light Mode"], index=0)
bg, txt, accent = ("#000", "#FFF", "#D4AF37") if theme == "Dark Mode" else ("#FFF", "#000", "#D4AF37")

st.markdown(f"""
<style>
    .stApp {{ background-color: {bg}; color: {txt} !important; }} 
    h1, h2, h3 {{ color: {accent} !important; }}
    .guide-box {{ padding: 15px; border-radius: 10px; background: #1a1a1a; border-left: 5px solid {accent}; margin-bottom: 20px; color: white; }}
    .metric-card {{ background: #111; padding: 15px; border-radius: 8px; border: 1px solid #333; }}
</style>
""", unsafe_allow_html=True)

# 2. EMAIL SENTINEL (Restored Settings)
with st.expander("🔐 Email Sentinel Setup (Gmail Only)"):
    sender = st.text_input("Your Gmail Address", value="sreejan@onebostoncapital.com")
    pwd = st.text_input("16-Digit App Password", type="password")
    if st.button("Save & Test Connection"):
        try:
            msg = MIMEText("Sentinel Active and Monitoring!"); msg['Subject'] = "✅ Robot Guard Online"; msg['From'] = sender; msg['To'] = sender
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
                s.login(sender, pwd); s.send_message(msg)
            st.success("Connection Settings Saved!")
        except Exception as e: st.error(f"Error: {e}")

# 3. HEADER & DATA
st.title("🛡️ Sreejan Perp Forecaster Sentinel")

with st.spinner('Scanning Market Intelligence...'):
    df, btc_p, err, status = fetch_base_data(st.session_state.chart_tf)

if not status:
    st.error(f"⚠️ {err}")
else:
    price = df['close'].iloc[-1]
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("₿ BTC Price", f"${btc_p:,.2f}")
    with c2: st.metric(f"S SOL Price ({st.session_state.chart_tf})", f"${price:,.2f}")

    # 4. STRATEGY GUIDE (Restored)
    st.markdown("---")
    with st.expander("📖 Strategy Guide: The Judge System", expanded=True):
        st.markdown(f'<div class="guide-box"><strong>Power Signal Checklist:</strong><br>⚪ 1-3 Judges: Weak Trend | 🟡 4-5 Judges: Developing | 🔥 6-8 Judges: <strong>Strong Conviction!</strong></div>', unsafe_allow_html=True)

    # 5. MTF RADAR (Restored)
    tfs = ["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d"]
    mcols = st.columns(8); longs, shorts = 0, 0
    for i, t in enumerate(tfs):
        try:
            d_m, _, _, s_m = fetch_base_data(t)
            if s_m:
                pm, e20, s200 = d_m['close'].iloc[-1], d_m['20_ema'].iloc[-1], d_m['200_sma'].iloc[-1]
                if pm > s200 and pm > e20: sig, color, longs = "🟢 LONG", "#0ff0", longs + 1
                elif pm < s200 and pm < e20: sig, color, shorts = "🔴 SHORT", "#f44", shorts + 1
                else: sig, color = "🟡 WAIT", "#888"
                mcols[i].markdown(f"**{t}**\n\n<span style='color:{color};'>{sig}</span>", unsafe_allow_html=True)
        except: pass

    conv = "STRONG" if (longs >= 6 or shorts >= 6) else "MODERATE"
    with c3: st.metric("Consensus", f"{max(longs, shorts)}/8 Alignment", conv)

    # 6. MAIN CHART
    fig = go.Figure(data=[go.Candlestick(x=df['date'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
    fig.add_trace(go.Scatter(x=df['date'], y=df['20_ema'], name="20 EMA", line=dict(color="#854CE6", width=2)))
    fig.add_trace(go.Scatter(x=df['date'], y=df['200_sma'], name="200 SMA", line=dict(color="#FF9900", dash='dot', width=2)))
    fig.update_layout(template="plotly_dark" if theme=="Dark Mode" else "plotly_white", paper_bgcolor=bg, plot_bgcolor=bg, height=550, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    # 7. NAVIGATION BUTTONS (Now BELOW the chart as requested)
    st.markdown("### ⏱️ Select Chart Timeframe")
    nav_cols = st.columns(len(tfs))
    for i, tf_opt in enumerate(tfs):
        if nav_cols[i].button(tf_opt, key=f"btn_{tf_opt}"):
            st.session_state.chart_tf = tf_opt
            st.rerun()

    # 8. WAR ROOM & SAFETY (Restored)
    st.markdown("---")
    st.subheader("✍️ War Room: Manual Planning & Safety Floor")
    lev = st.sidebar.slider("Leverage", 1.0, 50.0, 5.0)
    
    wc1, wc2, wc3 = st.columns(3)
    with wc1: st.session_state.perp_entry = st.number_input("Entry Price", value=float(price))
    with wc2: st.session_state.perp_tp = st.number_input("Take Profit", value=float(price*1.05))
    with wc3: st.session_state.perp_sl = st.number_input("Stop Loss", value=float(price*0.97))
    
    liq_p = price * (1 - (1/lev)*0.45) if longs >= shorts else price * (1 + (1/lev)*0.45)
    st.warning(f"🛡️ **Liquidation Safety Floor:** ${liq_p:,.2f} | **Current Leverage:** {lev}x")
