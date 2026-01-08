import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
from streamlit_autorefresh import st_autorefresh
from data_engine import fetch_base_data

# 1. PAGE SETUP & PULSE
st.set_page_config(page_title="Sreejan Sentinel Pro", layout="wide")
st_autorefresh(interval=3000, key="global_sync_pulse")

# 2. DATA PERSISTENCE LOCKS
tfs_list = ["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d"]

if 'matrix_state' not in st.session_state:
    st.session_state.matrix_state = [{"tf": t, "sig": "SYNCING...", "clr": "#555"} for t in tfs_list]
if 'signal_state' not in st.session_state:
    st.session_state.signal_state = {"bias": "ANALYZING", "lev": "WAITING", "conf": 0, "clr": "#444"}
if 'last_update' not in st.session_state: 
    st.session_state.last_update = 0
if 'chart_tf' not in st.session_state: 
    st.session_state.chart_tf = "1h"

# 3. ATOMIC CALCULATION ENGINE
now = time.time()
# Sync every 60 seconds. During other refreshes, we show the "Locked" data.
if (now - st.session_state.last_update) > 60 or st.session_state.signal_state["bias"] == "ANALYZING":
    buffer_matrix = []
    l_votes, s_votes = 0, 0
    
    # Hidden loop: prevents UI from seeing empty data
    for t in tfs_list:
        df, b_p, err, ok = fetch_base_data(t)
        if ok and not df.empty:
            p, e, s = df['close'].iloc[-1], df['20_ema'].iloc[-1], df['200_sma'].iloc[-1]
            if p > s and p > e:
                buffer_matrix.append({"tf": t, "sig": "🟢 LONG", "clr": "#0ff0"})
                l_votes += 1
            elif p < s and p < e:
                buffer_matrix.append({"tf": t, "sig": "🔴 SHORT", "clr": "#f44"})
                s_votes += 1
            else:
                buffer_matrix.append({"tf": t, "sig": "🟡 WAIT", "clr": "#f1c40f"})
        else:
            buffer_matrix.append({"tf": t, "sig": "⚪ SYNC", "clr": "#555"})

    # CRITICAL: Atomic Swap. Only update the screen if we have a full set of data
    if len(buffer_matrix) == 8:
        st.session_state.matrix_state = buffer_matrix
        conf = max(l_votes, s_votes)
        
        if conf >= 4:
            side = "GO LONG" if l_votes >= s_votes else "GO SHORT"
            lev_map = {4: "2x", 5: "3x", 6: "4x", 7: "5x", 8: "5x"}
            st.session_state.signal_state = {
                "bias": side, 
                "lev": f"USE {lev_map.get(conf, '2x')} LEVERAGE",
                "conf": conf, 
                "clr": "#0ff0" if "LONG" in side else "#f44"
            }
        else:
            st.session_state.signal_state = {"bias": "NEUTRAL", "lev": "WAIT FOR CONSENSUS", "conf": conf, "clr": "#555"}
        
        st.session_state.last_update = now

# 4. TOP STATS (SOL & BTC)
df_h, btc_p, _, _ = fetch_base_data("1h")
sol_p = df_h['close'].iloc[-1] if df_h is not None else 0
c1, c2 = st.columns(2)
c1.markdown(f"<h1 style='text-align:center; font-size:65px; margin:0;'>SOL: ${sol_p:,.2f}</h1>", unsafe_allow_html=True)
c2.markdown(f"<h1 style='text-align:center; font-size:65px; margin:0;'>BTC: ${btc_p:,.2f}</h1>", unsafe_allow_html=True)

# 5. RESTORED CONSENSUS MATRIX
st.write("### 🏛️ Consensus Judge Matrix")
cols = st.columns(8)
for i, item in enumerate(st.session_state.matrix_state):
    cols[i].markdown(
        f"""<div style="border:2px solid {item['clr']}; border-radius:10px; padding:15px; text-align:center; background: rgba(0,0,0,0.3);">
            <b style="font-size:18px; color:white;">{item['tf']}</b><br>
            <span style="color:{item['clr']}; font-size:16px; font-weight:bold;">{item['sig']}</span>
        </div>""", unsafe_allow_html=True
    )

# 6. GLOBAL BIAS BOX (THE "SOLID-LOCK" UI)
ss = st.session_state.signal_state
rem = max(0, int(60 - (time.time() - st.session_state.last_update)))

st.markdown("---")
st.markdown(
    f"""
    <div style="background-color: #161a1e; border: 5px solid {ss['clr']}; border-radius: 20px; padding: 60px; text-align: center;">
        <p style="color: #888; margin: 0; font-size: 20px; letter-spacing: 3px;">SREEJAN INTELLIGENCE CONSENSUS</p>
        <h1 style="color: white; font-size: 95px; margin: 15px 0; font-weight: 900; line-height: 1;">
            GLOBAL BIAS: <span style="color: {ss['clr']};">{ss['bias']}</span>
        </h1>
        <h2 style="color: {ss['clr']}; font-size: 60px; margin: 10px 0; font-weight: 700;">
            {ss['lev']}
        </h2>
        <p style="color: #666; font-size: 18px; margin-top: 30px;">
            Confidence: {ss['conf']}/8 Judges | Rules: EMA 20 + SMA 200 | Sync In: {rem}s
        </p>
    </div>
    """, unsafe_allow_html=True
)

# 7. CHART SECTION
st.markdown("---")
nav = st.columns(8)
for i, t in enumerate(tfs_list):
    if nav[i].button(t, key=f"btn_{t}", use_container_width=True):
        st.session_state.chart_tf = t
        st.rerun()

df_chart, _, _, _ = fetch_base_data(st.session_state.chart_tf)
if df_chart is not None:
    fig = go.Figure(data=[go.Candlestick(x=df_chart['date'], open=df_chart['open'], high=df_chart['high'], low=df_chart['low'], close=df_chart['close'])])
    fig.add_trace(go.Scatter(x=df_chart['date'], y=df_chart['20_ema'], name="20 EMA", line=dict(color="#854CE6")))
    fig.add_trace(go.Scatter(x=df_chart['date'], y=df_chart['200_sma'], name="200 SMA", line=dict(color="#FF9900", dash='dot')))
    fig.update_layout(template="plotly_dark", height=550, margin=dict(l=0,r=0,t=0,b=0), xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)
