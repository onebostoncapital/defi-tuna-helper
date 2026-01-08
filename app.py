import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
from streamlit_autorefresh import st_autorefresh
from data_engine import fetch_base_data

# 1. UI SETUP
st.set_page_config(page_title="Sreejan Sentinel: Intelligence Pro", layout="wide")
st_autorefresh(interval=1000, key="ui_pulse")

# Initialize Session States
if 'last_market_update' not in st.session_state: 
    st.session_state.last_market_update = time.time()
if 'chart_tf' not in st.session_state:
    st.session_state.chart_tf = "1h" # Default chart timeframe

# 2. DATA FETCH (PRIMARY)
df_main, btc_p, err_msg, status = fetch_base_data("1h")

if status and df_main is not None:
    sol_p = df_main['close'].iloc[-1]
    
    # TOP BAR METRICS (RESTORED)
    m1, m2, m3 = st.columns([2, 2, 4])
    m1.metric("🪙 SOLANA PRICE", f"${sol_p:,.2f}")
    m2.metric("₿ BITCOIN PRICE", f"${btc_p:,.2f}")
    
    with st.sidebar:
        st.header("📊 Intelligence Settings")
        st.success("✅ Engine: Online")
        st.info("Stable Mode: Information Only")
        
        elapsed = time.time() - st.session_state.last_market_update
        st.write(f"⏱️ Matrix Update: {max(0, int(30 - elapsed))}s")
        
        if (time.time() - st.session_state.last_market_update) >= 30:
            st.session_state.last_market_update = time.time()
            st.cache_data.clear()
            st.rerun()

    # 3. 8-JUDGE CONSENSUS MATRIX (RESTORED)
    st.markdown("### 🏛️ Consensus Judge Matrix")
    tfs = ["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d"]
    mcols = st.columns(8)
    tr_longs, tr_shorts = 0, 0

    for i, t in enumerate(tfs):
        dm, _, _, sm = fetch_base_data(t)
        if sm and dm is not None:
            p, e, s = dm['close'].iloc[-1], dm['20_ema'].iloc[-1], dm['200_sma'].iloc[-1]
            if p > s and p > e:
                sig, clr, bg = "🟢 LONG", "#0ff0", "rgba(0,255,0,0.1)"
                tr_longs += 1
            elif p < s and p < e:
                sig, clr, bg = "🔴 SHORT", "#f44", "rgba(255,0,0,0.1)"
                tr_shorts += 1
            else:
                sig, clr, bg = "🟡 WAIT", "#888", "rgba(128,128,128,0.1)"
            
            mcols[i].markdown(
                f"<div style='border:1px solid {clr}; border-radius:5px; padding:10px; "
                f"background-color:{bg}; text-align:center;'><b>{t}</b><br>"
                f"<span style='color:{clr}'>{sig}</span></div>", 
                unsafe_allow_html=True
            )

    # 4. CONSOLIDATED CONSENSUS BOX (RESTORED)
    st.markdown("---")
    tr_count = max(tr_longs, tr_shorts)
    final_dir = "LONG" if tr_longs >= tr_shorts else "SHORT"
    lev_map = {4: 2, 5: 3, 6: 4, 7: 5, 8: 5}
    cur_lev = lev_map.get(tr_count, 0) if tr_count >= 4 else 0
    con_clr = "#0ff0" if final_dir == "LONG" and cur_lev > 0 else "#f44" if cur_lev > 0 else "#888"
    
    st.markdown(
        f"<div style='border:2px solid {con_clr}; border-radius:10px; padding:25px; "
        f"background-color:rgba(0,0,0,0.4); text-align:center;'>"
        f"<h1 style='margin:0;'>GLOBAL BIAS: <span style='color:{con_clr}'>{final_dir if cur_lev > 0 else 'NEUTRAL'}</span></h1>"
        f"<h3>Confidence: {tr_count}/8 Judges | Leverage: {cur_lev}x</h3>"
        f"</div>", unsafe_allow_html=True
    )

    # 5. CHART NAVIGATION (NEW FEATURE)
    st.markdown("---")
    st.write("### 📈 Technical Chart Navigation")
    # Row of buttons for timeframe selection
    nav_cols = st.columns(len(tfs))
    for i, t in enumerate(tfs):
        if nav_cols[i].button(t, key=f"btn_{t}", use_container_width=True):
            st.session_state.chart_tf = t
            st.rerun()

    # 6. DYNAMIC CHART DATA
    # Fetch data specifically for the selected timeframe
    df_chart, _, _, c_status = fetch_base_data(st.session_state.chart_tf)
    
    if c_status and df_chart is not None:
        st.write(f"Displaying **{st.session_state.chart_tf}** SOL Price Action")
        fig = go.Figure(data=[go.Candlestick(
            x=df_chart['date'], open=df_chart['open'], high=df_chart['high'], 
            low=df_chart['low'], close=df_chart['close'], name="Price"
        )])
        fig.add_trace(go.Scatter(x=df_chart['date'], y=df_chart['20_ema'], name="20 EMA", line=dict(color="#854CE6")))
        fig.add_trace(go.Scatter(x=df_chart['date'], y=df_chart['200_sma'], name="200 SMA", line=dict(color="#FF9900", dash='dot')))
        
        fig.update_layout(template="plotly_dark", height=500, margin=dict(l=0,r=0,t=0,b=0), xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

else:
    st.error(f"Engine Error: {err_msg}")
