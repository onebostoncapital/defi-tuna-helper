import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
from streamlit_autorefresh import st_autorefresh
from data_engine import fetch_base_data

# 1. INITIALIZATION & SYNC
st.set_page_config(page_title="Sreejan Sentinel Pro", layout="wide")
st_autorefresh(interval=1000, key="pulse")

if 'last_upd' not in st.session_state: st.session_state.last_upd = time.time()
if 'chart_tf' not in st.session_state: st.session_state.chart_tf = "1h"

# 66s Sync Logic
elapsed = time.time() - st.session_state.last_upd
remaining = max(0, int(66 - elapsed))
if elapsed >= 66:
    st.cache_data.clear()
    st.session_state.last_upd = time.time()
    st.rerun()

# 2. DATA PRE-CALCULATION (Fixes the blank box)
tfs = ["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d"]
long_votes, short_votes = 0, 0
judge_results = []

for t in tfs:
    df, btc_p, _, ok = fetch_base_data(t)
    if ok:
        p, e, s = df['close'].iloc[-1], df['20_ema'].iloc[-1], df['200_sma'].iloc[-1]
        if p > s and p > e:
            judge_results.append({"tf": t, "sig": "🟢 LONG", "clr": "#0ff0"})
            long_votes += 1
        elif p < s and p < e:
            judge_results.append({"tf": t, "sig": "🔴 SHORT", "clr": "#f44"})
            short_votes += 1
        else:
            judge_results.append({"tf": t, "sig": "🟡 WAIT", "clr": "#888"})

# 3. GLOBAL BIAS LOGIC (Calculated before drawing UI)
conf_score = max(long_votes, short_votes)
is_valid_sig = conf_score >= 4
final_dir = "GO LONG" if long_votes >= short_votes else "GO SHORT"

lev_map = {4: "2x", 5: "3x", 6: "4x", 7: "5x", 8: "5x"}
final_lev = f"USE {lev_map.get(conf_score, 'WAIT')} LEVERAGE" if is_valid_sig else "WAITING FOR CONSENSUS"

# Box Styling
status_color = "#0ff0" if (is_valid_sig and "LONG" in final_dir) else "#f44" if is_valid_sig else "#555"
display_bias = final_dir if is_valid_sig else "NEUTRAL"

# 4. UI: HEADER & MATRIX
df_h, btc_price, _, _ = fetch_base_data("1h")
sol_price = df_h['close'].iloc[-1] if df_h is not None else 0

c1, c2 = st.columns(2)
c1.markdown(f"<h1 style='text-align:center; font-size:60px;'>SOL: ${sol_price:,.2f}</h1>", unsafe_allow_html=True)
c2.markdown(f"<h1 style='text-align:center; font-size:60px;'>BTC: ${btc_price:,.2f}</h1>", unsafe_allow_html=True)

st.write("### 🏛️ Consensus Judge Matrix")
m_cols = st.columns(8)
for i, res in enumerate(judge_results):
    m_cols[i].markdown(f"<div style='border:1px solid {res['clr']}; border-radius:5px; padding:10px; text-align:center;'><b>{res['tf']}</b><br>{res['sig']}</div>", unsafe_allow_html=True)

# 5. UI: GLOBAL BIAS BOX (Guaranteed Render)
st.markdown("---")
st.markdown(
    f"""
    <div style="background-color: #1e2129; border: 5px solid {status_color}; border-radius: 15px; padding: 50px; text-align: center;">
        <p style="color: #888; margin: 0; font-size: 20px; letter-spacing: 2px;">SREEJAN INTELLIGENCE CONSENSUS</p>
        <h1 style="color: white; font-size: 75px; margin: 15px 0; font-weight: 800;">
            GLOBAL BIAS: <span style="color: {status_color};">{display_bias}</span>
        </h1>
        <h2 style="color: {status_color}; font-size: 50px; margin: 10px 0; font-weight: 600;">
            {final_lev}
        </h2>
        <p style="color: #666; font-size: 18px; margin-top: 20px;">
            Confidence: {conf_score}/8 Judges | Sync: {remaining}s
        </p>
    </div>
    """, unsafe_allow_html=True
)

# 6. UI: CHART
st.markdown("---")
nav = st.columns(8)
for i, t in enumerate(tfs):
    if nav[i].button(t, key=f"v_{t}", use_container_width=True):
        st.session_state.chart_tf = t
        st.rerun()

df_c, _, _, _ = fetch_base_data(st.session_state.chart_tf)
if df_c is not None:
    fig = go.Figure(data=[go.Candlestick(x=df_c['date'], open=df_c['open'], high=df_c['high'], low=df_c['low'], close=df_c['close'])])
    fig.add_trace(go.Scatter(x=df_c['date'], y=df_c['20_ema'], name="20 EMA", line=dict(color="#854CE6")))
    fig.add_trace(go.Scatter(x=df_c['date'], y=df_c['200_sma'], name="200 SMA", line=dict(color="#FF9900", dash='dot')))
    fig.update_layout(template="plotly_dark", height=500, margin=dict(l=0,r=0,t=0,b=0), xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)
