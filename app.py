import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import smtplib
from email.mime.text import MIMEText
from data_engine import fetch_base_data

# 1. CORE SETUP
st.set_page_config(page_title="Sreejan Perp Sentinel Pro", layout="wide")

if 'chart_tf' not in st.session_state: st.session_state.chart_tf = "1h"
if 'perp_entry' not in st.session_state: st.session_state.perp_entry = 0.0

theme = st.sidebar.radio("Theme Mode", ["Dark Mode", "Light Mode"], index=0)
bg, txt, accent = ("#000", "#FFF", "#D4AF37") if theme == "Dark Mode" else ("#FFF", "#000", "#D4AF37")

st.markdown(f"""
<style>
    .stApp {{ background-color: {bg}; color: {txt} !important; }} 
    h1, h2, h3 {{ color: {accent} !important; }}
    .guide-box {{ padding: 15px; border-radius: 10px; background: #1a1a1a; border-left: 5px solid {accent}; margin-bottom: 20px; color: white; }}
</style>
""", unsafe_allow_html=True)

# 2. EMAIL SENTINEL SETUP
with st.expander("🔐 Email Sentinel Setup (Gmail Only)"):
    sender = st.text_input("Your Gmail Address")
    pwd = st.text_input("16-Digit App Password", type="password")
    if st.button("Save & Test Connection"):
        try:
            msg = MIMEText("Testing the Cloud Guardian!")
            msg['Subject'] = "✅ Robot Guard Test"; msg['From'] = sender; msg['To'] = sender
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
                s.login(sender, pwd); s.send_message(msg)
            st.success("Connection Saved! Dashboard is active.")
        except Exception as e: st.error(f"Error: {e}")

# 3. NAVIGATION
st.title("🛡️ Sreejan Perp Forecaster Sentinel")
tfs = ["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d"]
nav_cols = st.columns(len(tfs))
for i, tf in enumerate(tfs):
    if nav_cols[i].button(tf): st.session_state.chart_tf = tf

# 4. DATA FETCH
with st.spinner('Gathering Market Intelligence via Yahoo...'):
    df, btc_p, err, status = fetch_base_data(st.session_state.chart_tf)

if not status:
    st.error(f"⚠️ {err}")
else:
    price = df['close'].iloc[-1]
    c1, c2, c3 = st.columns(3)
    c1.metric("₿ BTC", f"${btc_p:,.2f}")
    c2.metric(f"S SOL ({st.session_state.chart_tf})", f"${price:,.2f}")

    # 5. STRATEGY GUIDE
    st.markdown("---")
    with st.expander("📖 How to Find the Strongest Signals", expanded=True):
        st.markdown(f'<div class="guide-box"><strong>Look for Alignment:</strong> Judges agree! <br>⚪ 1-3: Low | 🟡 4-5: Moderate | 🔥 6-8: <strong>Strong Power Signal!</strong></div>', unsafe_allow_html=True)

    # 6. MTF RADAR
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
    c3.metric("Consensus", f"{max(longs, shorts)}/8 Alignment", conv)

    # 7. CHART
    fig = go.Figure(data=[go.Candlestick(x=df['date'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
    fig.add_trace(go.Scatter(x=df['date'], y=df['20_ema'], name="20 EMA", line=dict(color="#854CE6")))
    fig.add_trace(go.Scatter(x=df['date'], y=df['200_sma'], name="200 SMA", line=dict(color="#FF9900", dash='dot')))
    fig.update_layout(template="plotly_dark" if theme=="Dark Mode" else "plotly_white", paper_bgcolor=bg, plot_bgcolor=bg, height=500, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    # 8. WAR ROOM
    st.markdown('<div class="guide-box">')
    st.subheader("✍️ War Room: Manual Entry & Safety Floor")
    lev = st.sidebar.slider("Leverage", 1.0, 50.0, 5.0)
    st.session_state.perp_entry = st.slider("Manual Entry", float(price*0.5), float(price*1.5), value=st.session_state.perp_entry)
    
    liq_p = price * (1 - (1/lev)*0.45) if longs >= shorts else price * (1 + (1/lev)*0.45)
    st.markdown(f"**Liquidation Safety Floor:** ${liq_p:,.2f}")
    st.markdown('</div>', unsafe_allow_html=True)
