import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
from streamlit_autorefresh import st_autorefresh
from data_engine import fetch_base_data

# 1. INITIALIZATION
st.set_page_config(page_title="Sreejan Sentinel Pro", layout="wide")
st_autorefresh(interval=1000, key="pulse")

if 'last_upd' not in st.session_state: st.session_state.last_upd = time.time()
if 'chart_tf' not in st.session_state: st.session_state.chart_tf = "1h"

# 2. 66s SYNC RULE
elapsed = time.time() - st.session_state.last_upd
remaining = max(0, int(66 - elapsed))
if elapsed >= 66:
    st.cache_data.clear()
    st.session_state.last_upd = time.time()
    st.rerun()

# 3. PRE-CALCULATE BIAS (Crucial: Done before UI is drawn)
tfs = ["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d"]
longs, shorts = 0, 0
judge_data = []

for t in tfs:
    df, btc_p, _, ok = fetch_base_data(t)
    if ok:
        p, e, s = df['close'].iloc[-1], df['20_ema'].iloc[-1], df['200_sma'].iloc[-1]
        if p > s and p > e:
            judge_data.append({"tf": t, "sig": "🟢 LONG", "clr": "#0ff0"})
            longs += 1
        elif p < s and p < e:
            judge_data.append({"tf": t, "sig": "🔴 SHORT", "clr": "#f44"})
            shorts += 1
        else:
            judge_data.append({"tf": t, "sig": "🟡 WAIT", "clr": "#888"})

# 4. FINAL SIGNAL LOGIC
confidence = max(longs, shorts)
is_valid = confidence >= 4
side = "GO LONG" if longs >= shorts else "GO SHORT"

lev_map = {4: "2x", 5: "3x", 6: "4x", 7: "5x", 8: "5x"}
lev_val = lev_map.get(confidence, "No Signal")

# Color and Text Formatting
box_color = "#0ff0" if (is_valid and "LONG" in side) else "#f44" if is_active else "#555"
final_signal = side if is_valid else "NEUTRAL"
final_leverage = f"USE {lev_val} LEVERAGE" if is_valid else "WAITING FOR CONSENSUS"

# 5. UI DISPLAY - HEADER
df_main, btc_price, _, _ = fetch_base_data("1h")
sol_price = df_main['close'].iloc[-1] if df_main is not None else 0

c1, c2 = st.columns(2)
c1.markdown(f"<h1 style='text-align:center; font-size:60px;'>SOL: ${sol_price:,.2f}</h1>", unsafe_allow_html=True)
c2.markdown(f"<h1 style='text-align:center; font-size:60px;'>BTC: ${btc_price:,.2f}</h1>", unsafe_allow_html=True)

# 6. JUDGE MATRIX
st.write("### 🏛️ Consensus Judge Matrix")
mcols = st.columns(8)
for i, judge in enumerate(judge_data):
    mcols[i].markdown(f"<div style='border:1px solid {judge['clr']}; border-radius:5px; padding:10px; text-align:center;'><b>{judge['tf']}</b><br>{judge['sig']}</div>", unsafe_allow_html=True)

# 7. THE FIXED GLOBAL BIAS BOX
st.markdown("---")
st.markdown(
    f"""
    <div style="background-color: #1e2129; border: 5px solid {box_color}; border-radius: 15px; padding: 50px; text-align: center;">
        <p style="color: #888; margin: 0; font-size: 20px;">SREEJAN INTELLIGENCE CONSENSUS</p>
        <h1 style="color: white; font-size: 70px; margin: 15px 0; font-weight: bold;">
            GLOBAL BIAS: <span style="color: {box_color};">{final_signal}</span>
        </h1>
        <h2 style="color: {box_color}; font-size: 50px; margin: 5px 0;">
            {final_leverage}
        </h2>
        <p style="color: #666; font-size: 18px; margin-top: 20px;">
            Confidence: {confidence}/8 Judges | Logic: EMA 20 + SMA 200 | Next Sync: {remaining}s
        </p>
    </div>
    """, unsafe_allow_html=True
)

# 8. CHART
st.markdown("---")
nav = st.columns(8)
for i, t in enumerate(tfs):
    if nav[i].button(t, key=f"nav_{t}", use_container_width=True):
        st.session_state.chart_tf = t
        st.rerun()

df_c, _, _, _ = fetch_base_data(st.session_state.chart_tf)
if df_c is not None:
    fig = go.Figure(data=[go.Candlestick(x=df_c['date'], open=df_c['open'], high=df_c['high'], low=df_c['low'], close=df_c['close'])])
    fig.add_trace(go.Scatter(x=df_c['date'], y=df_c['20_ema'], name="20 EMA", line=dict(color="#854CE6")))
    fig.add_trace(go.Scatter(x=df_c['date'], y=df_c['200_sma'], name="200 SMA", line=dict(color="#FF9900", dash='dot')))
    fig.update_layout(template="plotly_dark", height=500, margin=dict(l=0,r=0,t=0,b=0), xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)
