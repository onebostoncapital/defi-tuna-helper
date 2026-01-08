import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time, asyncio
from streamlit_autorefresh import st_autorefresh
from data_engine import fetch_base_data

# Core Drift/Solana Imports
from solders.keypair import Keypair
from driftpy.drift_client import DriftClient
from driftpy.constants.numeric_constants import BASE_PRECISION
from driftpy.types import OrderType, PositionDirection, OrderParams
from anchorpy import Wallet, Provider
from solana.rpc.async_api import AsyncClient

# 1. UI SETUP & HEARTBEAT
st.set_page_config(page_title="Sreejan Sentinel (Drift Fix)", layout="wide")
st_autorefresh(interval=1000, key="ui_pulse")

if 'last_market_update' not in st.session_state: st.session_state.last_market_update = time.time()
if 'trade_history' not in st.session_state: st.session_state.trade_history = []

# 2. SIDEBAR
with st.sidebar:
    st.header("🔐 Drift Credentials")
    rpc_url = st.text_input("Solana RPC URL", placeholder="https://api.mainnet-beta.solana.com")
    pk_base58 = st.text_input("Private Key (Base58)", type="password")
    sub_id = st.number_input("Sub-Account ID", value=0, step=1)
    total_cap = st.number_input("Equity ($)", value=1000.0)
    auto_pilot = st.toggle("🚀 ENABLE AUTO-PILOT")
    
    elapsed = time.time() - st.session_state.last_market_update
    st.write(f"⏱️ Sync: {max(0, int(30 - elapsed))}s")

# Auto-refresh Logic
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
            
            # FIXED: Corrected parameter name to unsafe_allow_html
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
    fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig, use_container_width=True)

    # 5. PROTECTED DRIFT ENGINE
    async def run_drift_action(action_type, side=None, leverage=0):
        if not pk_base58 or not rpc_url:
            st.error("Missing Credentials! Please check sidebar.")
            return None
        try:
            async_client = AsyncClient(rpc_url)
            kp = Keypair.from_base58_string(pk_base58)
            wallet = Wallet(kp)
            provider = Provider(async_client, wallet)
            client = DriftClient(provider.connection, provider.wallet, account_subscription="polling")
            await client.subscribe()
            
            if action_type == "TRADE":
                sol_qty = int(((total_cap * 0.05 * leverage) / price) * BASE_PRECISION)
                direction = PositionDirection.Long() if side == "LONG" else PositionDirection.Short()
                params = OrderParams(order_type=OrderType.Market(), market_index=0, direction=direction, base_asset_amount=sol_qty)
            else: # CLOSE ALL
                params = OrderParams(order_type=OrderType.Market(), market_index=0, direction=PositionDirection.Long(), base_asset_amount=0, reduce_only=True)
            
            sig = await client.place_perp_order(params, sub_account_id=int(sub_id))
            await client.unsubscribe()
            await async_client.close()
            return sig
        except Exception as e:
            st.error(f"Execution Error: {e}"); return None

    # 6. ACTION PANEL
    st.markdown("---")
    ec1, ec2 = st.columns(2)
    
    if cur_lev > 0:
        side = "LONG" if tr_longs >= 4 else "SHORT"
        if ec1.button(f"🚀 Execute Drift {side} ({cur_lev}x)", use_container_width=True):
            with st.spinner("Talking to Solana..."):
                sig = asyncio.run(run_drift_action("TRADE", side, cur_lev))
                if sig:
                    st.success(f"Trade Success! TX: {sig}")
                    st.session_state.trade_history.append({"Time": time.strftime("%H:%M"), "Action": f"{side} {cur_lev}x"})

    if ec2.button("🔴 CLOSE ALL POSITIONS", use_container_width=True):
        with st.spinner("Closing all..."):
            sig = asyncio.run(run_drift_action("CLOSE"))
            if sig: 
                st.warning("Position Close Requested.")
                st.session_state.trade_history.append({"Time": time.strftime("%H:%M"), "Action": "CLOSE ALL"})

    if st.session_state.trade_history:
        st.table(pd.DataFrame(st.session_state.trade_history).tail(5))
