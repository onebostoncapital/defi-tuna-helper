import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
from streamlit_autorefresh import st_autorefresh
from data_engine import fetch_base_data

# 1. PAGE CONFIG & PERSISTENCE
st.set_page_config(page_title="Sreejan Sentinel Pro", layout="wide")
st_autorefresh(interval=1000, key="global_refresh")

# Initialize persistent variables so they never "disappear"
if 'signal_cache' not in st.session_state:
    st.session_state.signal_cache = {"bias": "NEUTRAL", "lev": "WAITING", "conf": 0, "clr": "#555"}
if 'last_sync' not in st.session_state: 
    st.session_state.last_sync = time.time()
if 'chart_tf' not in st.session_state: 
    st.session_state.chart_tf = "1h"

# 2. SYNC LOGIC (66 Seconds)
elapsed = time.time() - st.session_state.last_sync
remaining = max(0, int(66 - elapsed))

if elapsed >= 66 or st.session_state.signal_cache["bias"] == "NEUTRAL":
    # Perform Calculations and Lock them in Session State
    tfs = ["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d"]
    longs, shorts = 0, 0
    
    for t in tfs:
        df, _, _, ok = fetch_base_data(t)
        if ok:
            p, e, s = df['close'].iloc[-1], df['20_ema'].iloc[-1], df['200_sma'].iloc[-1]
            if p > s and p > e: longs += 1
            elif p < s and p < e: shorts += 1
            
    conf = max(longs, shorts)
    if conf >= 4:
        side = "GO LONG" if longs >= shorts else "GO SHORT"
        lev_map = {4: "2x", 5: "3x", 6: "4x", 7: "5x", 8: "5x"}
        st.session_state.signal_cache = {
            "bias": side,
            "lev": f"USE {lev_map.get(conf, '2x')} LEVERAGE",
            "conf": conf,
            "clr": "#0ff0" if "LONG" in side else "#f44"
        }
    else:
        st.session_state.signal_cache = {"bias": "NEUTRAL", "lev": "WAITING FOR 4/8 JUDGES", "conf": conf, "clr": "#555"}
    
    st.session_state.last_sync = time.time()
    st.cache_data.clear()

# 3. UI RENDERING (Uses the Locked Cache)
df_h, btc_p, _, _ = fetch_base_data("1h")
sol_p = df_h['close'].iloc[-1] if df_h is not None else 0

c1, c2 = st.columns(2)
c1.markdown(f"<h1 style='text-align:center; font-size:60px;'>SOL: ${sol_p:,.2f}</h1>", unsafe_allow_html=True)
c2.markdown(f"<h1 style='text-align:center; font-size:60px;'>BTC: ${btc_p:,.2f}</h1>", unsafe_allow_html=True)

# 4. GLOBAL BIAS BOX (Guaranteed Visibility)
sc = st.session_state.signal_cache
st.markdown("---")
st.markdown(
    f"""
    <div style="background-color: #1e2129; border: 5px solid {sc['clr']}; border-radius: 15px; padding: 50px; text-align: center;">
        <p style="color: #888; margin: 0; font-size: 20px; letter-spacing: 2px;">SREEJAN INTELLIGENCE CONSENSUS</p>
        <h1 style="color: white; font-size: 80px; margin: 15px 0; font-weight: bold;">
            GLOBAL BIAS: <span style="color: {sc['clr']};">{sc['bias']}</span>
        </h1>
        <h2 style="color: {sc['clr']}; font-size: 50px; margin: 10px 0;">
            {sc['lev']}
        </h2>
        <p style="color: #666; font-size: 18px; margin-top: 20px;">
            Confidence: {sc['conf']}/8 Judges | Logic: EMA 20 + SMA 200 | Next Sync: {remaining}s
        </p>
    </div>
    """, unsafe_allow_html=True
)

# 5. CHART & CONTROLS
st.markdown("---")
nav = st.columns(8)
tfs_list = ["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d"]
for i, t in enumerate(tfs_list):
    if nav[i].button(t, key=f"btn_{t}", use_container_width=True):
        st.session_state.chart_tf = t
        st.rerun()

df_c, _, _, _ = fetch_base_data(st.session_state.chart_tf)
if df_c is not None:
    fig = go.Figure(data=[go.Candlestick(x=df_c['date'], open=df_c['open'], high=df_c['high'], low=df_c['low'], close=df_c['close'])])
    fig.add_trace(go.Scatter(x=df_c['date'], y=df_c['20_ema'], name="20 EMA", line=dict(color="#854CE6")))
    fig.add_trace(go.Scatter(x=df_c['date'], y=df_c['200_sma'], name="200 SMA", line=dict(color="#FF9900", dash='dot')))
    fig.update_layout(template="plotly_dark", height=500, margin=dict(l=0,r=0,t=0,b=0), xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)
