import streamlit as st
from streamlit_autorefresh import st_autorefresh
from data_engine import fetch_base_data

# 1. PERMANENT UI CONFIG
st.set_page_config(page_title="Sreejan Sentinel Pro", layout="wide")
st_autorefresh(interval=10000, key="master_sync") # 10s refresh for stability

# 2. THE VAULT (Prevents the "Disappearing Box" bug)
tfs = ["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d"]

if 'vault' not in st.session_state:
    st.session_state.vault = {t: {"sig": "INITIALIZING", "clr": "#555", "vote": 0} for t in tfs}
if 'bias_vault' not in st.session_state:
    st.session_state.bias_vault = {"bias": "SYNCING", "lev": "WAIT", "conf": 0, "clr": "#444"}

# 3. BACKGROUND PROCESSING (No UI interaction here)
live_count = 0
for t in tfs:
    df, _, _, ok = fetch_base_data(t)
    if ok and df is not None:
        p, e, s = df['close'].iloc[-1], df['20_ema'].iloc[-1], df['200_sma'].iloc[-1]
        
        if p > s and p > e:
            st.session_state.vault[t] = {"sig": "🟢 LONG", "clr": "#0ff0", "vote": 1}
        elif p < s and p < e:
            st.session_state.vault[t] = {"sig": "🔴 SHORT", "clr": "#f44", "vote": -1}
        else:
            st.session_state.vault[t] = {"sig": "🟡 WAIT", "clr": "#f1c40f", "vote": 0}
        live_count += 1

# 4. GLOBAL CALCULATIONS
l_votes = sum(1 for v in st.session_state.vault.values() if v['vote'] == 1)
s_votes = sum(1 for v in st.session_state.vault.values() if v['vote'] == -1)
total_conf = max(l_votes, s_votes)

if total_conf >= 4:
    side = "GO LONG" if l_votes >= s_votes else "GO SHORT"
    lev_map = {4: "2x", 5: "3x", 6: "4x", 7: "5x", 8: "5x"}
    st.session_state.bias_vault = {
        "bias": side, "lev": f"USE {lev_map.get(total_conf, '2x')} LEVERAGE",
        "conf": total_conf, "clr": "#0ff0" if "LONG" in side else "#f44"
    }
else:
    st.session_state.bias_vault = {"bias": "NEUTRAL", "lev": "WAIT FOR TREND", "conf": total_conf, "clr": "#888"}

# 5. UI RENDERING (Fixed Grid)
df_h, btc_p, _, _ = fetch_base_data("1h")
sol_p = df_h['close'].iloc[-1] if df_h is not None else 0

st.markdown(f"<div style='display:flex; justify-content:space-around;'><h1>SOL: ${sol_p:,.2f}</h1><h1>BTC: ${btc_p:,.2f}</h1></div>", unsafe_allow_html=True)

st.write("### 🏛️ Consensus Judge Matrix")
cols = st.columns(8)
for i, t in enumerate(tfs):
    item = st.session_state.vault[t]
    # 'min-height' and 'display:block' prevent boxes from disappearing
    cols[i].markdown(
        f"""<div style="border:2px solid {item['clr']}; border-radius:10px; padding:15px; text-align:center; background: rgba(255,255,255,0.05); min-height:100px; display:block;">
            <b style="color:white; font-size:16px;">{t}</b><br>
            <span style="color:{item['clr']}; font-weight:bold;">{item['sig']}</span>
        </div>""", unsafe_allow_html=True
    )

# 6. MASTER BIAS BOX
vb = st.session_state.bias_vault
st.markdown("---")
st.markdown(
    f"""
    <div style="background-color: #161a1e; border: 5px solid {vb['clr']}; border-radius: 20px; padding: 60px; text-align: center;">
        <p style="color:#888; font-size:18px; letter-spacing:2px;">SREEJAN INTELLIGENCE CONSENSUS</p>
        <h1 style="color: white; font-size: 85px; margin: 15px 0; font-weight: 900;">
            GLOBAL BIAS: <span style="color: {vb['clr']};">{vb['bias']}</span>
        </h1>
        <h2 style="color: {vb['clr']}; font-size: 50px;">{vb['lev']}</h2>
        <p style="color: #666; font-size: 16px;">Verified Judges: {vb['conf']}/8 | Engine Status: {live_count}/8 Active</p>
    </div>
    """, unsafe_allow_html=True
)
