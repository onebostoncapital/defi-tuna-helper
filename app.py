import ccxt
import pandas as pd
import streamlit as st
import requests
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. FETCH LIVE MARKET DATA & HISTORY
@st.cache_data(ttl=60)
def fetch_sol_market_data():
    try:
        exchange = ccxt.kraken()
        bars = exchange.fetch_ohlcv('SOL/USD', timeframe='1d', limit=35)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception:
        return None

# 2. FETCH GLOBAL CRYPTO NEWS
@st.cache_data(ttl=300)
def fetch_crypto_news():
    try:
        url = "https://min-api.cryptocompare.com/data/v2/news/?lang=EN"
        response = requests.get(url).json()
        return response['Data'][:5]
    except:
        return []

def get_sreejan_forecaster():
    # PAGE CONFIG (Favicon set to Solana Purple Circle)
    st.set_page_config(
        page_title="Sreejan Range Forecaster", 
        page_icon="🟣", 
        layout="wide"
    )

    st.title("🏦 Sreejan Range Forecaster")
    st.markdown("### Interactive Leveraged Yield Strategy & SOL Forecasting")

    # --- SIDEBAR: INPUTS ---
    st.sidebar.header("💰 Investment Settings")
    capital = st.sidebar.number_input("Enter Investment Amount ($)", min_value=10.0, value=10000.0, step=100.0)
    
    leverage_options = [1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0]
    lev_choice = st.sidebar.select_slider("Select Leverage", options=leverage_options, value=1.5)
    
    st.sidebar.divider()
    st.sidebar.header("🌍 Market Sentiment")
    btc_trend = st.sidebar.selectbox("Bitcoin Trend", ["Bullish 🚀", "Neutral ⚖️", "Bearish 📉"])
    
    # --- DATA ENGINE ---
    df = fetch_sol_market_data()
    
    if df is not None:
        price = df['close'].iloc[-1]
        df['tr'] = df[['high', 'low', 'close']].max(axis=1) - df[['high', 'low', 'close']].min(axis=1)
        atr = df['tr'].rolling(window=14).mean().iloc[-1]

        # 3. FORECASTING LOGIC (Next 5 Days)
        last_date = df['date'].iloc[-1]
        forecast_dates = [last_date + timedelta(days=i) for i in range(1, 6)]
        trend_adj = 1.015 if btc_trend == "Bullish 🚀" else 0.985 if btc_trend == "Bearish 📉" else 1.0
        forecast_prices = [price * (trend_adj ** i) for i in range(1, 6)]
        
        # --- TOP METRICS ---
        position_size = capital * lev_choice
        liq_price = price * (1 - (1 / lev_choice) * 0.45) if lev_choice > 1.0 else 0
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Live SOL Price ($)", f"${price:,.2f}")
        m2.metric("Total Position ($)", f"${position_size:,.2f}", f"{lev_choice}x Leverage")
        m3.metric("Liquidation Price ($)", f"${liq_price:,.2f}" if liq_price > 0 else "SAFE")

        st.divider()

        # --- CHARTING ---
        st.subheader("📊 Price History (Last 5 Days) & Forecast (Next 5 Days)")
        hist_5 = df.tail(5).copy()
        forecast_df = pd.DataFrame({'date': forecast_dates, 'close': forecast_prices, 'type': 'Forecast'})
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=hist_5['date'], y=hist_5['close'], mode='lines+markers', name='History', line=dict(color='#854CE6', width=4)))
        fig.add_trace(go.Scatter(x=forecast_df['date'], y=forecast_df['close'], mode='lines+markers', name='Forecast', line=dict(color='#00FFA3', width=4, dash='dash')))
        fig.update_layout(template="plotly_dark", height=400, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

        t1, t2 = st.columns(2)
        with t1:
            st.write("**Last 5 Days History**")
            st.table(hist_5[['date', 'close']].rename(columns={'date': 'Date', 'close': 'Price ($)'}).set_index('Date'))
        with t2:
            st.write("**Next 5 Days Forecast**")
            st.table(forecast_df[['date', 'close']].rename(columns={'date': 'Date', 'close': 'Price ($)'}).set_index('Date'))

        st.divider()

        # --- RANGE STRATEGIES ---
        st.subheader("🎯 Range Strategies")
        multiplier = 3.2 if btc_trend == "Bearish 📉" else 2.2 if btc_trend == "Bullish 🚀" else 2.7
        rec_low, rec_high = price - (atr * multiplier), price + (atr * multiplier)
        
        st.markdown(f"**Sreejan's Auto-Generated Range: ${rec_low:,.2f} — ${rec_high:,.2f}**")
        
        manual_range = st.slider("Manual Range Selection", min_value=float(price*0.5), max_value=float(price*1.5), value=(float(rec_low), float(rec_high)), step=0.50)
        m_low, m_high = manual_range
        
        # PROFIT MATRIX
        range_width = max(m_high - m_low, 0.01)
        efficiency = (price * 0.35) / range_width
        daily_profit = (position_size * 0.0017) * efficiency
        
        st.markdown(f"**Estimated Daily: ${daily_profit:,.2f}**")
        
        # Time Horizon Metrics (FIXED SYNTAX)
        p1, p2, p3, p4, p5, p6 = st.columns(6)
        p1.metric("1 hr", f"${(daily_profit/24):,.2f}")
        p2.metric("3 hr", f"${(daily_profit/24*3):,.2f}")
        p3.metric("6 hr", f"${(daily_profit/24*6):,.2f}")
        p4.metric("12 hr", f"${(daily_profit/2):,.2f}")
        p5.metric("1 Week", f"${(daily_profit*7):,.2f}")
        p6.metric("1 Month", f"${(daily_profit*30):,.2f}")

        if liq_price > 0 and m_low < liq_price:
            st.error(f"🚨 **DANGER:** Your manual Lower Bound (${m_low:,.2f}) is below Liquidation!")

        # --- NEWS FOOTER ---
        st.divider()
        st.subheader("📰 Global News Scanner")
        news_data = fetch_crypto_news()
        if news_data:
            news_cols = st.columns(len(news_data))
            for i, article in enumerate(news_data):
                with news_cols[i]:
                    st.markdown(f"**[{article['title'][:45]}...]({article['url']})**")
                    st.caption(f"{article['source']}")
    else:
        st.error("Market data error. Check your connection.")

if __name__ == "__main__":
    get_sreejan_forecaster()
