import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time, asyncio
from streamlit_autorefresh import st_autorefresh
from data_engine import fetch_base_data

# 1. CORE IMPORTS WITH SAFETY GUARD
# This prevents the "Oh No" screen if the server struggles with the library
try:
    from solders.keypair import Keypair
    from driftpy.drift_client import DriftClient
    from driftpy.constants.numeric_constants import BASE_PRECISION
    from driftpy.types import OrderType, PositionDirection, OrderParams
    from anchorpy import Wallet, Provider
    from solana.rpc.async_api import AsyncClient
    SDK_READY = True
except Exception as e:
    SDK_READY = False
    SDK_ERROR = str(e)

# 2. UI SETUP
st.set_page_config(page_title="Sreejan Sentinel Pro", layout="wide")
st_autorefresh(interval=1000, key="ui_pulse")

# 3. HEADER DATA (BTC & SOL PRICE RESTORED)
df, btc_p, err, status = fetch_base_data("1h")

if status:
    sol_p = df['close'].iloc[-1]
    
    # Top Bar Metrics
    col_a, col_b, col_c = st.columns([2, 2, 4])
    col_a.metric("🪙 SOLANA", f"${sol_p:,.2f}")
    col_b.metric("₿ BITCOIN", f"${btc_p:,.2f}")
    
    # 4. SIDEBAR SETTINGS
    with st.sidebar:
        st.header("🔐 Drift Execution")
        if not SDK_READY:
            st.error(f"⚠️ SDK Status: Error Loading Libraries")
            st.info(f"Details: {SDK_ERROR}")
        else:
            st.success("✅ SDK Status: Ready")
            
        rpc_url = st.text_input("Solana RPC", value="https://api.mainnet-beta.solana.com")
        pk_base58 = st.text_input("Private Key", type="password")
        total_cap = st.number_input("Margin ($)", value=1000.0)
        auto_pilot = st.toggle("🚀 AUTO-PILOT")

    # 5. 8-JUDGE CONSENSUS MATRIX (RESTORED)
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
            
            # FIXED: Corrected parameter name
            mcols[i].markdown(
                f"<div style='border:1px solid {clr}; border-radius:5px; padding:10px; "
                f"background-color:{bg}; text-align:center;'><b>{t}</b><br>"
                f"<span style='color:{clr}'>{sig}</span></div>", 
                unsafe_allow_html=True
            )

    # 6. CONSOLIDATED CONSENSUS BOX (RESTORED & DETAILED)
    st.markdown("---")
    tr_count = max(tr_longs, tr_shorts)
    final_dir = "LONG" if tr_longs >= tr_shorts else "SHORT"
    lev_map = {4: 2, 5: 3, 6: 4, 7: 5, 8: 5}
    cur_lev = lev_map.get(tr_count, 0) if tr_count >= 4 else 0
    
    con_clr = "#0ff0" if final_dir == "LONG" and cur_lev > 0 else "#f44" if cur_lev > 0 else "#888"
    
    st.markdown(
        f"<div style='border:2px solid {con_clr}; border-radius:10px; padding:20px; background-color:rgba(0,0,0,0.3); text-align:center;'>"
        f"<h2>GLOBAL CONSENSUS: <span style='color:{con_clr}'>{final_dir if cur_lev > 0 else 'NEUTRAL'}</span></h2>"
        f"<h4>Confidence: {tr_count}/8 Judges | Recommended Leverage: {cur_lev}x</h4>"
        f"</div>", unsafe_allow_html=True
    )

    # 7. CHART
    fig = go.Figure(data=[go.Candlestick(x=df['date'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="SOL")])
    fig.add_trace(go.Scatter(x=df['date'], y=df['20_ema'], name="20 EMA", line=dict(color="#854CE6")))
    fig.add_trace(go.Scatter(x=df['date'], y=df['200_sma'], name="200 SMA", line=dict(color="#FF9900", dash='dot')))
    fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig, use_container_width=True)

    # 8. DRIFT EXECUTION (RESTORED)
    async def run_drift_action(side, leverage):
        if not pk_base58 or not SDK_READY: return None
        try:
            async_client = AsyncClient(rpc_url)
            kp = Keypair.from_base58_string(pk_base58)
            wallet = Wallet(kp)
            provider = Provider(async_client, wallet)
            client = DriftClient(provider.connection, provider.wallet, account_subscription="polling")
            await client.subscribe()
            
            sol_qty = int(((total_cap * 0.05 * leverage) / sol_p) * BASE_PRECISION)
            direction = PositionDirection.Long() if side == "LONG" else PositionDirection.Short()
            params = OrderParams(order_type=OrderType.Market(), market_index=0, direction=direction, base_asset_amount=sol_qty)
            
            sig = await client.place_perp_order(params)
            await client.unsubscribe(); await async_client.close()
            return sig
        except Exception as e:
            st.error(f"Execution Error: {e}"); return None

    # 9. ACTION BUTTONS
    st.markdown("---")
    ec1, ec2, ec3 = st.columns(3)
    if ec1.button(f"🚀 Open Drift LONG ({cur_lev}x)", use_container_width=True):
        if SDK_READY: asyncio.run(run_drift_action("LONG", cur_lev))
    if ec2.button(f"🔻 Open Drift SHORT ({cur_lev}x)", use_container_width=True):
        if SDK_READY: asyncio.run(run_drift_action("SHORT", cur_lev))
    ec3.button("🔴 EMERGENCY EXIT", use_container_width=True)

else:
    st.warning("Fetching real-time market data... Please wait.")
