import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
from streamlit_autorefresh import st_autorefresh
from data_engine import fetch_base_data

# 1. PERMANENT STATE STORAGE
st.set_page_config(page_title="Sreejan Sentinel Pro", layout="wide")
st_autorefresh(interval=2000, key="broadcast_pulse")

# Initialize memory to survive refreshes
if 'signal_lock' not in st.session_state:
    st.session_state.signal_lock = {"bias": "ANALYZING", "lev": "WAITING", "conf": 0, "clr": "#555"}
if 'matrix_lock' not in st.session_state:
    st.session_state.matrix_lock = []
if 'last_sync' not in st.session_state: 
    st.session_state.last_sync = 0
if 'chart_tf' not in st.session_state: 
    st.session_state.chart_tf = "1h"

# 2. THE ENGINE (Calculates everything then "Locks" it)
now = time.time()
if (now - st.session_state.last_sync) > 66 or not st.session_state.matrix_lock:
    tfs = ["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d"]
    temp_matrix = []
    l_votes, s_votes = 0, 0
    
    for t in tfs:
        df, _, _, ok = fetch_base_data(t)
        if ok:
            p, e, s = df['close'].iloc[-1], df['20_ema'].iloc[-1], df['200_sma'].iloc[-1]
            if p > s and p > e:
                temp_matrix.append({"tf": t, "sig": "🟢 LONG", "clr": "#0ff0"})
                l_votes += 1
            elif p < s and p < e:
                temp_matrix.append({"tf": t, "sig": "🔴 SHORT", "clr": "#f44"})
                s_votes += 1
            else:
                temp_matrix.append({"tf": t, "sig": "🟡 WAIT", "clr": "#888"})
    
    # Update the Locks
    st.session_state.matrix_lock = temp_matrix
    conf = max(l_votes, s_votes)
    
    if conf >= 4:
        side = "GO LONG" if l_votes >= s_votes else "GO SHORT"
        lev_map = {4: "2x", 5: "3x", 6: "4x", 7: "5x", 8: "5x"}
        st.session_state.signal_lock = {
            "bias": side,
            "lev": f"USE {lev_map.get(conf, '2x')} LEVERAGE",
            "conf": conf,
            "clr": "#0ff0" if "LONG" in side else "#f44"
        }
    else:
        st.session_state.signal_lock = {"bias": "NEUTRAL", "lev": "WAIT FOR CONSENSUS", "conf": conf, "clr": "#555"}
    
    st.session_state.last_sync = now

# 3. UI: HEADER
df_h, btc_p, _, _ = fetch_base_data("1h")
sol_p = df_h['close'].iloc[-1] if df_h is not None else 0

c1, c2 = st.columns(2)
c1.markdown(f"<h1 style='text-align:center; font-size:60px;'>SOL: ${sol_p:,.2f}</h1>", unsafe_allow_html=True)
c2.markdown(f"<h1 style='text-align:center; font-size:60px;'>BTC: ${btc_p:,.2f}</h1>", unsafe_allow_html=True)

# 4. UI: RESTORED JUDGE MATRIX
st.write("### 🏛️ Consensus Judge Matrix")
m_cols = st.columns(8)
for i, item in enumerate(st.session_state.matrix_lock):
    m_cols[i].markdown(
        f"""<div style="border:1px solid {item['clr']}; border-radius:5px; padding:10px; text-align:center; background: rgba(255,255,255,0.05);">
            <b style="font-size:14px;">{item['tf']}</b><br><span style="color:{item['clr']}; font-size:12px;">{item['sig']}</span>
        </div>""", unsafe_allow_html=True
    )

# 5. UI: GLOBAL BIAS BOX (HARD-LOCKED)
sl = st.session_state.signal_lock
remaining = max(0, int(66 - (time.time() - st.session_state.last_sync)))

st.markdown("---")
st.markdown(
    f"""
    <div style="background-color: #1e2129; border: 5px solid {sl['clr']}; border-radius: 15px; padding: 50px; text-align: center;">
        <p style="color: #888; margin: 0; font-size: 18px; letter-spacing: 2px;">SREEJAN INTELLIGENCE CONSENSUS</p>
        <h1 style="color: white; font-size: 85px; margin: 10px 0; font-weight: 900;">
            GLOBAL BIAS: <span style="color: {sl['clr']};">{sl['bias']}</span>
        </h1>
        <h2 style="color: {sl['clr']}; font-size: 55px; margin: 5px 0;">
            {sl['lev']}
        </h2>
        <p style="color: #666; font-size: 16px; margin-top: 25px; border-top: 1px solid #333; padding-top: 15px;">
            Confidence: {sl['conf']}/8 Judges | Logic: EMA 20 + SMA 200 | Next Sync: {remaining}s
        </p>
    </div>
    """, unsafe_allow_html=True
)

# 6. UI: CHART
st.markdown("---")
nav = st.columns(8)
t_list = ["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d"]
for i, t in enumerate(t_list):
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
