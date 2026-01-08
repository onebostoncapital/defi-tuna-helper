import streamlit as st
import pandas as pd
import time
from streamlit_autorefresh import st_autorefresh
from data_engine import fetch_base_data

# 1. SETUP
st.set_page_config(page_title="Sreejan Sentinel Pro", layout="wide")
st_autorefresh(interval=6000, key="global_pulse") # Slower refresh to stop API bans

# 2. THE LOCK (Memory that never clears)
tfs = ["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d"]

if 'memory_matrix' not in st.session_state:
    st.session_state.memory_matrix = {t: {"sig": "SYNCING", "clr": "#555", "val": 0} for t in tfs}
if 'memory_bias' not in st.session_state:
    st.session_state.memory_bias = {"bias": "CALCULATING", "lev": "WAITING", "conf": 0, "clr": "#444"}

# 3. CORE LOGIC ENGINE
l_votes, s_votes = 0, 0
active_this_round = 0

for t in tfs:
    df, _, _, ok = fetch_base_data(t)
    
    if ok and not df.empty:
        # Strict Rule: Price > EMA 20 AND Price > SMA 200
        p, e, s = df['close'].iloc[-1], df['20_ema'].iloc[-1], df['200_sma'].iloc[-1]
        
        if p > s and p > e:
            st.session_state.memory_matrix[t] = {"sig": "🟢 LONG", "clr": "#0ff0", "val": 1}
        elif p < s and p < e:
            st.session_state.memory_matrix[t] = {"sig": "🔴 SHORT", "clr": "#f44", "val": -1}
        else:
            st.session_state.memory_matrix[t] = {"sig": "🟡 WAIT", "clr": "#f1c40f", "val": 0}
        active_this_round += 1
    # If fetch fails (grey boxes), we DO NOT update memory. We keep the last green/red state.

# Calculate Votes from Memory (This ensures 15m/30m always count)
for t in tfs:
    v = st.session_state.memory_matrix[t]['val']
    if v == 1: l_votes += 1
    elif v == -1: s_votes += 1

conf = max(l_votes, s_votes)

# 4. GLOBAL BIAS RULES
if conf >= 4:
    side = "GO LONG" if l_votes >= s_votes else "GO SHORT"
    lev_map = {4: "2x", 5: "3x", 6: "4x", 7: "5x", 8: "5x"}
    st.session_state.memory_bias = {
        "bias": side, "lev": f"USE {lev_map.get(conf, '2x')} LEVERAGE",
        "conf": conf, "clr": "#0ff0" if "LONG" in side else "#f44"
    }
else:
    st.session_state.memory_bias = {"bias": "NEUTRAL", "lev": "WAIT FOR TREND", "conf": conf, "clr": "#888"}

# 5. UI RENDER
df_h, btc_p, _, _ = fetch_base_data("1h")
sol_p = df_h['close'].iloc[-1] if df_h is not None else 0

c1, c2 = st.columns(2)
c1.markdown(f"<h1 style='text-align:center; font-size:65px;'>SOL: ${sol_p:,.2f}</h1>", unsafe_allow_html=True)
c2.markdown(f"<h1 style='text-align:center; font-size:65px;'>BTC: ${btc_p:,.2f}</h1>", unsafe_allow_html=True)

# THE MATRIX (Guaranteed No Blanks)
st.write("### 🏛️ Consensus Judge Matrix")
cols = st.columns(8)
for i, t in enumerate(tfs):
    item = st.session_state.memory_matrix[t]
    cols[i].markdown(
        f"""<div style="border:2px solid {item['clr']}; border-radius:10px; padding:15px; text-align:center; background: rgba(0,0,0,0.4); min-height:90px;">
            <b style="color:white; font-size:16px;">{t}</b><br>
            <span style="color:{item['clr']}; font-weight:bold;">{item['sig']}</span>
        </div>""", unsafe_allow_html=True
    )

# THE SIGNAL BOX
mb = st.session_state.memory_bias
st.markdown("---")
st.markdown(
    f"""
    <div style="background-color: #161a1e; border: 5px solid {mb['clr']}; border-radius: 20px; padding: 60px; text-align: center;">
        <p style="color:#888; font-size:20px; letter-spacing:3px;">SREEJAN INTELLIGENCE CONSENSUS</p>
        <h1 style="color: white; font-size: 90px; margin: 15px 0; font-weight: 900;">GLOBAL BIAS: <span style="color: {mb['clr']};">{mb['bias']}</span></h1>
        <h2 style="color: {mb['clr']}; font-size: 55px;">{mb['lev']}</h2>
        <p style="color: #666; font-size: 18px; margin-top: 30px;">
            Confidence: {mb['conf']}/8 Judges | Logic: Verified EMA 20 + SMA 200
        </p>
    </div>
    """, unsafe_allow_html=True
)
