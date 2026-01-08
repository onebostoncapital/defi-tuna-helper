import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
from streamlit_autorefresh import st_autorefresh
from data_engine import fetch_base_data

# 1. PAGE SETUP
st.set_page_config(page_title="Sentinel Pro: 66s Sync", layout="wide")
st_autorefresh(interval=1000, key="pulse")

if 'last_upd' not in st.session_state: st.session_state.last_upd = time.time()
if 'chart_tf' not in st.session_state: st.session_state.chart_tf = "1h"

# 2. 66s REFRESH LOGIC
elapsed = time.time() - st.session_state.last_upd
remaining = max(0, int(66 - elapsed))
if elapsed >= 66:
    st.cache_data.clear()
    st.session_state.last_upd = time.time()
    st.rerun()

# 3. PRE-CALCULATE ALL JUDGES (Crucial for the Box)
tfs = ["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d"]
judge_results = []
long_count = 0
short_count = 0

for t in tfs:
    df, btc_p, err, ok = fetch_base_data(t)
    if ok:
        p, e, s = df['close'].iloc[-1], df['20_ema'].iloc[-1], df['200_sma'].iloc[-1]
        if p > s and p > e:
            judge_results.append({"tf": t, "sig": "🟢 LONG", "clr": "#0ff0", "bg": "rgba(0,255,0,0.1)"})
            long_count += 1
        elif p < s and p < e:
            judge_results.append({"tf": t, "sig": "🔴 SHORT", "clr": "#f44", "bg": "rgba(255,0,0,0.1)"})
            short_count += 1
        else:
            judge_results.append({"tf": t, "sig": "🟡 WAIT", "clr": "#888", "bg": "rgba(128,128,128,0.1)"})

# 4. FINAL SIGNAL LOGIC
total_confidence = max(long_count, short_count)
is_valid_signal = total_confidence >= 4
final_direction = "GO LONG" if long_count >= short_count else "GO SHORT"

lev_map = {4: "2x", 5: "3x", 6: "4x", 7: "5x", 8: "5x"}
recommended_lev = lev_map.get(total_confidence, "WAITING")

box_border_color = "#0ff0" if (is_valid_signal and final_direction == "GO LONG") else "#f44" if is_valid_signal else "#444"
final_bias_display = final_direction if is_valid_signal else "NEUTRAL"
final_lev_display = f"USE {recommended_lev} LEVERAGE" if is_valid_signal else "WAIT FOR 4/8 JUDGES"

# 5. UI DISPLAY - HEADER
df_h, btc_price, _, _ = fetch_base_data("1h")
sol_price = df_h['close'].iloc[-1] if df_h is not None else 0

c1, c2 = st.columns(2)
c1.markdown(f"<h1 style='text-align:center; font-size:60px;'>SOL: ${sol_price:,.2f}</h1>", unsafe_allow_html=True)
c2.markdown(f"<h1 style='text-align:center; font-size:60px;'>BTC: ${btc_price:,.2f}</h1>", unsafe_allow_html=True)

# 6. JUDGE MATRIX DISPLAY
st.write("### 🏛️ Consensus Judge Matrix")
m_cols = st.columns(8)
for i, res in enumerate(judge_results):
    m_cols[i].markdown(f"<div style='border:1px solid {res['clr']}; border-radius:5px; padding:10px; background-color:{res['bg']}; text-align:center;'><b>{res['tf']}</b><br>{res['sig']}</div>", unsafe_allow_html=True)

# 7. THE GLOBAL BIAS BOX (THE ULTIMATE FIX)
st.markdown("---")
st.markdown(
    f"""
    <div style="background-color: #1e2129; border: 5px solid {box_border_color}; border-radius: 15px; padding: 50px; text-align: center;">
        <p style="color: #888; margin: 0; font-size: 20px; letter-spacing: 2px;">SREEJAN INTELLIGENCE CONSENSUS</p>
        <h1 style="color: white; font-size: 75px; margin: 15px 0; font-weight: 800;">
            GLOBAL BIAS: <span style="color: {box_border_color};">{final_bias_display}</span>
        </h1>
        <h2 style="color: {box_border_color}; font-size: 50px; margin: 10px 0; font-weight: 600;">
            {final_lev_display}
        </h2>
        <p style="color: #666; font-size: 18px; margin-top: 20px;">
            Confidence: {total_confidence}/8 Judges | Logic: EMA 20 + SMA 200 | Next Sync: {remaining}s
        </p>
    </div>
    """, unsafe_allow_html=True
)

# 8. CHART NAVIGATION & PLOT
st.markdown("---")
nav = st.columns(8)
for i, t in enumerate(tfs):
    if nav[i].button(t, key=f"btn_{t}", use_container_width=True):
        st.session_state.chart_tf = t
        st.rerun()

df_c, _, _, _ = fetch_base_data(st.session_state.chart_tf)
if df_c is not None:
    fig = go.Figure(data=[go.Candlestick(x=df_c['date'], open=df_c['open'], high=df_c['high'], low=df_c['low'], close=df_c['close'])])
    fig.add_trace(go.Scatter(x=df_c['date'], y=df_c['20_ema'], name="20 EMA", line=dict(color="#854CE6")))
    fig.add_trace(go.Scatter(x=df_c['date'], y=df_c['200_sma'], name="200 SMA", line=dict(color="#FF9900", dash='dot')))
    fig.update_layout(template="plotly_dark", height=500, margin=dict(l=0,r=0,t=0,b=0), xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)
