import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
from streamlit_autorefresh import st_autorefresh
from data_engine import fetch_base_data

# 1. SETUP & PERSISTENCE
st.set_page_config(page_title="Sreejan Sentinel Pro", layout="wide")
st_autorefresh(interval=3000, key="global_sync") # 3s refresh is safer for API limits

# Initialize the 'Solid Cache' so boxes are never blank
tfs_list = ["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d"]

if 'matrix_storage' not in st.session_state:
    st.session_state.matrix_storage = [{"tf": t, "sig": "SYNCING", "clr": "#555"} for t in tfs_list]
if 'signal_storage' not in st.session_state:
    st.session_state.signal_storage = {"bias": "ANALYZING", "lev": "WAITING", "conf": 0, "clr": "#555"}
if 'last_sync_time' not in st.session_state: 
    st.session_state.last_sync_time = 0
if 'chart_tf' not in st.session_state: 
    st.session_state.chart_tf = "1h"

# 2. BACKGROUND CALCULATION ENGINE
now = time.time()
# Only recalculate every 66 seconds to avoid Yahoo Finance rate limits
if (now - st.session_state.last_sync_time) > 66 or st.session_state.signal_storage["bias"] == "ANALYZING":
    new_matrix = []
    long_count, short_count = 0, 0
    
    # We use a temporary list so the UI doesn't see "half-finished" data
    for t in tfs_list:
        df, _, _, ok = fetch_base_data(t)
        if ok and not df.empty:
            price = df['close'].iloc[-1]
            ema20 = df['20_ema'].iloc[-1]
            sma200 = df['200_sma'].iloc[-1]
            
            if price > sma200 and price > ema20:
                new_matrix.append({"tf": t, "sig": "🟢 LONG", "clr": "#0ff0"})
                long_count += 1
            elif price < sma200 and price < ema20:
                new_matrix.append({"tf": t, "sig": "🔴 SHORT", "clr": "#f44"})
                short_count += 1
            else:
                new_matrix.append({"tf": t, "sig": "🟡 WAIT", "clr": "#f1c40f"})
        else:
            new_matrix.append({"tf": t, "sig": "⚪ NO DATA", "clr": "#555"})
    
    # Update Session State ONLY after the loop is 100% complete
    st.session_state.matrix_storage = new_matrix
    total_conf = max(long_count, short_count)
    
    if total_conf >= 4:
        side = "GO LONG" if long_count >= short_count else "GO SHORT"
        lev_map = {4: "2x", 5: "3x", 6: "4x", 7: "5x", 8: "5x"}
        st.session_state.signal_storage = {
            "bias": side, 
            "lev": f"USE {lev_map.get(total_conf, '2x')} LEVERAGE",
            "conf": total_conf, 
            "clr": "#0ff0" if "LONG" in side else "#f44"
        }
    else:
        st.session_state.signal_storage = {
            "bias": "NEUTRAL", "lev": "WAIT FOR CONSENSUS", "conf": total_conf, "clr": "#555"
        }
    st.session_state.last_sync_time = now

# 3. HEADER RENDERING
df_h, btc_p, _, _ = fetch_base_data("1h")
sol_p = df_h['close'].iloc[-1] if df_h is not None else 0
c1, c2 = st.columns(2)
c1.markdown(f"<h1 style='text-align:center; font-size:60px;'>SOL: ${sol_p:,.2f}</h1>", unsafe_allow_html=True)
c2.markdown(f"<h1 style='text-align:center; font-size:60px;'>BTC: ${btc_p:,.2f}</h1>", unsafe_allow_html=True)

# 4. RESTORED JUDGE MATRIX (Uses Atomic Cache)
st.write("### 🏛️ Consensus Judge Matrix")
m_cols = st.columns(8)
for i, item in enumerate(st.session_state.matrix_storage):
    # Using a fixed-height container to prevent layout jumping
    m_cols[i].markdown(
        f"""<div style="border:2px solid {item['clr']}; border-radius:10px; padding:15px; text-align:center; background: rgba(0,0,0,0.3); min-height:80px;">
            <b style="font-size:18px; color:white;">{item['tf']}</b><br>
            <span style="color:{item['clr']}; font-size:15px; font-weight:bold;">{item['sig']}</span>
        </div>""", unsafe_allow_html=True
    )

# 5. GLOBAL BIAS BOX (Uses Atomic Cache)
ss = st.session_state.signal_storage
rem = max(0, int(66 - (time.time() - st.session_state.last_sync_time)))

st.markdown("---")
st.markdown(
    f"""
    <div style="background-color: #1e2129; border: 5px solid {ss['clr']}; border-radius: 15px; padding: 50px; text-align: center;">
        <p style="color: #888; margin: 0; font-size: 18px; letter-spacing: 2px;">SREEJAN INTELLIGENCE CONSENSUS</p>
        <h1 style="color: white; font-size: 85px; margin: 10px 0; font-weight: 900;">
            GLOBAL BIAS: <span style="color: {ss['clr']};">{ss['bias']}</span>
        </h1>
        <h2 style="color: {ss['clr']}; font-size: 55px; margin: 5px 0;">
            {ss['lev']}
        </h2>
        <p style="color: #666; font-size: 16px; margin-top: 25px;">
            Confidence: {ss['conf']}/8 Judges | Next Sync: {rem}s
        </p>
    </div>
    """, unsafe_allow_html=True
)

# 6. CHART SECTION
st.markdown("---")
nav = st.columns(8)
for i, t in enumerate(tfs_list):
    if nav[i].button(t, key=f"nav_btn_{t}", use_container_width=True):
        st.session_state.chart_tf = t
        st.rerun()

df_plot, _, _, _ = fetch_base_data(st.session_state.chart_tf)
if df_plot is not None:
    fig = go.Figure(data=[go.Candlestick(x=df_plot['date'], open=df_plot['open'], high=df_plot['high'], low=df_plot['low'], close=df_plot['close'])])
    fig.add_trace(go.Scatter(x=df_plot['date'], y=df_plot['20_ema'], name="20 EMA", line=dict(color="#854CE6")))
    fig.add_trace(go.Scatter(x=df_plot['date'], y=df_plot['200_sma'], name="200 SMA", line=dict(color="#FF9900", dash='dot')))
    fig.update_layout(template="plotly_dark", height=500, margin=dict(l=0,r=0,t=0,b=0), xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)
