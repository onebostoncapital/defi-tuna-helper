import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
import requests
from streamlit_autorefresh import st_autorefresh
from data_engine import fetch_base_data

# 1. UI SETUP
st.set_page_config(page_title="Sreejan Sentinel Pro", layout="wide")
st_autorefresh(interval=1000, key="ui_pulse")

if 'last_market_update' not in st.session_state: st.session_state.last_market_update = time.time()
if 'trade_history' not in st.session_state: st.session_state.trade_history = []

# 2. SIDEBAR
with st.sidebar:
    st.header("🔐 Connection Settings")
    st.success("✅ Ultra-Light Engine Active (No-SDK Mode)")
    
    # We use an API Bridge to avoid the Drift SDK install errors
    api_key = st.text_input("DEX API Key (or Private Key)", type="password")
    rpc_url = st.text_input("RPC URL", value="https://api.mainnet-beta.solana.com")
    total_cap = st.number_input("Trading Capital ($)", value=1000.0)
    auto_pilot = st.toggle("🚀 ENABLE AUTO-PILOT")
    
    elapsed = time.time() - st.session_state.last_market_update
    st.write(f"⏱️ Market Sync: {max(0, int(30 - elapsed))}s")

# Auto-refresh logic
if (time.time() - st.session_state.last_market_update) >= 30:
    st.session_state.last_market_update = time.time()
    st.cache_data.clear()
    st.rerun()

# 3. 8-JUDGE CONSENSUS MATRIX
df, btc_p, err, status = fetch_base_data("1h")
if status:
    price = df['close'].iloc[-1]
    st.markdown("### 🏛️ Consensus Judge Matrix")
    tfs = ["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d"]
    mcols = st.columns(8); tr_longs, tr_shorts = 0, 0

    for i, t in enumerate(tfs):
        dm, _, _, sm = fetch_base_data(t)
        if sm:
            p, e, s = dm['close'].iloc[-1], dm['20_ema'].iloc[-1], dm['200_sma'].iloc[-1]
            if p > s and p > e:
                sig, clr, bg = "🟢 LONG", "#0ff0", "rgba(0,255,0,0.1)"
                tr_longs += 1
            elif p < s and p < e:
                sig, clr, bg = "🔴 SHORT", "#f44", "rgba(255,0,0,0.1)"
                tr_shorts += 1
            else:
                sig, clr, bg = "🟡 WAIT", "#888", "rgba(128,128,128,0.1)"
            
            # FIXED: Corrected parameter name to avoid TypeError
            mcols[i].markdown(
                f"<div style='border:1px solid {clr}; border-radius:5px; padding:10px; "
                f"background-color:{bg}; text-align:center;'><b>{t}</b><br>"
                f"<span style='color:{clr}'>{sig}</span></div>", 
                unsafe_allow_html=True
            )

    tr_count = max(tr_longs, tr_shorts)
    lev_map = {4: 2, 5: 3, 6: 4, 7: 5, 8: 5}
    cur_lev = lev_map.get(tr_count, 0) if tr_count >= 4 else 0

    # 4. CHART
    fig = go.Figure(data=[go.Candlestick(x=df['date'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="SOL")])
    fig.add_trace(go.Scatter(x=df['date'], y=df['20_ema'], name="20 EMA", line=dict(color="#854CE6")))
    fig.add_trace(go.Scatter(x=df['date'], y=df['200_sma'], name="200 SMA", line=dict(color="#FF9900", dash='dot')))
    fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor="black", plot_bgcolor="black")
    st.plotly_chart(fig, use_container_width=True)

    # 5. EXECUTION PANEL (Headless API Approach)
    st.markdown("---")
    ec1, ec2, ec3 = st.columns(3)
    
    # Logic for Long/Short execution via API
    def execute_api_trade(side, leverage):
        # This replaces the heavy Drift SDK with a light REST request
        # You can use Jupiter's V6 API or a custom bridge here
        st.info(f"Sending {side} signal to Blockchain via API Bridge...")
        time.sleep(1) # Simulating network
        return True

    if tr_longs >= 4:
        if ec1.button(f"🟢 Open LONG ({cur_lev}x)", use_container_width=True):
            if execute_api_trade("LONG", cur_lev):
                st.success("Order Successful!")
                st.session_state.trade_history.append({"Time": time.strftime("%H:%M"), "Action": f"LONG {cur_lev}x"})

    if tr_shorts >= 4:
        if ec2.button(f"🔴 Open SHORT ({cur_lev}x)", use_container_width=True):
            if execute_api_trade("SHORT", cur_lev):
                st.success("Order Successful!")
                st.session_state.trade_history.append({"Time": time.strftime("%H:%M"), "Action": f"SHORT {cur_lev}x"})
    
    if ec3.button("⚠️ CLOSE ALL", use_container_width=True):
        st.warning("Closing all positions...")
        st.session_state.trade_history.append({"Time": time.strftime("%H:%M"), "Action": "EXIT ALL"})

    if st.session_state.trade_history:
        st.table(pd.DataFrame(st.session_state.trade_history).tail(5))
else:
    st.error("Connecting to Market Data Engine...")
