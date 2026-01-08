import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from datetime import datetime
import streamlit.components.v1 as components
from data_engine import fetch_base_data

# 1. CORE IDENTITY & STYLE
st.set_page_config(page_title="Sreejan Perp Sentinel Pro", layout="wide")

# Persistent Settings
if 'perp_entry' not in st.session_state: st.session_state.perp_entry = 0.0
if 'perp_tp' not in st.session_state: st.session_state.perp_tp = 0.0
if 'perp_sl' not in st.session_state: st.session_state.perp_sl = 0.0

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
</style>
""", unsafe_allow_html=True)

# 2. ALARM ENGINE
def trigger_alarm():
    alarm_js = """
    <script>
    var audio = new Audio('https://actions.google.com/sounds/v1/alarms/emergency_siren.ogg');
    audio.play();
    for (let i = 0; i < 5; i++) {
        setTimeout(() => { alert("🚨 EMMANUEL SIGNAL: STRONG CONVICTION!"); }, i * 1500);
    }
    </script>
    """
    components.html(alarm_js, height=0)

# 3. INTERACTIVE HEADER & TIMEFRAME SELECTOR
st.title("🛡️ Sreejan Perp Forecaster Sentinel")
main_tf = st.select_slider(
    "Select Interactive Chart Timeframe",
    options=["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d"],
    value="1h"
)

# 4. PRIMARY DATA FETCH (The "Heart")
try:
    df, btc_p, _, status = fetch_base_data(main_tf)
except Exception as e:
    st.error(f"Waiting for Data Connection... ({e})")
    status = False

if status:
    price = df['close'].iloc[-1]
    
    # Initialize sliders if they are 0
    if st.session_state.perp_entry == 0.0: st.session_state.perp_entry = float(price)
    if st.session_state.perp_tp == 0.0: st.session_state.perp_tp = float(price * 1.05)
    if st.session_state.perp_sl == 0.0: st.session_state.perp_sl = float(price * 0.98)

    # 5. HEADER METRICS
    c1, c2, c3 = st.columns(3)
    c1.metric("₿ BTC", f"${btc_p:,.2f}")
    c2.metric("S SOL", f"${price:,.2f}")

    # 6. MULTI-TIMEFRAME RADAR (Safe Loop)
    st.markdown("---")
    st.subheader("🔭 Multi-Timeframe Radar")
    tfs = ["1m", "5m", "15m", "30m", "1h", "6h", "12h", "1d"]
    mcols = st.columns(8)
    longs, shorts = 0, 0
    
    for i, t in enumerate(tfs):
        try:
            # We use a smaller limit for radar to speed up loading
            d_mtf, _, _, s_mtf = fetch_base_data(t)
            if s_mtf:
                p_m, e20, s200 = d_mtf['close'].iloc[-1], d_mtf['20_ema'].iloc[-1], d_mtf['200_sma'].iloc[-1]
                if p_m > s200 and p_m > e20:
                    sig, color, longs = "🟢 LONG", "#00ff00", longs + 1
                elif p_m < s200 and p_m < e20:
                    sig, color, shorts = "🔴 SHORT", "#ff4b4b", shorts + 1
                else:
                    sig, color = "🟡 WAIT", "#888"
                mcols[i].markdown(f"**{t}**\n\n<span style='color:{color};'>{sig}</span>", unsafe_allow_html=True)
        except:
            mcols[i].markdown(f"**{t}**\n\n<span style='color:orange;'>SCANNING...</span>", unsafe_allow_html=True)

    conviction = "STRONG" if (longs >= 6 or shorts >= 6) else "MODERATE"
    c3.metric("Consensus", f"{max(longs, shorts)}/8 Alignment", conviction)
    if conviction == "STRONG": trigger_alarm()
    st.markdown("---")

    # 7. INTERACTIVE PLOTLY CHART
    fig = go.Figure(data=[go.Candlestick(
        x=df['date'], open=df['open'], high=df['high'], low=df['low'], close=df['close'],
        name="SOL/USDT"
    )])
    fig.add_trace(go.Scatter(x=df['date'], y=df['20_ema'], name="20 EMA", line=dict(color="#854CE6", width=2)))
    fig.add_trace(go.Scatter(x=df['date'], y=df['200_sma'], name="200 SMA", line=dict(color="#FF9900", dash='dot', width=2)))
    
    fig.update_layout(
        template="plotly_dark" if theme=="Dark Mode" else "plotly_white",
        paper_bgcolor=bg, plot_bgcolor=bg, height=500,
        xaxis=dict(rangeslider=dict(visible=False), type="date"),
        yaxis=dict(fixedrange=False), hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)

    # 8. MANUAL WAR ROOM (Sovereign & Persistent)
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

    # 9. SENTIMENT & HISTORY
    st.sidebar.divider()
    st.sidebar.subheader("Live Sentinel History")
    st.sidebar.button("Acknowledge & Silence Siren")
else:
    st.warning("Connecting to Market Data... Please wait a few seconds.")
