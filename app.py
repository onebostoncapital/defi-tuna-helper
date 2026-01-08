import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
from streamlit_autorefresh import st_autorefresh
from data_engine import fetch_base_data

# 1. SETUP & PULSE
st.set_page_config(page_title="Sreejan Sentinel Pro", layout="wide")
st_autorefresh(interval=3000, key="global_pulse")

# 2. THE VAULT (Persistent Storage)
# We use st.session_state to "remember" data so boxes NEVER go blank.
tfs = ["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d"]

if 'vault_matrix' not in st.session_state:
    st.session_state.vault_matrix = {t: {"sig": "SYNCING", "clr": "#555"} for t in tfs}
if 'vault_signal' not in st.session_state:
    st.session_state.vault_signal = {"bias": "ANALYZING", "lev": "WAITING", "conf": 0, "clr": "#444"}
if 'last_sync_ts' not in st.session_state:
    st.session_state.last_sync_ts = 0

# 3. BACKGROUND CALCULATION ENGINE
now = time.time()
# Only recalculate every 60 seconds to prevent "Rate Limit" errors and blanks
if (now - st.session_state.last_sync_ts) > 60:
    l_votes, s_votes = 0, 0
    updated_matrix = {}
    
    for t in tfs:
        df, _, _, ok = fetch_base_data(t)
        if ok and not df.empty:
            p, e, s = df['close'].iloc[-1], df['20_ema'].iloc[-1], df['200_sma'].iloc[-1]
            if p > s and p > e:
                updated_matrix[t] = {"sig": "🟢 LONG", "clr": "#0ff0"}
                l_votes += 1
            elif p < s and p < e:
                updated_matrix[t] = {"sig": "🔴 SHORT", "clr": "#f44"}
                s_votes += 1
            else:
                updated_matrix[t] = {"sig": "🟡 WAIT", "clr": "#f1c40f"}
        else:
            # If fetch fails, keep the OLD data instead of showing a blank
            updated_matrix[t] = st.session_state.vault_matrix.get(t, {"sig": "⚪ SYNC", "clr": "#555"})

    # ATOMIC UPDATE: Apply everything at once
    st.session_state.vault_matrix = updated_matrix
    conf = max(l_votes, s_votes)
    
    if conf >= 4:
        side = "GO LONG" if l_votes >= s_votes else "GO SHORT"
        lev_map = {4: "2x", 5: "3x", 6: "4x", 7: "5x", 8: "5x"}
        st.session_state.vault_signal = {
            "bias": side, "lev": f"USE {lev_map.get(conf, '2x')} LEVERAGE",
            "conf": conf, "clr": "#0ff0" if "LONG" in side else "#f44"
        }
    else:
        st.session_state.vault_signal = {"bias": "NEUTRAL", "lev": "WAIT FOR CONSENSUS", "conf": conf, "clr": "#555"}
    
    st.session_state.last_sync_ts = now

# 4. RENDER UI
df_h, btc_p, _, _ = fetch_base_data("1h")
sol_p = df_h['close'].iloc[-1] if df_h is not None else 0
c1, c2 = st.columns(2)
c1.markdown(f"<h1 style='text-align:center; font-size:60px;'>SOL: ${sol_p:,.2f}</h1>", unsafe_allow_html=True)
c2.markdown(f"<h1 style='text-align:center; font-size:65px;'>BTC: ${btc_p:,.2f}</h1>", unsafe_allow_html=True)

# 5. RENDER THE MATRIX (Fixed height to prevent jumping)
st.write("### 🏛️ Consensus Judge Matrix")
cols = st.columns(8)
for i, t in enumerate(tfs):
    item = st.session_state.vault_matrix[t]
    cols[i].markdown(
        f"""<div style="border:2px solid {item['clr']}; border-radius:10px; padding:15px; text-align:center; background: rgba(0,0,0,0.3); min-height:85px;">
            <b style="color:white; font-size:16px;">{t}</b><br>
            <span style="color:{item['clr']}; font-weight:bold;">{item['sig']}</span>
        </div>""", unsafe_allow_html=True
    )

# 6. RENDER THE GLOBAL BIAS
vs = st.session_state.vault_signal
rem = max(0, int(60 - (time.time() - st.session_state.last_sync_ts)))
st.markdown("---")
st.markdown(
    f"""
    <div style="background-color: #161a1e; border: 5px solid {vs['clr']}; border-radius: 20px; padding: 55px; text-align: center;">
        <p style="color:#888; font-size:18px; letter-spacing:2px;">SREEJAN INTELLIGENCE CONSENSUS</p>
        <h1 style="color: white; font-size: 85px; margin: 10px 0;">GLOBAL BIAS: <span style="color: {vs['clr']};">{vs['bias']}</span></h1>
        <h2 style="color: {vs['clr']}; font-size: 55px;">{vs['lev']}</h2>
        <p style="color: #666; font-size: 16px;">Confidence: {vs['conf']}/8 Judges | Logic: EMA 20 + SMA 200 | Sync: {rem}s</p>
    </div>
    """, unsafe_allow_html=True
)
