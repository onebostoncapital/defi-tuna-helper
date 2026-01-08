import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
from streamlit_autorefresh import st_autorefresh
from data_engine import fetch_base_data

# 1. PAGE CONFIG & AUTO-REFRESH
st.set_page_config(page_title="Sreejan Sentinel Pro", layout="wide")
st_autorefresh(interval=3000, key="global_sync")

# 2. PERSISTENT CHART STATE
if 'chart_tf' not in st.session_state:
    st.session_state.chart_tf = "1h"

# 3. CORE LOGIC ENGINE (Restored)
tfs = ["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d"]
matrix_data = []
l_votes, s_votes = 0, 0

# Fetch all data at once to ensure consensus is accurate
for t in tfs:
    df, _, _, ok = fetch_base_data(t)
    if ok and not df.empty:
        p, e, s = df['close'].iloc[-1], df['20_ema'].iloc[-1], df['200_sma'].iloc[-1]
        if p > s and p > e:
            matrix_data.append({"tf": t, "sig": "🟢 LONG", "clr": "#0ff0"})
            l_votes += 1
        elif p < s and p < e:
            matrix_data.append({"tf": t, "sig": "🔴 SHORT", "clr": "#f44"})
            s_votes += 1
        else:
            matrix_data.append({"tf": t, "sig": "🟡 WAIT", "clr": "#f1c40f"})
    else:
        # Fallback to prevent "Messed up" UI boxes
        matrix_data.append({"tf": t, "sig": "⚪ SYNC", "clr": "#555"})

# Calculate Global Bias
total_active = l_votes + s_votes
confidence = max(l_votes, s_votes)

if confidence >= 4:
    bias_text = "GO LONG" if l_votes >= s_votes else "GO SHORT"
    bias_clr = "#0ff0" if "LONG" in bias_text else "#f44"
    lev_map = {4: "2x", 5: "3x", 6: "4x", 7: "5x", 8: "5x"}
    lev_text = f"USE {lev_map.get(confidence, '2x')} LEVERAGE"
else:
    bias_text = "NEUTRAL"
    bias_clr = "#888"
    lev_text = "WAIT FOR CONSENSUS"

# 4. UI: HEADER (SOL & BTC)
df_h, btc_p, _, _ = fetch_base_data("1h")
sol_p = df_h['close'].iloc[-1] if df_h is not None else 0
c1, c2 = st.columns(2)
c1.markdown(f"<h1 style='text-align:center; font-size:65px;'>SOL: ${sol_p:,.2f}</h1>", unsafe_allow_html=True)
c2.markdown(f"<h1 style='text-align:center; font-size:65px;'>BTC: ${btc_p:,.2f}</h1>", unsafe_allow_html=True)

# 5. UI: RESTORED JUDGE MATRIX
st.write("### 🏛️ Consensus Judge Matrix")
cols = st.columns(8)
for i, item in enumerate(matrix_data):
    cols[i].markdown(
        f"""<div style="border:2px solid {item['clr']}; border-radius:10px; padding:15px; text-align:center; background: rgba(0,0,0,0.3);">
            <b style="font-size:18px; color:white;">{item['tf']}</b><br>
            <span style="color:{item['clr']}; font-size:16px; font-weight:bold;">{item['sig']}</span>
        </div>""", unsafe_allow_html=True
    )

# 6. UI: GLOBAL BIAS BOX
st.markdown("---")
st.markdown(
    f"""
    <div style="background-color: #161a1e; border: 5px solid {bias_clr}; border-radius: 20px; padding: 60px; text-align: center;">
        <p style="color: #888; margin: 0; font-size: 20px; letter-spacing: 3px;">SREEJAN INTELLIGENCE CONSENSUS</p>
        <h1 style="color: white; font-size: 95px; margin: 15px 0; font-weight: 900; line-height: 1;">
            GLOBAL BIAS: <span style="color: {bias_clr};">{bias_text}</span>
        </h1>
        <h2 style="color: {bias_clr}; font-size: 60px; margin: 10px 0; font-weight: 700;">
            {lev_text}
        </h2>
        <p style="color: #666; font-size: 18px; margin-top: 30px;">
            Confidence: {confidence}/8 Judges | Logic: EMA 20 + SMA 200
        </p>
    </div>
    """, unsafe_allow_html=True
)

# 7. UI: CHART SECTION
st.markdown("---")
nav = st.columns(8)
for i, t in enumerate(tfs):
    if nav[i].button(t, key=f"btn_{t}", use_container_width=True):
        st.session_state.chart_tf = t
        st.rerun()

df_chart, _, _, _ = fetch_base_data(st.session_state.chart_tf)
if df_chart is not None:
    fig = go.Figure(data=[go.Candlestick(x=df_chart['date'], open=df_chart['open'], high=df_chart['high'], low=df_chart['low'], close=df_chart['close'])])
    fig.add_trace(go.Scatter(x=df_chart['date'], y=df_chart['20_ema'], name="20 EMA", line=dict(color="#854CE6")))
    fig.add_trace(go.Scatter(x=df_chart['date'], y=df_chart['200_sma'], name="200 SMA", line=dict(color="#FF9900", dash='dot')))
    fig.update_layout(template="plotly_dark", height=600, margin=dict(l=0,r=0,t=0,b=0), xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)
