import ccxt
import pandas as pd
import streamlit as st
import requests
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. DATA ENGINE
@st.cache_data(ttl=10)
def fetch_sol_market_data():
    try:
        exchange = ccxt.kraken()
        bars = exchange.fetch_ohlcv('SOL/USD', timeframe='1d', limit=40)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception:
        return None

# 2. NEWS ENGINE
@st.cache_data(ttl=300)
def fetch_crypto_news():
    try:
        url = "https://min-api.cryptocompare.com/data/v2/news/?lang=EN"
        response = requests.get(url).json()
        return response['Data'][:5]
    except:
        return []

def get_sreejan_forecaster():
    st.set_page_config(page_title="Sreejan Range Forecaster", page_icon="🟣", layout="wide")

    # --- SIDEBAR: GLOBAL SETTINGS ---
    st.sidebar.header("💰 Investment Settings")
    capital = st.sidebar.number_input("Capital Amount ($)", min_value=10.0, value=10000.0, step=100.0)
    
    # RULE: Leverage Dots 1.0 - 2.0
    lev_options = [1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0]
    lev_choice = st.sidebar.select_slider("Select Leverage", options=lev_options, value=1.5)
    
    btc_trend = st.sidebar.selectbox("Market Sentiment", ["Bullish 🚀", "Neutral ⚖️", "Bearish 📉"])
    
    if st.sidebar.button("🔄 Force Refresh"):
        st.cache_data.clear()
        st.rerun()

    # --- DATA PROCESSING ---
    df = fetch_sol_market_data()
    
    if df is not None:
        price = df['close'].iloc[-1]
        last_date = df['date'].iloc[-1]
        
        # ATR for Auto-Range calculation
        df['tr'] = df[['high', 'low', 'close']].max(axis=1) - df[['high', 'low', 'close']].min(axis=1)
        atr = df['tr'].rolling(window=14).mean().iloc[-1]
        
        # RULE: Liquidation Price Calculation
        # Assuming ~40% margin maintenance level for crypto-leverage logic
        liq_price = price * (1 - (1 / lev_choice) * 0.45) if lev_choice > 1.0 else 0
        
        # Forecast Math
        forecast_dates = [last_date + timedelta(days=i) for i in range(1, 6)]
        bias = 0.015 if btc_trend == "Bullish 🚀" else -0.015 if btc_trend == "Bearish 📉" else 0
        forecast_prices = [price * ((1 + bias) ** i) for i in range(1, 6)]

        # --- HEADER METRICS ---
        st.title("🏦 Sreejan Range Forecaster")
        m1, m2, m3 = st.columns(3)
        m1.metric("Live SOL Price", f"${price:,.2f}")
        m2.metric("Total Position Size", f"${(capital * lev_choice):,.2f}")
        # RULE: Liquidation Price in Top Metrics
        m3.metric("Liquidation Price", f"${liq_price:,.2f}" if liq_price > 0 else "SAFE")

        # --- CHART: REACTIVE FORECAST ---
        st.subheader("📊 Reactive Forecast Horizon")
        hist_10 = df.tail(10)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=hist_10['date'], y=hist_10['close'], name='History', line=dict(color='#854CE6', width=4)))
        fig.add_trace(go.Scatter(x=forecast_dates, y=forecast_prices, name='Forecast', line=dict(color='#00FFA3', dash='dash', width=3)))
        
        # RULE: Vertical Line and Price Marker
        fig.add_vline(x=last_date, line_width=2, line_dash="solid", line_color="white")
        fig.add_trace(go.Scatter(x=[last_date], y=[price], mode='markers+text', text=[f"${price:,.2f}"], textposition="top center", marker=dict(color='white', size=10)))
        
        fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig, use_container_width=True)

        st.divider()

        # --- CORE: RANGE SELECTOR ---
        st.subheader("🎯 Strategy Range Configurator")
        
        # RULE: Bold Auto-Range Recommendation
        mult = 3.2 if btc_trend == "Bearish 📉" else 2.2 if btc_trend == "Bullish 🚀" else 2.7
        auto_low, auto_high = price - (atr * mult), price + (atr * mult)
        st.markdown(f"### **Auto-Generated Range: ${auto_low:,.2f} — ${auto_high:,.2f}**")
        
        # RULE: Dual-Handle Manual Slider
        manual_range = st.slider(
            "Manual Range Tuning",
            min_value=float(price * 0.4),
            max_value=float(price * 1.6),
            value=(float(auto_low), float(auto_high)),
            step=0.10,
            format="$%.2f"
        )
        m_low, m_high = manual_range

        # Warning if manual range is dangerous
        if liq_price > 0 and m_low <= liq_price:
            st.warning(f"⚠️ **Alert:** Lower range boundary (${m_low:,.2f}) is dangerously close to or below Liquidation (${liq_price:,.2f})!")

        # --- YIELD PROJECTIONS (RULE: 7 Time Horizons) ---
        position_size = capital * lev_choice
        range_width = max(m_high - m_low, 0.01)
        efficiency = (price * 0.35) / range_width
        daily_profit = (position_size * 0.0017) * efficiency
        
        st.markdown(f"#### 💰 Estimated Returns (Based on ${daily_profit:,.2f}/day)")
        p_cols = st.columns(7)
        p_cols[0].metric("1 HR", f"${(daily_profit/24):,.2f}")
        p_cols[1].metric("3 HR", f"${(daily_profit/24*3):,.2f}")
        p_cols[2].metric("6 HR", f"${(daily_profit/24*6):,.2f}")
        p_cols[3].metric("12 HR", f"${(daily_profit/2):,.2f}")
        p_cols[4].metric("1 Day", f"${daily_profit:,.2f}")
        p_cols[5].metric("1 Week", f"${daily_profit*7:,.2f}")
        p_cols[6].metric("1 Month", f"${daily_profit*30:,.2f}")

        # --- DATA TABLES ---
        st.divider()
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            st.write("**Price History (Last 5 Days)**")
            st.table(hist_10[['date', 'close']].tail(5).rename(columns={'date': 'Date', 'close': 'Price'}).set_index('Date'))
        with col_t2:
            st.write("**Forecasted Prices**")
            f_df = pd.DataFrame({'Date': forecast_dates, 'Price': forecast_prices}).set_index('Date')
            st.table(f_df)

        # --- RULE: News at the Bottom ---
        st.divider()
        st.subheader("📰 Global Crypto News Feed")
        news = fetch_crypto_news()
        if news:
            n_cols = st.columns(len(news))
            for idx, article in enumerate(news):
                with n_cols[idx]:
                    st.markdown(f"**[{article['title'][:45]}...]({article['url']})**")
                    st.caption(f"{article['source']}")

    else:
        st.error("Market data unavailable. Please refresh.")

if __name__ == "__main__":
    get_sreejan_forecaster()
