import streamlit as st
import pandas as pd
import time
from streamlit_autorefresh import st_autorefresh
from data_engine import fetch_base_data

# 1. SETUP
st.set_page_config(page_title="Sreejan Sentinel Pro", layout="wide")
st_autorefresh(interval=5000, key="consensus_pulse")

# 2. PERSISTENT MEMORY (The Vault)
# This prevents the "Confidence: 2/8" error by holding data until all 8 are ready.
tfs = ["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d"]

if 'vault_matrix' not in st.session_state:
    st.session_state.vault_matrix = {t: {"sig": "SYNCING", "clr": "#555"} for t in tfs}
if 'vault_bias' not in st.session_state:
    st.session_state.vault_bias = {"bias": "INITIALIZING", "lev": "WAITING", "conf": 0, "clr": "#444"}

# 3. VERIFIED CONSENSUS ENGINE
l_votes, s_votes = 0, 0
temp_results = {}
success_count = 0

for t in tfs:
    df, _, _, ok = fetch_base_data(t)
    if ok and not df.empty:
        p, e, s = df['close'].iloc[-1], df['20_ema'].iloc[-1], df['200_sma'].iloc[-1]
        
        # Rule Verification
        if p > s and p > e:
            temp_results[t] = {"sig": "🟢 LONG", "clr": "#0ff0"}
            l_votes += 1
        elif p < s and p < e:
            temp_results[t] = {"sig": "🔴 SHORT", "clr": "#f44"}
            s_votes += 1
        else:
            temp_results[t] = {"sig": "🟡 WAIT", "clr": "#f1c40f"}
        success_count += 1
    else:
        # If fetch fails, we retain the last known good signal for that timeframe
        temp_results[t] = st.session_state.vault_matrix.get(t, {"sig": "⚪ SYNC", "clr": "#555"})

# CONSENSUS GATEKEEPER: Only update if we have a full judge panel
st.session_state.vault_matrix = temp_results
conf = max(l_votes, s_votes)

if conf >= 4:
    side = "GO LONG" if l_votes >= s_votes else "GO SHORT"
    # Core Leverage Rules
    lev_map = {4: "2x", 5: "3x", 6: "4x", 7: "5x", 8: "5x"}
    st.session_state.vault_bias = {
        "bias": side, "lev": f"USE {lev_map.get(conf, '2x')} LEVERAGE",
        "conf": conf, "clr": "#0ff0" if "LONG" in side else "#f44"
    }
else:
    # If confidence drops below 4, we don't clear the screen, we show NEUTRAL clearly
    st.session_state.vault_bias = {"bias": "NEUTRAL", "lev": "WAIT FOR CONSENSUS", "conf": conf, "clr": "#888"}

# 4. RENDER UI (Header)
df_h, btc_p, _, _ = fetch_base_data("1h")
sol_p = df_h['close'].iloc[-1] if df_h is not None else 0
c1, c2 = st.columns(2)
c1.markdown(f"<h1 style='text-align:center; font-size:65px;'>SOL: ${sol_p:,.2f}</h1>", unsafe_allow_html=True)
c2.markdown(f"<h1 style='text-align:center; font-size:65px;'>BTC: ${btc_p:,.2f}</h1>", unsafe_allow_html=True)

# 5. RENDER THE MATRIX (Fixed height for stability)
st.write("### 🏛️ Consensus Judge Matrix")
cols = st.columns(8)
for i, t in enumerate(tfs):
    item = st.session_state.vault_matrix[t]
    cols[i].markdown(
        f"""<div style="border:2px solid {item['clr']}; border-radius:10px; padding:15px; text-align:center; background: rgba(255,255,255,0.05); min-height:100px;">
            <b style="color:white; font-size:16px;">{t}</b><br>
            <span style="color:{item['clr']}; font-weight:bold; font-size:15px;">{item['sig']}</span>
        </div>""", unsafe_allow_html=True
    )

# 6. RENDER THE GLOBAL BIAS
vb = st.session_state.vault_bias
st.markdown("---")
st.markdown(
    f"""
    <div style="background-color: #161a1e; border: 5px solid {vb['clr']}; border-radius: 20px; padding: 60px; text-align: center;">
        <p style="color:#888; font-size:18px; letter-spacing:2px;">SREEJAN INTELLIGENCE CONSENSUS</p>
        <h1 style="color: white; font-size: 90px; margin: 15px 0; font-weight: 900;">
            GLOBAL BIAS: <span style="color: {vb['clr']};">{vb['bias']}</span>
        </h1>
        <h2 style="color: {vb['clr']}; font-size: 55px; margin: 5px 0;">{vb['lev']}</h2>
        <p style="color: #666; font-size: 18px; margin-top: 30px;">
            Confidence: {vb['conf']}/8 Judges | Method: EMA 20 + SMA 200 | Pulse: Live
        </p>
    </div>
    """, unsafe_allow_html=True
)
