import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from data_engine import fetch_base_data

# 1. INITIAL SETUP
st.set_page_config(page_title="Sreejan Sentinel Pro", layout="wide")
st_autorefresh(interval=5000, key="global_sync")

# 2. THE DATA VAULT (Prevents Blanks)
tfs = ["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d"]

if 'vault' not in st.session_state:
    st.session_state.vault = {t: {"sig": "SYNCING", "clr": "#555", "vote": 0} for t in tfs}
if 'bias_vault' not in st.session_state:
    st.session_state.bias_vault = {"bias": "ANALYZING", "lev": "SYNCING", "conf": 0, "clr": "#444"}

# 3. SYNCHRONOUS VALIDATION ENGINE
l_votes, s_votes = 0, 0
successful_this_round = 0

for t in tfs:
    df, btc_p, _, ok = fetch_base_data(t)
    
    if ok and not df.empty:
        p, e, s = df['close'].iloc[-1], df['20_ema'].iloc[-1], df['200_sma'].iloc[-1]
        
        # Apply Rules
        if p > s and p > e:
            st.session_state.vault[t] = {"sig": "🟢 LONG", "clr": "#0ff0", "vote": 1}
        elif p < s and p < e:
            st.session_state.vault[t] = {"sig": "🔴 SHORT", "clr": "#f44", "vote": -1}
        else:
            st.session_state.vault[t] = {"sig": "🟡 WAIT", "clr": "#f1c40f", "vote": 0}
        successful_this_round += 1
    # If fetch fails, the vault retains the last good state (No blank holes)

# 4. FINAL CONSENSUS CALCULATION
for t in tfs:
    v = st.session_state.vault[t]['vote']
    if v == 1: l_votes += 1
    elif v == -1: s_votes += 1

conf = max(l_votes, s_votes)

if conf >= 4:
    side = "GO LONG" if l_votes >= s_votes else "GO SHORT"
    lev_map = {4: "2x", 5: "3x", 6: "4x", 7: "5x", 8: "5x"}
    st.session_state.bias_vault = {
        "bias": side, "lev": f"USE {lev_map.get(conf, '2x')} LEVERAGE",
        "conf": conf, "clr": "#0ff0" if "LONG" in side else "#f44"
    }
else:
    st.session_state.bias_vault = {"bias": "NEUTRAL", "lev": "WAIT FOR TREND", "conf": conf, "clr": "#888"}

# 5. UI RENDER
df_h, btc_p, _, _ = fetch_base_data("1h")
sol_p = df_h['close'].iloc[-1] if df_h is not None else 0

c1, c2 = st.columns(2)
c1.markdown(f"<h1 style='text-align:center; font-size:60px;'>SOL: ${sol_p:,.2f}</h1>", unsafe_allow_html=True)
c2.markdown(f"<h1 style='text-align:center; font-size:60px;'>BTC: ${btc_p:,.2f}</h1>", unsafe_allow_html=True)

st.write("### 🏛️ Consensus Judge Matrix")
cols = st.columns(8)
for i, t in enumerate(tfs):
    item = st.session_state.vault[t]
    cols[i].markdown(
        f"""<div style="border:2px solid {item['clr']}; border-radius:10px; padding:15px; text-align:center; background: rgba(0,0,0,0.3); min-height:85px;">
            <b style="color:white; font-size:16px;">{t}</b><br>
            <span style="color:{item['clr']}; font-weight:bold;">{item['sig']}</span>
        </div>""", unsafe_allow_html=True
    )

bv = st.session_state.bias_vault
st.markdown("---")
st.markdown(
    f"""
    <div style="background-color: #161a1e; border: 5px solid {bv['clr']}; border-radius: 20px; padding: 60px; text-align: center;">
        <p style="color:#888; font-size:18px; letter-spacing:2px;">SREEJAN INTELLIGENCE CONSENSUS</p>
        <h1 style="color: white; font-size: 80px; margin: 15px 0;">GLOBAL BIAS: <span style="color: {bv['clr']};">{bv['bias']}</span></h1>
        <h2 style="color: {bv['clr']}; font-size: 50px;">{bv['lev']}</h2>
        <p style="color: #666; font-size: 16px;">Confidence: {bv['conf']}/8 Judges | Logic: EMA 20 + SMA 200 | Pulse: {successful_this_round}/8 Live</p>
    </div>
    """, unsafe_allow_html=True
)
