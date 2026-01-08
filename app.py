import streamlit as st
import plotly.graph_objects as go
from data_engine import fetch_base_data

st.set_page_config(page_title="Terminal Alpha: Perp", layout="wide")

# High-Contrast Style
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF !important; }
    h1, h2 { color: #D4AF37 !important; }
    </style>
""", unsafe_allow_html=True)

st.title("📉 Perp Trading Indicator")
st.sidebar.title("Settings")
tf = st.sidebar.selectbox("Timeframe", ["1m", "5m", "15m", "1h", "4h", "1d"], index=5)

df, btc_p, daily_atr, status = fetch_base_data(tf)

if status:
    price = df['close'].iloc[-1]
    ema20 = df['20_ema'].iloc[-1]
    sma200 = df['200_sma'].iloc[-1]

    # Signal Table
    if price > sma200 and price > ema20:
        sig, color = "STRONG BUY 🟢", "#00FFA3"
    elif price < sma200 and price < ema20:
        sig, color = "STRONG SELL 🔴", "#FF4B4B"
    else:
        sig, color = "NEUTRAL ⚖️", "#888"

    st.header(f"Bias: {sig}")
    st.metric("BTC Price", f"${btc_p:,.2f}")

    # Chart
    fig = go.Figure(data=[go.Candlestick(x=df['date'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
    fig.add_trace(go.Scatter(x=df['date'], y=df['20_ema'], name="20 EMA", line=dict(color="#854CE6")))
    fig.add_trace(go.Scatter(x=df['date'], y=df['200_sma'], name="200 SMA", line=dict(color="#FF9900", dash='dot')))
    fig.update_layout(template="plotly_dark", paper_bgcolor='black', plot_bgcolor='black')
    st.plotly_chart(fig, use_container_width=True)
