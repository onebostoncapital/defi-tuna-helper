import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
from streamlit_autorefresh import st_autorefresh
from data_engine import fetch_base_data

# 1. SETUP & PULSE
st.set_page_config(page_title="Sreejan Sentinel Pro", layout="wide")
st_autorefresh(interval=5000, key="global_sync_pulse") # 5s is more stable for API limits

# 2. INITIALIZE PERSISTENT CACHE (Prevents Blanks)
tfs = ["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d"]

if 'master_matrix' not in st.session_state:
    st.session_state.master_matrix = [{"tf": t, "sig": "SYNCING", "clr": "#555"} for t in tfs]
if 'master_signal' not in st.session_state:
    st.session_state.master_signal = {"bias": "ANALYZING", "lev": "WAITING", "conf": 0, "clr": "#444"}
if 'last_sync' not in st.session_state: 
    st.session_state.last_sync = 0

# 3. ATOMIC BACKGROUND ENGINE
# Only run the heavy fetch if 60 seconds have passed
if (time.time() - st.session_state.last_sync) > 60:
    temp_results = []
    l_votes, s_votes = 0, 0
    
    # Hidden loop: collects ALL data before touching the screen
    for t in tfs:
        df, _, _, ok = fetch_base_data(t)
        if ok and not df.empty:
            p, e, s = df['close'].iloc[-1], df['20_ema'].iloc[-1], df['200_sma'].iloc[-1]
            if p > s and p > e:
                temp_results.append({"tf": t, "sig": "🟢 LONG", "clr": "#0ff0"})
                l_votes += 1
            elif p < s and p < e:
                temp_results.append({"tf": t, "sig": "🔴 SHORT", "clr": "#f44"})
                s_votes += 1
            else:
                temp_results.append({"tf": t, "sig": "🟡 WAIT", "clr": "#f1c40f"})
        else:
            temp_results.append({"tf": t, "sig": "⚪ SYNC", "clr": "#555"})

    # ATOMIC SWAP: Only update if all 8 judges are processed
    if len(temp_results) == 8:
        st.session_state.master_matrix = temp_results
        conf = max(l_votes, s_votes)
        if conf >= 4:
            side = "GO LONG" if l_votes >= s_votes else "GO SHORT"
            lev_map = {4: "2x", 5: "3x", 6: "4x", 7: "5x", 8: "5x"}
            st.session_state.master_signal = {
                "bias": side, "lev": f"USE {lev_map.get(conf, '2x')} LEVERAGE",
                "conf": conf, "clr": "#0ff0" if "LONG" in side else "#f44"
            }
        else:
            st.session_state.master_signal = {"bias": "NEUTRAL", "lev": "WAIT FOR CONSENSUS", "conf": conf, "clr": "#555"}
        st.session_state.last_sync = time.time()

# 4. UI: RENDER HEADERS
df_h, btc_p, _, _ = fetch_base_data("1h")
sol_p = df_h['close'].iloc[-1] if df_h is not None else 0
c1, c2 = st.columns(2)
c1.markdown(f"<h1 style='text-align:center; font-size:60px;'>SOL: ${sol_p:,.2f}</h1>", unsafe_allow_html=True)
c2.markdown(f"<h1 style='text-align:center; font-size:60px;'>BTC: ${btc_p:,.2f}</h1>", unsafe_allow_html=True)

# 5. UI: RENDER MATRIX (Uses Locked State)
st.write("### 🏛️ Consensus Judge Matrix")
cols = st.columns(8)
for i, item in enumerate(st.session_state.master_matrix):
    cols[i].markdown(
        f"""<div style="border:2px solid {item['clr']}; border-radius:10px; padding:15px; text-align:center; background: rgba(0,0,0,0.4);">
            <b style="font-size:18px;">{item['tf']}</b><br>
            <span style="color:{item['clr']}; font-weight:bold;">{item['sig']}</span>
        </div>""", unsafe_allow_html=True
    )

# 6. UI: RENDER GLOBAL BIAS
ms = st.session_state.master_signal
rem = max(0, int(60 - (time.time() - st.session_state.last_sync)))
st.markdown("---")
st.markdown(
    f"""
    <div style="background-color: #161a1e; border: 5px solid {ms['clr']}; border-radius: 20px; padding: 50px; text-align: center;">
        <h1 style="color: white; font-size: 80px; margin-bottom: 0;">GLOBAL BIAS: <span style="color: {ms['clr']};">{ms['bias']}</span></h1>
        <h2 style="color: {ms['clr']}; font-size: 50px; margin-top: 10px;">{ms['lev']}</h2>
        <p style="color: #666; font-size: 16px;">Confidence: {ms['conf']}/8 Judges | Next Sync: {rem}s</p>
    </div>
    """, unsafe_allow_html=True
)
