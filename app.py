import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
from streamlit_autorefresh import st_autorefresh
from data_engine import fetch_base_data

# 1. UI INITIALIZATION
st.set_page_config(page_title="Sreejan Sentinel: Final Stability", layout="wide")
st_autorefresh(interval=1000, key="ui_pulse")

if 'last_market_update' not in st.session_state: 
    st.session_state.last_market_update = time.time()
if 'chart_tf' not in st.session_state:
    st.session_state.chart_tf = "1h"

# 2. 66s SYNC RULE
elapsed = time.time() - st.session_state.last_market_update
remaining = max(0, int(66 - elapsed))

if elapsed >= 66:
    st.cache_data.clear()
    st.session_state.last_market_update = time.time()
    st.rerun()

# 3. GLOBAL PRICES
df_main, btc_p, err, status = fetch_base_data("1h")

if status:
    sol_p = df_main['close'].iloc[-1]
    
    # Large Header Metrics
    m1, m2 = st.columns(2)
    m1.markdown(f"<h1 style='text-align: center; font-size: 60px;'>SOL: ${sol_p:,.2f}</h1>", unsafe_allow_html=True)
    m2.markdown(f"<h1 style='text-align: center; font-size: 60px;'>BTC: ${btc_p:,.2f}</h1>", unsafe_allow_html=True)

    with st.sidebar:
        st.header("⚙️ Status")
        st.info(f"🔄 Sync In: {remaining}s")
        if st.button("Manual Refresh"):
            st.cache_data.clear()
            st.session_state.last_market_update = time.time()
            st.rerun()

    # 4. THE 8-JUDGE MATRIX (RESTORED 12H)
    st.markdown("### 🏛️ Consensus Judge Matrix")
    # Ensuring all 8 judges are present as per rules
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

    # 5. THE GLOBAL BIAS BOX (GO LONG/SHORT + LEVERAGE)
    st.markdown("---")
    
    # Calculate Signal Logic
    tr_count = max(tr_longs, tr_shorts)
    is_signal = tr_count >= 4
    direction = "GO LONG" if tr_longs >= tr_shorts else "GO SHORT"
    
    # Leverage Rules
    lev_map = {4: "2x", 5: "3x", 6: "4x", 7: "5x", 8: "5x"}
    final_lev = lev_map.get(tr_count, "Wait for Consensus") if is_signal else "Wait for Consensus"
    
    # Style logic for the Box
    box_clr = "#0ff0" if (direction == "GO LONG" and is_signal) else "#f44" if is_signal else "#555"
    box_text = direction if is_signal else "NEUTRAL"

    # Aggressive HTML injection to ensure the content is NOT missing
    st.markdown(
        f"""
        <div style="background-color: #262730; border: 4px solid {box_clr}; border-radius: 15px; padding: 40px; text-align: center;">
            <h1 style="color: white; margin-bottom: 0px; font-size: 50px;">GLOBAL BIAS: <span style="color: {box_clr};">{box_text}</span></h1>
            <p style="color: #aaa; font-size: 20px;">Matrix Confidence: {tr_count}/8 Judges | Rules: 20 EMA + 200 SMA</p>
            <h2 style="color: white; font-size: 45px; margin-top: 10px;">Leverage: <span style="color: {box_clr};">{final_lev}</span></h2>
        </div>
        """, unsafe_allow_html=True
    )

    # 6. CHART NAVIGATION & CHART
    st.markdown("---")
    st.write("### 📈 Chart Control")
    nav_btns = st.columns(8)
    for i, t in enumerate(tfs):
        if nav_btns[i].button(t, key=f"nav_{t}", use_container_width=True):
            st.session_state.chart_tf = t
            st.rerun()

    df_chart, _, _, c_status = fetch_base_data(st.session_state.chart_tf)
    if c_status:
        fig = go.Figure(data=[go.Candlestick(
            x=df_chart['date'], open=df_chart['open'], high=df_chart['high'], 
            low=df_chart['low'], close=df_chart['close'], name="Price"
        )])
        fig.add_trace(go.Scatter(x=df_chart['date'], y=df_chart['20_ema'], name="20 EMA", line=dict(color="#854CE6")))
        fig.add_trace(go.Scatter(x=df_chart['date'], y=df_chart['200_sma'], name="200 SMA", line=dict(color="#FF9900", dash='dot')))
        fig.update_layout(template="plotly_dark", height=500, margin=dict(l=0,r=0,t=0,b=0), xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

else:
    st.error(f"Engine Offline: {err}")
