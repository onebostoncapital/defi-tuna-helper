import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
from streamlit_autorefresh import st_autorefresh
from data_engine import fetch_base_data

# 1. UI INITIALIZATION
st.set_page_config(page_title="Sreejan Sentinel Pro", layout="wide")
st_autorefresh(interval=2000, key="ui_pulse")

if 'chart_tf' not in st.session_state:
    st.session_state.chart_tf = "1h"

# 2. GLOBAL HEADER (BTC & SOL PRICE)
df_main, btc_p, err, status = fetch_base_data("1h")

if status:
    sol_p = df_main['close'].iloc[-1]
    
    # Header Metrics
    m1, m2 = st.columns(2)
    m1.markdown(f"<h1 style='text-align: center;'>SOL: ${sol_p:,.2f}</h1>", unsafe_allow_html=True)
    m2.markdown(f"<h1 style='text-align: center;'>BTC: ${btc_p:,.2f}</h1>", unsafe_allow_html=True)

    # 3. 8-JUDGE CONSENSUS MATRIX
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

    # 4. CONSOLIDATED CONSENSUS BOX
    st.markdown("---")
    tr_count = max(tr_longs, tr_shorts)
    final_dir = "LONG" if tr_longs >= tr_shorts else "SHORT"
    lev_map = {4: 2, 5: 3, 6: 4, 7: 5, 8: 5}
    cur_lev = lev_map.get(tr_count, 0) if tr_count >= 4 else 0
    con_clr = "#0ff0" if final_dir == "LONG" and cur_lev > 0 else "#f44" if cur_lev > 0 else "#888"
    
    st.markdown(
        f"<div style='border:2px solid {con_clr}; border-radius:10px; padding:25px; "
        f"background-color:rgba(0,0,0,0.4); text-align:center;'>"
        f"<h1 style='margin:0;'>GLOBAL BIAS: <span style='color:{con_clr}'>{final_dir if cur_lev > 0 else 'NEUTRAL'}</span></h1>"
        f"<h3>Confidence: {tr_count}/8 Judges | Leverage: {cur_lev}x</h3>"
        f"</div>", unsafe_allow_html=True
    )

    # 5. CHART NAVIGATION BAR
    st.markdown("---")
    st.write("### 📈 Chart Timeframe Navigation")
    nav_btns = st.columns(8)
    for i, t in enumerate(tfs):
        if nav_btns[i].button(t, key=f"nav_{t}", use_container_width=True):
            st.session_state.chart_tf = t
            st.rerun()

    # 6. DYNAMIC CHART
    df_chart, _, _, c_status = fetch_base_data(st.session_state.chart_tf)
    if c_status:
        st.write(f"Displaying **{st.session_state.chart_tf}** Chart")
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
