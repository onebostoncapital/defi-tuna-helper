import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
from streamlit_autorefresh import st_autorefresh
from data_engine import fetch_base_data

# 1. UI SETUP & CONFIGURATION
st.set_page_config(page_title="Sreejan Sentinel: Intelligence Dashboard", layout="wide")
st_autorefresh(interval=1000, key="ui_pulse") # 1-second UI pulse

# Initialize session state for persistence
if 'last_market_update' not in st.session_state: 
    st.session_state.last_market_update = time.time()

# 2. HEADER DATA (BITCOIN & SOLANA PRICE RESTORED)
# We fetch the primary data (1h timeframe) to get current prices
df, btc_p, err, status = fetch_base_data("1h")

if status:
    sol_p = df['close'].iloc[-1]
    
    # TOP BAR METRICS: Restoring the dual-price display
    m1, m2, m3 = st.columns([2, 2, 4])
    m1.metric("🪙 SOLANA PRICE", f"${sol_p:,.2f}")
    m2.metric("₿ BITCOIN PRICE", f"${btc_p:,.2f}")
    
    # SIDEBAR: Information & Controls
    with st.sidebar:
        st.header("📊 Intelligence Settings")
        st.success("✅ Stable Mode: Information Only")
        st.info("Execution features disabled to maintain dashboard stability.")
        
        # Market Sync Timer
        elapsed = time.time() - st.session_state.last_market_update
        st.write(f"⏱️ Matrix Update in: {max(0, int(30 - elapsed))}s")
        
        if (time.time() - st.session_state.last_market_update) >= 30:
            st.session_state.last_market_update = time.time()
            st.cache_data.clear()
            st.rerun()

    # 3. 8-JUDGE CONSENSUS MATRIX (RESTORED)
    # Rules: 8 timeframes, 20 EMA vs 200 SMA comparison
    st.markdown("### 🏛️ Consensus Judge Matrix")
    tfs = ["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d"]
    mcols = st.columns(8)
    tr_longs, tr_shorts = 0, 0

    for i, t in enumerate(tfs):
        dm, _, _, sm = fetch_base_data(t)
        if sm:
            p, e, s = dm['close'].iloc[-1], dm['20_ema'].iloc[-1], dm['200_sma'].iloc[-1]
            
            # Rule: Price must be above both EMA and SMA for LONG
            if p > s and p > e:
                sig, clr, bg = "🟢 LONG", "#0ff0", "rgba(0,255,0,0.1)"
                tr_longs += 1
            # Rule: Price must be below both EMA and SMA for SHORT
            elif p < s and p < e:
                sig, clr, bg = "🔴 SHORT", "#f44", "rgba(255,0,0,0.1)"
                tr_shorts += 1
            else:
                sig, clr, bg = "🟡 WAIT", "#888", "rgba(128,128,128,0.1)"
            
            # Displaying the Judge Box
            mcols[i].markdown(
                f"<div style='border:1px solid {clr}; border-radius:5px; padding:10px; "
                f"background-color:{bg}; text-align:center;'><b>{t}</b><br>"
                f"<span style='color:{clr}'>{sig}</span></div>", 
                unsafe_allow_html=True
            )

    # 4. CONSOLIDATED CONSENSUS BOX (RESTORED)
    # Rule: Minimum 4/8 consensus for a signal. Leverage scales with confidence.
    st.markdown("---")
    tr_count = max(tr_longs, tr_shorts)
    final_dir = "LONG" if tr_longs >= tr_shorts else "SHORT"
    
    # Defined Leverage Rule-set
    lev_map = {4: 2, 5: 3, 6: 4, 7: 5, 8: 5}
    cur_lev = lev_map.get(tr_count, 0) if tr_count >= 4 else 0
    
    con_clr = "#0ff0" if final_dir == "LONG" and cur_lev > 0 else "#f44" if cur_lev > 0 else "#888"
    
    st.markdown(
        f"<div style='border:2px solid {con_clr}; border-radius:10px; padding:25px; "
        f"background-color:rgba(0,0,0,0.4); text-align:center;'>"
        f"<h1 style='margin:0;'>GLOBAL BIAS: <span style='color:{con_clr}'>{final_dir if cur_lev > 0 else 'NEUTRAL'}</span></h1>"
        f"<h3>Confidence: {tr_count}/8 Judges | Logic: 20 EMA + 200 SMA</h3>"
        f"<h2>Recommended Leverage: <span style='color:{con_clr}'>{cur_lev}x</span></h2>"
        f"</div>", unsafe_allow_html=True
    )

    # 5. TECHNICAL CHART
    st.markdown("---")
    fig = go.Figure(data=[go.Candlestick(
        x=df['date'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="Price"
    )])
    fig.add_trace(go.Scatter(x=df['date'], y=df['20_ema'], name="20 EMA", line=dict(color="#854CE6")))
    fig.add_trace(go.Scatter(x=df['date'], y=df['200_sma'], name="200 SMA", line=dict(color="#FF9900", dash='dot')))
    
    fig.update_layout(
        template="plotly_dark", 
        height=500, 
        margin=dict(l=0,r=0,t=0,b=0),
        xaxis_rangeslider_visible=False
    )
    st.plotly_chart(fig, use_container_width=True)

else:
    st.error("Engine Offline. Check data source connection in data_engine.py")
