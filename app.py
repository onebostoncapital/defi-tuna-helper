import streamlit as st
from streamlit_autorefresh import st_autorefresh
from data_engine import fetch_base_data

# 1. PERMANENT PAGE SETUP
st.set_page_config(page_title="Sreejan Sentinel Pro", layout="wide")
st_autorefresh(interval=10000, key="master_sync_lock")

# 2. THE PERSISTENT VAULT (Prevents the "Neutral" trap)
tfs = ["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d"]

if 'matrix' not in st.session_state:
    st.session_state.matrix = {t: {"sig": "SYNCING", "clr": "#555", "vote": 0} for t in tfs}
if 'global_bias' not in st.session_state:
    st.session_state.global_bias = {"bias": "INITIALIZING", "lev": "WAIT", "conf": 0, "clr": "#444"}

# 3. BACKGROUND INTELLIGENCE (Atomic Update)
live_updates = 0
for t in tfs:
    df, _, _, ok = fetch_base_data(t)
    if ok and df is not None:
        p, e, s = df['close'].iloc[-1], df['20_ema'].iloc[-1], df['200_sma'].iloc[-1]
        
        # Strict logic: Above both = LONG, Below both = SHORT
        if p > s and p > e:
            st.session_state.matrix[t] = {"sig": "🟢 LONG", "clr": "#0ff0", "vote": 1}
        elif p < s and p < e:
            st.session_state.matrix[t] = {"sig": "🔴 SHORT", "clr": "#f44", "vote": -1}
        else:
            st.session_state.matrix[t] = {"sig": "🟡 WAIT", "clr": "#f1c40f", "vote": 0}
        live_updates += 1
    # If fetch fails, the box STAYS but keeps its old value. No disappearing.

# 4. CONSENSUS MATH
l_votes = sum(1 for v in st.session_state.matrix.values() if v['vote'] == 1)
s_votes = sum(1 for v in st.session_state.matrix.values() if v['vote'] == -1)
total_conf = max(l_votes, s_votes)

if total_conf >= 4:
    side = "GO LONG" if l_votes >= s_votes else "GO SHORT"
    lev_map = {4: "2x", 5: "3x", 6: "4x", 7: "5x", 8: "5x"}
    st.session_state.global_bias = {
        "bias": side, "lev": f"USE {lev_map.get(total_conf, '2x')} LEVERAGE",
        "conf": total_conf, "clr": "#0ff0" if "LONG" in side else "#f44"
    }
else:
    st.session_state.global_bias = {"bias": "NEUTRAL", "lev": "WAIT FOR TREND", "conf": total_conf, "clr": "#888"}

# 5. UI RENDERING (Fixed Grid)
df_h, btc_p, _, _ = fetch_base_data("1h")
sol_p = df_h['close'].iloc[-1] if df_h is not None else 0

st.markdown(f"<div style='display:flex; justify-content:space-around;'><h1>SOL: ${sol_p:,.2f}</h1><h1>BTC: ${btc_p:,.2f}</h1></div>", unsafe_allow_html=True)

st.write("### 🏛️ Consensus Judge Matrix")
# This creates 8 columns that are FIXED. They cannot disappear.
cols = st.columns(8)
for i, t in enumerate(tfs):
    item = st.session_state.matrix[t]
    cols[i].markdown(
        f"""<div style="border:2px solid {item['clr']}; border-radius:10px; padding:15px; text-align:center; background: rgba(255,255,255,0.05); min-height:100px;">
            <b style="color:white; font-size:16px;">{t}</b><br>
            <span style="color:{item['clr']}; font-weight:bold; font-size:15px;">{item['sig']}</span>
        </div>""", unsafe_allow_html=True
    )

# 6. SIGNAL BOX
gb = st.session_state.global_bias
st.markdown("---")
st.markdown(
    f"""
    <div style="background-color: #161a1e; border: 5px solid {gb['clr']}; border-radius: 20px; padding: 60px; text-align: center;">
        <p style="color:#888; font-size:18px; letter-spacing:2px;">SREEJAN INTELLIGENCE CONSENSUS</p>
        <h1 style="color: white; font-size: 85px; margin: 15px 0; font-weight: 900;">
            GLOBAL BIAS: <span style="color: {gb['clr']};">{gb['bias']}</span>
        </h1>
        <h2 style="color: {gb['clr']}; font-size: 50px;">{gb['lev']}</h2>
        <p style="color: #666; font-size: 16px;">Verified Judges: {gb['conf']}/8 | Sync: {live_updates}/8 Live</p>
    </div>
    """, unsafe_allow_html=True
)
