import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
from streamlit_autorefresh import st_autorefresh
from data_engine import fetch_base_data

# 1. UI SETUP
st.set_page_config(page_title="Sreejan Sentinel Pro", layout="wide")
st_autorefresh(interval=1000, key="pulse")

if 'last_upd' not in st.session_state: st.session_state.last_upd = time.time()
if 'chart_tf' not in st.session_state: st.session_state.chart_tf = "1h"

# 2. 66s SYNC RULE
elapsed = time.time() - st.session_state.last_upd
remaining = max(0, int(66 - elapsed))
if elapsed >= 66:
    st.cache_data.clear()
    st.session_state.last_upd = time.time()
    st.rerun()

# 3. DATA FETCH
df_m, btc_p, err, status = fetch_base_data("1h")

if status:
    sol_p = df_m['close'].iloc[-1]
    
    # Large Headers
    h1, h2 = st.columns(2)
    h1.markdown(f"<h1 style='text-align:center; font-size:60px;'>SOL: ${sol_p:,.2f}</h1>", unsafe_allow_html=True)
    h2.markdown(f"<h1 style='text-align:center; font-size:60px;'>BTC: ${btc_p:,.2f}</h1>", unsafe_allow_html=True)

    # 4. 8-JUDGE MATRIX
    st.write("### 🏛️ Consensus Judge Matrix")
    tfs = ["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d"]
    cols = st.columns(8)
    longs, shorts = 0, 0

    for i, t in enumerate(tfs):
        df, _, _, ok = fetch_base_data(t)
        if ok:
            p, e, s = df['close'].iloc[-1], df['20_ema'].iloc[-1], df['200_sma'].iloc[-1]
            if p > s and p > e:
                msg, clr, bg = "🟢 LONG", "#0ff0", "rgba(0,255,0,0.1)"
                longs += 1
            elif p < s and p < e:
                msg, clr, bg = "🔴 SHORT", "#f44", "rgba(255,0,0,0.1)"
                shorts += 1
            else:
                msg, clr, bg = "🟡 WAIT", "#888", "rgba(128,128,128,0.1)"
            
            cols[i].markdown(f"<div style='border:1px solid {clr}; border-radius:5px; padding:10px; background-color:{bg}; text-align:center;'><b>{t}</b><br>{msg}</div>", unsafe_allow_html=True)

    # 5. THE GLOBAL BIAS BOX (THE "NO-BLANK" FIX)
    st.markdown("---")
    
    # Determine the strongest signal
    score = max(longs, shorts)
    side = "GO LONG" if longs >= shorts else "GO SHORT"
    
    # Leverage Mapping
    lev_map = {4: "2x", 5: "3x", 6: "4x", 7: "5x", 8: "5x"}
    lev_val = lev_map.get(score, "WAITING")
    
    # Box Appearance logic
    box_color = "#0ff0" if (score >= 4 and side == "GO LONG") else "#f44" if (score >= 4) else "#555"
    display_signal = side if score >= 4 else "NEUTRAL"
    display_lev = f"USE {lev_val} LEVERAGE" if score >= 4 else "WAIT FOR 4/8 JUDGES"

    # SINGLE BLOCK HTML - This prevents the text from being "missing"
    st.markdown(
        f"""
        <div style="background-color: #1e2129; border: 5px solid {box_color}; border-radius: 15px; padding: 50px; text-align: center;">
            <p style="color: #888; margin: 0; font-size: 20px;">Sreejan Intelligence Consensus</p>
            <h1 style="color: white; font-size: 70px; margin: 10px 0;">GLOBAL BIAS: <span style="color: {box_color};">{display_signal}</span></h1>
            <h2 style="color: {box_color}; font-size: 50px; margin: 5px 0;">{display_lev}</h2>
            <p style="color: #666; font-size: 18px; margin-top: 15px;">Confidence: {score}/8 Judges | Logic: EMA 20 + SMA 200 | Sync: {remaining}s</p>
        </div>
        """, unsafe_allow_html=True
    )

    # 6. CHART CONTROLS
    st.markdown("---")
    nav = st.columns(8)
    for i, t in enumerate(tfs):
        if nav[i].button(t, key=f"btn_{t}", use_container_width=True):
            st.session_state.chart_tf = t
            st.rerun()

    # 7. MAIN CHART
    df_c, _, _, c_ok = fetch_base_data(st.session_state.chart_tf)
    if c_ok:
        fig = go.Figure(data=[go.Candlestick(x=df_c['date'], open=df_c['open'], high=df_c['high'], low=df_c['low'], close=df_c['close'])])
        fig.add_trace(go.Scatter(x=df_c['date'], y=df_c['20_ema'], name="20 EMA", line=dict(color="#854CE6")))
        fig.add_trace(go.Scatter(x=df_c['date'], y=df_c['200_sma'], name="200 SMA", line=dict(color="#FF9900", dash='dot')))
        fig.update_layout(template="plotly_dark", height=500, margin=dict(l=0,r=0,t=0,b=0), xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

else:
    st.error(f"Reconnecting... {err}")
