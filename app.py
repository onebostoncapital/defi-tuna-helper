import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
from streamlit_autorefresh import st_autorefresh
from data_engine import fetch_base_data

# 1. PAGE SETUP & AUTOMATIC REFRESH
st.set_page_config(page_title="Sentinel Pro: Signal Fix", layout="wide")
st_autorefresh(interval=1000, key="global_pulse")

if 'last_sync' not in st.session_state: st.session_state.last_sync = time.time()
if 'chart_tf' not in st.session_state: st.session_state.chart_tf = "1h"

# 66s Data Sync Logic
elapsed = time.time() - st.session_state.last_sync
remaining = max(0, int(66 - elapsed))
if elapsed >= 66:
    st.cache_data.clear()
    st.session_state.last_sync = time.time()
    st.rerun()

# 2. PRE-FLIGHT CALCULATION (Fixes the missing text issue)
tfs = ["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d"]
long_votes = 0
short_votes = 0
matrix_summary = []

# Perform all calculations before any UI is rendered
for t in tfs:
    df, btc_price, _, ok = fetch_base_data(t)
    if ok:
        price, ema, sma = df['close'].iloc[-1], df['20_ema'].iloc[-1], df['200_sma'].iloc[-1]
        if price > sma and price > ema:
            matrix_summary.append({"tf": t, "sig": "🟢 LONG", "clr": "#0ff0"})
            long_votes += 1
        elif price < sma and price < ema:
            matrix_summary.append({"tf": t, "sig": "🔴 SHORT", "clr": "#f44"})
            short_votes += 1
        else:
            matrix_summary.append({"tf": t, "sig": "🟡 WAIT", "clr": "#888"})

# 3. LOCK FINAL STRINGS
total_confidence = max(long_votes, short_votes)
is_active = total_confidence >= 4
bias_text = "GO LONG" if long_votes >= short_votes else "GO SHORT"

lev_map = {4: "2x", 5: "3x", 6: "4x", 7: "5x", 8: "5x"}
lev_instruction = f"USE {lev_map.get(total_confidence, 'WAIT')} LEVERAGE"

# Styling Variables
box_border = "#0ff0" if (is_active and "LONG" in bias_text) else "#f44" if is_active else "#444"
final_display_bias = bias_text if is_active else "NEUTRAL"
final_display_lev = lev_instruction if is_active else "WAITING FOR 4/8 JUDGES"

# 4. UI: HEADER
df_main, btc_val, _, _ = fetch_base_data("1h")
sol_val = df_main['close'].iloc[-1] if df_main is not None else 0

c1, c2 = st.columns(2)
c1.markdown(f"<h1 style='text-align:center; font-size:60px;'>SOL: ${sol_val:,.2f}</h1>", unsafe_allow_html=True)
c2.markdown(f"<h1 style='text-align:center; font-size:60px;'>BTC: ${btc_val:,.2f}</h1>", unsafe_allow_html=True)

# 5. UI: JUDGE MATRIX
st.write("### 🏛️ Consensus Judge Matrix")
mcols = st.columns(8)
for i, item in enumerate(matrix_summary):
    mcols[i].markdown(f"<div style='border:1px solid {item['clr']}; border-radius:5px; padding:10px; text-align:center;'><b>{item['tf']}</b><br>{item['sig']}</div>", unsafe_allow_html=True)

# 6. UI: GLOBAL BIAS BOX (INJECTION FIX)
st.markdown("---")
st.markdown(
    f"""
    <div style="background-color: #1e2129; border: 5px solid {box_border}; border-radius: 15px; padding: 50px; text-align: center;">
        <p style="color: #888; margin: 0; font-size: 20px;">SREEJAN INTELLIGENCE CONSENSUS</p>
        <h1 style="color: white; font-size: 75px; margin: 15px 0; font-weight: bold;">
            GLOBAL BIAS: <span style="color: {box_border};">{final_display_bias}</span>
        </h1>
        <h2 style="color: {box_border}; font-size: 50px; margin: 10px 0;">
            {final_display_lev}
        </h2>
        <p style="color: #666; font-size: 18px; margin-top: 20px;">
            Confidence: {total_confidence}/8 Judges | Sync: {remaining}s
        </p>
    </div>
    """, unsafe_allow_html=True
)

# 7. UI: CHARTING
st.markdown("---")
nav = st.columns(8)
for i, t in enumerate(tfs):
    if nav[i].button(t, key=f"nav_{t}", use_container_width=True):
        st.session_state.chart_tf = t
        st.rerun()

df_plot, _, _, _ = fetch_base_data(st.session_state.chart_tf)
if df_plot is not None:
    fig = go.Figure(data=[go.Candlestick(x=df_plot['date'], open=df_plot['open'], high=df_plot['high'], low=df_plot['low'], close=df_plot['close'])])
    fig.add_trace(go.Scatter(x=df_plot['date'], y=df_plot['20_ema'], name="20 EMA", line=dict(color="#854CE6")))
    fig.add_trace(go.Scatter(x=df_plot['date'], y=df_plot['200_sma'], name="200 SMA", line=dict(color="#FF9900", dash='dot')))
    fig.update_layout(template="plotly_dark", height=500, margin=dict(l=0,r=0,t=0,b=0), xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)
