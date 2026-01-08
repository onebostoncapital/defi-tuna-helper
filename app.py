import streamlit as st
import plotly.graph_objects as go
from data_engine import fetch_base_data

st.set_page_config(page_title="Perp Indicator", layout="wide")

# Rule 14: Theme Toggle
theme = st.sidebar.radio("Theme Mode", ["Dark Mode", "Light Mode"])
bg = "#000000" if theme == "Dark Mode" else "#FFFFFF"
txt = "#FFFFFF" if theme == "Dark Mode" else "#000000"
st.markdown(f"<style>.stApp {{ background-color: {bg}; color: {txt} !important; }} h1, h2 {{ color: #D4AF37 !important; }}</style>", unsafe_allow_html=True)

tf = st.sidebar.selectbox("Timeframe", ["1m", "5m", "15m", "1h", "4h", "1d"], index=3)
df, btc_p, _, status = fetch_base_data(tf)

if status:
    # Rule 13: Price Banner
    c1, c2 = st.columns(2)
    c1.metric("₿ BTC", f"${btc_p:,.2f}")
    c2.metric("S SOL", f"${df['close'].iloc[-1]:,.2f}")
    st.divider()

    # Rule 1: Emmanuel Logic
    price, ema20, sma200 = df['close'].iloc[-1], df['20_ema'].iloc[-1], df['200_sma'].iloc[-1]
    sig = "BUY 🟢" if price > sma200 and price > ema20 else "SELL 🔴" if price < sma200 and price < ema20 else "NEUTRAL ⚖️"
    st.header(f"Strategy Signal: {sig}")

    fig = go.Figure(data=[go.Candlestick(x=df['date'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
    fig.add_trace(go.Scatter(x=df['date'], y=df['20_ema'], name="20 EMA", line=dict(color="#854CE6")))
    fig.add_trace(go.Scatter(x=df['date'], y=df['200_sma'], name="200 SMA", line=dict(color="#FF9900", dash='dot')))
    fig.update_layout(template="plotly_dark" if theme=="Dark Mode" else "plotly_white", paper_bgcolor=bg, plot_bgcolor=bg)
    st.plotly_chart(fig, use_container_width=True)
