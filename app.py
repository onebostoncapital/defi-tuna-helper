import streamlit as st
import pandas as pd
import time
from streamlit_autorefresh import st_autorefresh
from data_engine import fetch_base_data

# 1. SETUP
st.set_page_config(page_title="Sreejan Sentinel Pro", layout="wide")
st_autorefresh(interval=5000, key="consensus_pulse")

# 2. PERMANENT DATA VAULT
tfs = ["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d"]

# Initialize memory so we never start with empty boxes
if 'final_matrix' not in st.session_state:
    st.session_state.final_matrix = {t: {"sig": "SYNCING", "clr": "#555", "vote": 0} for t in tfs}
if 'final_bias' not in st.session_state:
    st.session_state.final_bias = {"bias": "INITIALIZING", "lev": "WAITING", "conf": 0, "clr": "#444"}

# 3. SYNCHRONOUS ENGINE
l_votes, s_votes = 0, 0
successful_fetches = 0

for t in tfs:
    df, _, _, ok = fetch_base_data(t)
    
    if ok and df is not None and not df.empty:
        # Core Rule Implementation
        p, e, s = df['close'].iloc[-1], df['20_ema'].iloc[-1], df['200_sma'].iloc[-1]
        
        if p > s and p > e:
            st.session_state.final_matrix[t] = {"sig": "🟢 LONG", "clr": "#0ff0", "vote": 1}
        elif p < s and p < e:
            st.session_state.final_matrix[t] = {"sig": "🔴 SHORT", "clr": "#f44", "vote": -1}
        else:
            st.session_state.final_matrix[t] = {"sig": "🟡 WAIT", "clr": "#f1c40f", "vote": 0}
        successful_fetches += 1
    # If fetch fails (the grey box error), we KEEP the old data. We do NOT let it go blank.

# 4. GLOBAL BIAS CALCULATION (From populated memory only)
for t in tfs:
    v = st.session_state.final_matrix[t]['vote']
    if v == 1: l_votes += 1
    elif v == -1: s_votes += 1

conf = max(l_votes, s_votes)

# Confidence Rule: Only trigger if 4+ judges agree
if conf >= 4:
    side = "GO LONG" if l_votes >= s_votes else "GO SHORT"
    lev_map = {4: "2x", 5: "3x", 6: "4x", 7: "5x", 8: "5x"}
    st.session_state.final_bias = {
        "bias": side, "lev": f"USE {lev_map.get(conf, '2x')} LEVERAGE",
        "conf": conf, "clr": "#0ff0" if "LONG" in side else "#f44"
    }
else:
    st.session_state.final_bias = {"bias": "NEUTRAL", "lev": "WAIT FOR TREND", "conf": conf, "clr": "#888"}

# 5. UI RENDER (SOL & BTC)
df_h, btc_p, _, _ = fetch_base_data("1h")
sol_p = df_h['close'].iloc[-1] if df_h is not None else 0
c1, c2 = st.columns(2)
c1.markdown(f"<h1 style='text-align:center; font-size:65px;'>SOL: ${sol_p:,.2f}</h1>", unsafe_allow_html=True)
c2.markdown(f"<h1 style='text-align:center; font-size:65px;'>BTC: ${btc_p:,.2f}</h1>", unsafe_allow_html=True)

# 6. UI: THE MATRIX (Guaranteed 8 Columns)
st.write("### 🏛️ Consensus Judge Matrix")
cols = st.columns(8)
for i, t in enumerate(tfs):
    item = st.session_state.final_matrix[t]
    cols[i].markdown(
        f"""<div style="border:2px solid {item['clr']}; border-radius:10px; padding:15px; text-align:center; background: rgba(255,255,255,0.05); min-height:100px;">
            <b style="color:white; font-size:18px;">{t}</b><br>
            <span style="color:{item['clr']}; font-weight:bold; font-size:16px;">{item['sig']}</span>
        </div>""", unsafe_allow_html=True
    )

# 7. UI: GLOBAL BIAS BOX
fb = st.session_state.final_bias
st.markdown("---")
st.markdown(
    f"""
    <div style="background-color: #161a1e; border: 5px solid {fb['clr']}; border-radius: 20px; padding: 60px; text-align: center;">
        <p style="color:#888; font-size:18px; letter-spacing:2px;">SREEJAN INTELLIGENCE CONSENSUS</p>
        <h1 style="color: white; font-size: 90px; margin: 15px 0; font-weight: 900;">
            GLOBAL BIAS: <span style="color: {fb['clr']};">{fb['bias']}</span>
        </h1>
        <h2 style="color: {fb['clr']}; font-size: 55px; margin: 5px 0;">{fb['lev']}</h2>
        <p style="color: #666; font-size: 18px; margin-top: 30px;">
            Confidence: {fb['conf']}/8 Judges | Logic: EMA 20 + SMA 200 | Fetched: {successful_fetches}/8
        </p>
    </div>
    """, unsafe_allow_html=True
)
