import ccxt
import pandas as pd
import streamlit as st
import requests
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. FETCH LIVE MARKET DATA
# Cache reduced to 10 seconds for high-frequency updates
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

def get_sreejan_forecaster():
    st.set_page_config(page_title="Sreejan Range Forecaster", page_icon="🟣", layout="wide")

    # --- SIDEBAR: INPUTS ---
    st.sidebar.header("💰 Investment Settings")
    if st.sidebar.button("🔄 Force Price Update"):
        st.cache_data.clear()
        st.rerun()

    capital = st.sidebar.number_input("Investment Amount ($)", min_value=10.0, value=10000.0, step=100.0)
    lev_choice = st.sidebar.select_slider("Select Leverage", options=[1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0], value=1.5)
    
    st.sidebar.divider()
    st.sidebar.header("🌍 Market Sentiment")
    btc_trend = st.sidebar.selectbox("Bitcoin Trend", ["Bullish 🚀", "Neutral ⚖️", "Bearish 📉"])
    
    # --- DATA ENGINE ---
    df = fetch_sol_market_data()
    
    if df is not None:
        current_price = df['close'].iloc[-1]
        last_date = df['date'].iloc[-1]
        
        # Calculate Volatility (making the forecast react to price drops)
        df['returns'] = df['close'].pct_change()
        volatility = df['returns'].tail(14).std()
        
        # 3. DYNAMIC FORECAST LOGIC
        forecast_dates = [last_date + timedelta(days=i) for i in range(1, 6)]
        bias = 0.012 if btc_trend == "Bullish 🚀" else -0.012 if btc_trend == "Bearish 📉" else 0
        
        forecast_prices = []
        temp_p = current_price
        for i in range(1, 6):
            # If price went down, volatility increases, creating a steeper reaction
            temp_p = temp_p * (1 + bias + (volatility * np.random.randn() * 0.2))
            forecast_prices.append(temp_p)
        
        # --- TOP METRICS ---
        st.title("🏦 Sreejan Range Forecaster")
        m1, m2, m3 = st.columns(3)
        price_diff = current_price - df['close'].iloc[-2]
        m1.metric("Live SOL Price", f"${current_price:,.2f}", f"{price_diff:+.2f}")
        m2.metric("Total Position", f"${(capital * lev_choice):,.2f}", f"{lev_choice}x")
        
        # --- REACTIVE CHART WITH VERTICAL LINE ---
        st.subheader("📊 Price Action & Forecast Horizon")
        hist_5 = df.tail(10).copy() # Showing 10 days history for context
        forecast_df = pd.DataFrame({'date': forecast_dates, 'close': forecast_prices})

        fig = go.Figure()

        # 1. Historical Data
        fig.add_trace(go.Scatter(x=hist_5['date'], y=hist_5['close'], name='History', line=dict(color='#854CE6', width=4)))
        
        # 2. Forecast Data
        fig.add_trace(go.Scatter(x=forecast_df['date'], y=forecast_df['close'], name='Forecast', line=dict(color='#00FFA3', width=4, dash='dash')))

        # 3. CURRENT PRICE VERTICAL LINE
        fig.add_vline(x=last_date, line_width=2, line_dash="solid", line_color="white")
        
        # 4. CURRENT PRICE DOT & LABEL
        fig.add_trace(go.Scatter(
            x=[last_date], y=[current_price],
            mode='markers+text',
            name='Current Price',
            text=[f"  ${current_price:,.2f}"],
            textposition="middle right",
            marker=dict(color='white', size=12, line=dict(color='#854CE6', width=2))
        ))

        fig.update_layout(template="plotly_dark", height=450, margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

        # Side-by-Side Tables
        t1, t2 = st.columns(2)
        with t1:
            st.write("**Recent History**")
            st.table(hist_5[['date', 'close']].tail(5).rename(columns={'date': 'Date', 'close': 'Price ($)'}).set_index('Date'))
        with t2:
            st.write("**Smart Forecast**")
            st.table(forecast_df.rename(columns={'date': 'Date', 'close': 'Price ($)'}).set_index('Date'))

        st.divider()

        # --- PROFIT CALCULATIONS ---
        daily_profit = (capital * lev_choice) * 0.0017
        st.markdown(f"### 💰 Yield Projections (Daily: ${daily_profit:,.2f})")
        p_cols = st.columns(4)
        p_cols[0].metric("1 Hour", f"${(daily_profit/24):,.2f}")
        p_cols[1].metric("12 Hours", f"${(daily_profit/2):,.2f}")
        p_cols[2].metric("1 Week", f"${(daily_profit*7):,.2f}")
        p_cols[3].metric("1 Month", f"${(daily_profit*30):,.2f}")

    else:
        st.error("Connection lost. Please click 'Force Price Update' in the sidebar.")

if __name__ == "__main__":
    get_sreejan_forecaster()
