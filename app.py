import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
from streamlit_autorefresh import st_autorefresh
from data_engine import fetch_base_data

# 1. SETUP & STABILITY
st.set_page_config(page_title="Sreejan Sentinel Pro", layout="wide")
st_autorefresh(interval=5000, key="global_sync_pulse") # Increased to 5s to avoid API bans

# 2. THE PERSISTENCE VAULT
tfs = ["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d"]

# Initialize memory if it's the first time running
if 'history_matrix' not in st.session_state:
    st.session_state.history_matrix = {t: {"sig": "INITIALIZING", "clr": "#555"} for t in tfs}
if 'history_signal' not in st.session_state:
    st.session_state.history_signal = {"bias": "ANALYZING", "lev": "WAITING", "conf": 0, "clr": "#444"}
if 'last_full_sync' not in st.session_state:
    st.session_state.last_full_sync = 0

# 3. ROBUST CALCULATION ENGINE
now = time.time()
# Sync every 60 seconds to stay under API limits
if (now - st.session_state.last_full_sync) > 60:
    l_votes, s_votes = 0, 0
    temp_matrix = st.session_state.history_matrix.copy()
    
    for t in tfs:
        df, _, _, ok = fetch_base_data(t)
        if ok and not df.empty:
            p, e, s = df['close'].iloc[-1], df['20_ema'].iloc[-1], df['200_sma'].iloc[-1]
            if p > s and p > e:
                temp_matrix[t] = {"sig": "🟢 LONG", "clr": "#0ff0"}
                l_votes += 1
            elif p < s and p < e:
                temp_matrix[t] = {"sig": "🔴 SHORT", "clr": "#f44"}
                s_votes += 1
            else:
                temp_matrix[t] = {"sig": "🟡 WAIT", "clr": "#f1c40f"}
        # If fetch fails, we do NOT set it to blank. We keep the old data.

    # UPDATE GLOBAL STATE
    st.session_state.history_matrix = temp_matrix
    conf = max(l_votes, s_votes)
    
    if conf >= 4:
        side = "GO LONG" if l_votes >= s_votes else "GO SHORT"
        lev_map = {4: "2x", 5: "3x", 6: "4x", 7: "5x", 8: "5x"}
        st.session_state.history_signal = {
            "bias": side, "lev": f"USE {lev_map.get(conf, '2x')} LEVERAGE",
            "conf": conf, "clr": "#0ff0" if "LONG" in side else "#f44"
        }
    else:
        st.session_state.history_signal = {"bias": "NEUTRAL", "lev": "WAIT FOR CONSENSUS", "conf": conf, "clr": "#555"}
    
    st.session_state.last_full_sync = now

# 4. UI: STATS
df_h, btc_p, _, _ = fetch_base_data("1h")
sol_p = df_h['close'].iloc[-1] if df_h is not None else 0
c1, c2 = st.columns(2)
c1.markdown(f"<h1 style='text-align:center; font-size:60px;'>SOL: ${sol_p:,.2f}</h1>", unsafe_allow_html=True)
c2.markdown(f"<h1 style='text-align:center; font-size:60px;'>BTC: ${btc_p:,.2f}</h1>", unsafe_allow_html=True)

# 5. UI: MATRIX (Locked Height to stop flickering)
st.write("### 🏛️ Consensus Judge Matrix")
cols = st.columns(8)
for i, t in enumerate(tfs):
    item = st.session_state.history_matrix[t]
    cols[i].markdown(
        f"""<div style="border:2px solid {item['clr']}; border-radius:10px; padding:15px; text-align:center; background: rgba(255,255,255,0.05); min-height:90px;">
            <b style="font-size:16px; color:white;">{t}</b><br>
            <span style="color:{item['clr']}; font-weight:bold; font-size:14px;">{item['sig']}</span>
        </div>""", unsafe_allow_html=True
    )

# 6. UI: GLOBAL BIAS
hs = st.session_state.history_signal
rem = max(0, int(60 - (time.time() - st.session_state.last_full_sync)))
st.markdown("---")
st.markdown(
    f"""
    <div style="background-color: #161a1e; border: 5px solid {hs['clr']}; border-radius: 20px; padding: 50px; text-align: center;">
        <p style="color:#888; font-size:18px; letter-spacing:2px;">SREEJAN INTELLIGENCE CONSENSUS</p>
        <h1 style="color: white; font-size: 85px; margin: 10px 0; font-weight: 900;">
            GLOBAL BIAS: <span style="color: {hs['clr']};">{hs['bias']}</span>
        </h1>
        <h2 style="color: {hs['clr']}; font-size: 55px; margin: 5px 0;">{hs['lev']}</h2>
        <p style="color: #666; font-size: 16px; margin-top: 25px;">
            Confidence: {hs['conf']}/8 Judges | Logic: EMA 20 + SMA 200 | Next Sync: {rem}s
        </p>
    </div>
    """, unsafe_allow_html=True
)
