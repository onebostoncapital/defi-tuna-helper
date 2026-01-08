import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
from streamlit_autorefresh import st_autorefresh
from data_engine import fetch_base_data

# 1. SETUP & SYNC
st.set_page_config(page_title="Sreejan Sentinel Pro", layout="wide")
st_autorefresh(interval=1000, key="ui_pulse")

if 'last_market_update' not in st.session_state: st.session_state.last_market_update = time.time()
if 'chart_tf' not in st.session_state: st.session_state.chart_tf = "1h"

elapsed = time.time() - st.session_state.last_market_update
remaining = max(0, int(66 - elapsed))

if elapsed >= 66:
    st.cache_data.clear()
    st.session_state.last_market_update = time.time()
    st.rerun()

# 2. PRE-CALCULATE ALL JUDGES (FIX: Pre-loop ensures data is ready)
tfs = ["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d"]
judge_results = []
long_votes = 0
short_votes = 0

for t in tfs:
    df, btc_p, _, ok = fetch_base_data(t)
    if ok:
        p, e, s = df['close'].iloc[-1], df['20_ema'].iloc[-1], df['200_sma'].iloc[-1]
        if p > s and p > e:
            judge_results.append({"tf": t, "sig": "🟢 LONG", "clr": "#0ff0", "bg": "rgba(0,255,0,0.1)"})
            long_votes += 1
        elif p < s and p < e:
            judge_results.append({"tf": t, "sig": "🔴 SHORT", "clr": "#f44", "bg": "rgba(255,0,0,0.1)"})
            short_votes += 1
        else:
            judge_results.append({"tf": t, "sig": "🟡 WAIT", "clr": "#888", "bg": "rgba(128,128,128,0.1)"})

# 3. FINAL BIAS CALCULATIONS
consensus_count = max(long_votes, short_votes)
is_valid_signal = consensus_count >= 4
direction = "GO LONG" if long_votes >= short_votes else "GO SHORT"

lev_map = {4: "2x", 5: "3x", 6: "4x", 7: "5x", 8: "5x"}
recommended_lev = f"USE {lev_map.get(consensus_count, 'WAIT')} LEVERAGE" if is_valid_signal else "WAITING FOR CONSENSUS"

# Color logic for the box
final_color = "#0ff0" if (is_valid_signal and "LONG" in direction) else "#f44" if is_valid_signal else "#555"
final_bias_text = direction if is_valid_signal else "NEUTRAL"

# 4. UI: HEADER
df_main, btc_val, _, _ = fetch_base_data("1h")
sol_val = df_main['close'].iloc[-1] if df_main is not None else 0

c1, c2 = st.columns(2)
c1.markdown(f"<h1 style='text-align:center; font-size:60px;'>SOL: ${sol_val:,.2f}</h1>", unsafe_allow_html=True)
c2.markdown(f"<h1 style='text-align:center; font-size:60px;'>BTC: ${btc_val:,.2f}</h1>", unsafe_allow_html=True)

# 5. UI: JUDGE MATRIX
st.write("### 🏛️ Consensus Judge Matrix")
mcols = st.columns(8)
for i, res in enumerate(judge_results):
    mcols[i].markdown(f"<div style='border:1px solid {res['clr']}; border-radius:5px; padding:10px; background-color:{res['bg']}; text-align:center;'><b>{res['tf']}</b><br>{res['sig']}</div>", unsafe_allow_html=True)

# 6. UI: GLOBAL BIAS BOX (THE RENDERING FIX)
st.markdown("---")
st.markdown(
    f"""
    <div style="background-color: #1e2129; border: 5px solid {final_color}; border-radius: 15px; padding: 50px; text-align: center;">
        <p style="color: #888; margin: 0; font-size: 20px; letter-spacing: 2px;">SREEJAN INTELLIGENCE CONSENSUS</p>
        <h1 style="color: white; font-size: 75px; margin: 15px 0; font-weight: bold;">
            GLOBAL BIAS: <span style="color: {final_color};">{final_bias_text}</span>
        </h1>
        <h2 style="color: {final_color}; font-size: 50px; margin: 10px 0;">
            {recommended_lev}
        </h2>
        <p style="color: #666; font-size: 18px; margin-top: 20px;">
            Confidence: {consensus_count}/8 Judges | Logic: 20 EMA + 200 SMA | Sync: {remaining}s
        </p>
    </div>
    """, unsafe_allow_html=True
)

# 7. UI: CHART CONTROLS & PLOT
st.markdown("---")
nav = st.columns(8)
for i, t in enumerate(tfs):
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
