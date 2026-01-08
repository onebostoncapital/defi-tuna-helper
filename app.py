import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
from streamlit_autorefresh import st_autorefresh
from data_engine import fetch_base_data

# 1. SETUP
st.set_page_config(page_title="Sreejan Sentinel Pro", layout="wide")
st_autorefresh(interval=1000, key="ui_pulse")

if 'last_market_update' not in st.session_state: 
    st.session_state.last_market_update = time.time()
if 'chart_tf' not in st.session_state:
    st.session_state.chart_tf = "1h"

# 2. 66s SYNC
elapsed = time.time() - st.session_state.last_market_update
remaining = max(0, int(66 - elapsed))

if elapsed >= 66:
    st.cache_data.clear()
    st.session_state.last_market_update = time.time()
    st.rerun()

# 3. PRICES
df_main, btc_p, err, status = fetch_base_data("1h")

if status:
    sol_p = df_main['close'].iloc[-1]
    
    # Large Header
    c1, c2 = st.columns(2)
    c1.markdown(f"<h1 style='text-align: center; font-size: 55px;'>SOL: ${sol_p:,.2f}</h1>", unsafe_allow_html=True)
    c2.markdown(f"<h1 style='text-align: center; font-size: 55px;'>BTC: ${btc_p:,.2f}</h1>", unsafe_allow_html=True)

    # 4. 8-JUDGE MATRIX (NOW WITH 12H)
    st.markdown("### 🏛️ Consensus Judge Matrix")
    tfs = ["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d"]
    mcols = st.columns(8)
    tr_longs, tr_shorts = 0, 0

    for i, t in enumerate(tfs):
        dm, _, _, sm = fetch_base_data(t)
        if sm:
            p, e, s = dm['close'].iloc[-1], dm['20_ema'].iloc[-1], dm['200_sma'].iloc[-1]
            if p > s and p > e:
                sig, clr, bg = "🟢 LONG", "#0ff0", "rgba(0,255,0,0.1)"
                tr_longs += 1
            elif p < s and p < e:
                sig, clr, bg = "🔴 SHORT", "#f44", "rgba(255,0,0,0.1)"
                tr_shorts += 1
            else:
                sig, clr, bg = "🟡 WAIT", "#888", "rgba(128,128,128,0.1)"
            
            mcols[i].markdown(
                f"<div style='border:1px solid {clr}; border-radius:5px; padding:10px; "
                f"background-color:{bg}; text-align:center;'><b>{t}</b><br>{sig}</div>", 
                unsafe_allow_html=True
            )

    # 5. FIXED GLOBAL BIAS BOX
    st.markdown("---")
    tr_count = max(tr_longs, tr_shorts)
    is_signal = tr_count >= 4
    
    # Force Strings for display to prevent blank boxes
    final_dir = "GO LONG" if tr_longs >= tr_shorts else "GO SHORT"
    lev_map = {4: "2x", 5: "3x", 6: "4x", 7: "5x", 8: "5x"}
    final_lev = lev_map.get(tr_count, "Wait for Consensus") if is_signal else "Wait for Consensus"
    
    box_clr = "#0ff0" if (tr_longs >= tr_shorts and is_signal) else "#f44" if is_signal else "#666"
    display_bias = final_dir if is_signal else "NEUTRAL"

    st.markdown(
        f"""
        <div style="background-color: #262730; border: 5px solid {box_clr}; border-radius: 15px; padding: 40px; text-align: center;">
            <h1 style="color: white; font-size: 55px; margin-bottom: 0px;">GLOBAL BIAS: <span style="color: {box_clr};">{display_bias}</span></h1>
            <p style="color: #aaa; font-size: 20px;">Matrix Confidence: {tr_count}/8 Judges | Sync: {remaining}s</p>
            <h2 style="color: white; font-size: 45px; margin-top: 10px;">Leverage: <span style="color: {box_clr};">{final_lev}</span></h2>
        </div>
        """, unsafe_allow_html=True
    )

    # 6. CHART
    st.markdown("---")
    nav = st.columns(8)
    for i, t in enumerate(tfs):
        if nav[i].button(t, key=f"v_{t}", use_container_width=True):
            st.session_state.chart_tf = t
            st.rerun()

    df_c, _, _, c_st = fetch_base_data(st.session_state.chart_tf)
    if c_st:
        fig = go.Figure(data=[go.Candlestick(x=df_c['date'], open=df_c['open'], high=df_c['high'], low=df_c['low'], close=df_c['close'])])
        fig.add_trace(go.Scatter(x=df_c['date'], y=df_c['20_ema'], name="20 EMA", line=dict(color="#854CE6")))
        fig.add_trace(go.Scatter(x=df_c['date'], y=df_c['200_sma'], name="200 SMA", line=dict(color="#FF9900", dash='dot')))
        fig.update_layout(template="plotly_dark", height=500, margin=dict(l=0,r=0,t=0,b=0), xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

else:
    st.error(f"Engine Reconnecting... {err}")
