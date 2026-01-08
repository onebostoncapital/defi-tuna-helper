import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import smtplib, time, asyncio
from email.mime.text import MIMEText
from streamlit_autorefresh import st_autorefresh
from data_engine import fetch_base_data

# --- DRIFT PROTOCOL CORE ---
from solders.keypair import Keypair
from driftpy.drift_client import DriftClient
from driftpy.constants.numeric_constants import BASE_PRECISION
from driftpy.types import OrderType, PositionDirection, OrderParams
from anchorpy import Wallet

# 1. UI REFRESH HEARTBEAT
st.set_page_config(page_title="Sreejan Perp Sentinel Pro", layout="wide")
st_autorefresh(interval=1000, key="ui_pulse") # 1s update for the live clock

if 'last_market_update' not in st.session_state: st.session_state.last_market_update = time.time()
if 'chart_tf' not in st.session_state: st.session_state.chart_tf = "1h"
if 'last_trade_time' not in st.session_state: st.session_state.last_trade_time = 0
if 'trade_history' not in st.session_state: st.session_state.trade_history = []

# 2. SIDEBAR - DRIFT & ALERTS
with st.sidebar:
    st.header("🔐 Sentinel Config")
    rpc_url = st.text_input("Solana RPC URL", value="https://api.mainnet-beta.solana.com")
    pk_base58 = st.text_input("Private Key (Base58)", type="password")
    sub_id = st.number_input("Drift Sub-Account ID", value=0)
    
    st.markdown("---")
    sender = st.text_input("Gmail", value="sreejan@onebostoncapital.com")
    gmail_pwd = st.text_input("App Password", type="password")
    total_cap = st.number_input("Drift Equity ($)", value=1000.0)
    auto_pilot = st.toggle("🚀 ENABLE AUTO-PILOT")
    
    # Live Timer
    elapsed = time.time() - st.session_state.last_market_update
    time_to_refresh = max(0, int(30 - elapsed))
    st.subheader(f"⏱️ Syncing in: {time_to_refresh}s")
    st.progress(time_to_refresh / 30)

# Refresh Data Trigger
if time_to_refresh <= 0:
    st.session_state.last_market_update = time.time()
    st.cache_data.clear()
    st.rerun()

# 3. ANALYSIS & 8-JUDGE MATRIX
df, btc_p, err, status = fetch_base_data(st.session_state.chart_tf)

if status:
    price = df['close'].iloc[-1]
    c1, c2, c3 = st.columns(3)
    c1.metric("₿ BTC Price", f"${btc_p:,.2f}")
    c2.metric(f"S SOL ({st.session_state.chart_tf})", f"${price:,.2f}")

    # CONSENSUS MATRIX UI
    st.markdown("### 🏛️ Consensus Judge Matrix (8-Judges)")
    tfs = ["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d"]
    mcols = st.columns(8)
    tr_longs, tr_shorts = 0, 0

    for i, t in enumerate(tfs):
        dm, _, _, sm = fetch_base_data(t)
        if sm:
            p, e, s = dm['close'].iloc[-1], dm['20_ema'].iloc[-1], dm['200_sma'].iloc[-1]
            if p > s and p > e: 
                sig, clr, bg_c = "🟢 LONG", "#0ff0", "rgba(0, 255, 0, 0.1)"
                tr_longs += 1
            elif p < s and p < e: 
                sig, clr, bg_c = "🔴 SHORT", "#f44", "rgba(255, 0, 0, 0.1)"
                tr_shorts += 1
            else: 
                sig, clr, bg_c = "🟡 WAIT", "#888", "rgba(128, 128, 128, 0.1)"
            
            mcols[i].markdown(f"<div style='border:1px solid {clr}; border-radius:5px; padding:10px; background-color:{bg_c}; text-align:center;'><b>{t}</b><br><span style='color:{clr};'>{sig}</span></div>", unsafe_allow_html=True)

    # LEVERAGE LOGIC
    tr_count = max(tr_longs, tr_shorts)
    lev_map = {4: 2, 5: 3, 6: 4, 7: 5, 8: 5}
    cur_lev = lev_map.get(tr_count, 0) if tr_count >= 4 else 0
    c3.metric("Execution Judge", f"{tr_count}/8 Align", f"{cur_lev}x Leverage" if cur_lev > 0 else "WAIT")

    # 4. CHART WITH 20 EMA & 200 SMA
    fig = go.Figure(data=[go.Candlestick(x=df['date'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="SOL")])
    fig.add_trace(go.Scatter(x=df['date'], y=df['20_ema'], name="20 EMA", line=dict(color="#854CE6", width=2)))
    fig.add_trace(go.Scatter(x=df['date'], y=df['200_sma'], name="200 SMA", line=dict(color="#FF9900", width=2, dash='dot')))
    fig.update_layout(template="plotly_dark", height=450, xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig, use_container_width=True)

    # 5. DRIFT EXECUTION LOGIC
    async def execute_drift_order(side, leverage):
        if not pk_base58: return None
        try:
            kp = Keypair.from_base58_string(pk_base58)
            wallet = Wallet(kp)
            client = DriftClient(rpc_url, wallet, account_subscription="polling")
            
            # Calculate 5% Capital Trade Size
            usd_val = total_cap * 0.05 * leverage
            sol_qty = int((usd_val / price) * BASE_PRECISION)
            
            direction = PositionDirection.Long() if side == "LONG" else PositionDirection.Short()
            params = OrderParams(order_type=OrderType.Market(), market_index=0, direction=direction, base_asset_amount=sol_qty)
            
            tx_sig = await client.place_perp_order(params, sub_account_id=sub_id)
            return tx_sig
        except Exception as e:
            st.error(f"Drift Error: {str(e)}")
            return None

    def send_alert(side, lev, consensus):
        try:
            body = f"SENTINEL DISPATCH\nSide: {side}\nLev: {lev}x\nConsensus: {consensus}/8\nAmt: 5% (${total_cap*0.05})"
            msg = MIMEText(body); msg['Subject'] = f"🛡️ {side} Trade Alert"; msg['From'] = sender; msg['To'] = sender
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
                s.login(sender, gmail_pwd); s.send_message(msg)
            return True
        except: return False

    # 6. TRIGGER LOGIC
    if cur_lev > 0:
        side = "LONG" if tr_longs >= 4 else "SHORT"
        
        # AUTO-PILOT
        if auto_pilot and (time.time() - st.session_state.last_trade_time > 300):
            tx = asyncio.run(execute_drift_order(side, cur_lev))
            if tx:
                st.session_state.last_trade_time = time.time()
                send_alert(side, cur_lev, tr_count)
                st.session_state.trade_history.append({"Time": time.strftime("%H:%M"), "Side": side, "Lev": cur_lev, "Type": "AUTO"})
                st.toast(f"🚀 AUTO-PILOT Executed: {side} {cur_lev}x")

        # MANUAL EXECUTE
        if st.button(f"🚀 Manual: {side} ({cur_lev}x)"):
            tx = asyncio.run(execute_drift_order(side, cur_lev))
            if tx:
                send_alert(side, cur_lev, tr_count)
                st.session_state.trade_history.append({"Time": time.strftime("%H:%M"), "Side": side, "Lev": cur_lev, "Type": "MANUAL"})
                st.success(f"Trade Success: {tx}")

    if st.session_state.trade_history:
        st.write("### 📜 Live Trade Logs")
        st.table(pd.DataFrame(st.session_state.trade_history).tail(5))
else:
    st.error(f"Connection Failed: {err}")
