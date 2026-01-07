import ccxt
import pandas as pd
import streamlit as st
import requests
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. CORE DATA ENGINE (Prices, Volume, Sentiment, Funding)
@st.cache_data(ttl=15)
def fetch_market_intelligence():
    try:
        exchange = ccxt.kraken()
        # Fetch SOL Data
        sol_bars = exchange.fetch_ohlcv('SOL/USD', timeframe='1d', limit=40)
        sol_df = pd.DataFrame(sol_bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        sol_df['date'] = pd.to_datetime(sol_df['timestamp'], unit='ms')
        sol_vol_24h = sol_df['volume'].iloc[-1] * sol_df['close'].iloc[-1]
        
        # Fetch BTC for Banner
        btc_ticker = exchange.fetch_ticker('BTC/USD')
        btc_price = btc_ticker['last']
        
        # Fetch Fear & Greed Index
        fng_res = requests.get("https://api.alternative.me/fng/").json()
        fng_value = int(fng_res['data'][0]['value'])
        fng_label = fng_res['data'][0]['value_classification']
        
        return sol_df, btc_price, sol_vol_24h, fng_value, fng_label
    except Exception:
        return None, None, None, None, None

def get_sreejan_forecaster():
    st.set_page_config(page_title="Sreejan Range Forecaster", page_icon="🟣", layout="wide")

    sol_df, btc_price, sol_vol_24h, fng_val, fng_lab = fetch_market_intelligence()

    # --- 1. TOP BANNER: MARKET SIGNALS ---
    if sol_df is not None:
        sol_price = sol_df['close'].iloc[-1]
        st.markdown(f"""
            <div style="background-color: #111; padding: 15px; border-radius: 12px; border: 1px solid #333; display: flex; justify-content: space-around; align-items: center;">
                <div style="text-align: center;"><p style="margin:0; color:#888; font-size:12px;">BITCOIN</p><b style="font-size:18px; color:#FF9900;">${btc_price:,.2f}</b></div>
                <div style="text-align: center;"><p style="margin:0; color:#888; font-size:12px;">SOLANA</p><b style="font-size:18px; color:#854CE6;">${sol_price:,.2f}</b></div>
                <div style="text-align: center;"><p style="margin:0; color:#888; font-size:12px;">SOL 24H VOLUME</p><b style="font-size:18px; color:#00FFA3;">${sol_vol_24h/1e9:.2f}B</b></div>
                <div style="text-align: center;"><p style="margin:0; color:#888; font-size:12px;">FEAR & GREED</p><b style="font-size:18px; color:#FFF;">{fng_val} ({fng_lab})</b></div>
            </div>
        """, unsafe_allow_html=True)

    # --- SIDEBAR: GLOBAL SETTINGS (LOCKED) ---
    st.sidebar.header("💰 Investment Settings")
    capital = st.sidebar.number_input("Capital Amount ($)", min_value=10.0, value=10000.0, step=100.0)
    lev_options = [1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0]
    lev_choice = st.sidebar.select_slider("Select Leverage", options=lev_options, value=1.5)
    btc_trend = st.sidebar.selectbox("Market Sentiment", ["Bullish 🚀", "Neutral ⚖️", "Bearish 📉"])
    
    if st.sidebar.button("🔄 Force Data Refresh"):
        st.cache_data.clear()
        st.rerun()

    if sol_df is not None:
        price = sol_df['close'].iloc[-1]
        last_date = sol_df['date'].iloc[-1]
        
        # Indicator Math
        sol_df['tr'] = sol_df[['high', 'low', 'close']].max(axis=1) - sol_df[['high', 'low', 'close']].min(axis=1)
        atr = sol_df['tr'].rolling(window=14).mean().iloc[-1]
        liq_price = price * (1 - (1 / lev_choice) * 0.45) if lev_choice > 1.0 else 0
        
        # Forecast
        forecast_dates = [last_date + timedelta(days=i) for i in range(1, 6)]
        bias = 0.015 if btc_trend == "Bullish 🚀" else -0.015 if btc_trend == "Bearish 📉" else 0
        forecast_prices = [price * ((1 + bias) ** i) for i in range(1, 6)]

        # --- PERP TRADING INDICATIVE (NEW CORE ELEMENT) ---
        st.divider()
        st.subheader("⚡ Perpetual Trading Indicative")
        # Logic: If price > 20d EMA and Fear/Greed is rising, favor Long
        ema_20 = sol_df['close'].tail(20).mean()
        signal = "LONG 🟢" if price > ema_20 and fng_val > 40 else "SHORT 🔴" if price < ema_20 else "NEUTRAL ⚪"
        confidence = "HIGH" if abs(price - ema_20) > (atr * 0.5) else "MEDIUM"
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.info(f"**Action Bias:** {signal}")
        with c2:
            st.info(f"**Confidence:** {confidence}")
        with c3:
            st.info(f"**Pivot Point:** ${ema_20:,.2f}")

        # --- CHART: HEATMAP + FORECAST (LOCKED) ---
        st.subheader("📊 Strategic Price Horizon")
        fig = go.Figure()
        heatmap_range = np.linspace(price - (atr*4), price + (atr*4), 50)
        for i in range(len(heatmap_range)-1):
            opacity = 0.12 * np.exp(-abs(heatmap_range[i] - price) / (atr * 2))
            fig.add_hrect(y0=heatmap_range[i], y1=heatmap_range[i+1], fillcolor="#854CE6", opacity=opacity, line_width=0)

        fig.add_trace(go.Scatter(x=sol_df.tail(10)['date'], y=sol_df.tail(10)['close'], name='History', line=dict(color='#854CE6', width=4)))
        fig.add_trace(go.Scatter(x=forecast_dates, y=forecast_prices, name='Forecast', line=dict(color='#00FFA3', dash='dash', width=3)))
        fig.add_vline(x=last_date, line_width=2, line_dash="solid", line_color="white")
        fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0, r=0, t=10, b=0), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

        # --- CORE: RANGE CONFIGURATOR (LOCKED) ---
        st.subheader("🎯 Liquidity Range Settings")
        mult = 3.2 if btc_trend == "Bearish 📉" else 2.2 if btc_trend == "Bullish 🚀" else 2.7
        auto_low, auto_high = price - (atr * mult), price + (atr * mult)
        st.markdown(f"### **Recommended Range: ${auto_low:,.2f} — ${auto_high:,.2f}**")
        
        manual_range = st.slider(
            "Tune Manual Execution Range",
            min_value=float(price * 0.4), max_value=float(price * 1.6),
            value=(float(auto_low), float(auto_high)), step=0.10, format="$%.2f"
        )
        m_low, m_high = manual_range

        # --- YIELD MATRIX (LOCKED: 7 HORIZONS) ---
        daily_profit = (capital * lev_choice * 0.0017) * ((price * 0.35) / max(m_high - m_low, 0.01))
        st.markdown(f"#### 💰 Yield Matrix (Daily: ${daily_profit:,.2f})")
        p_cols = st.columns(7)
        intervals = {"1 HR": 1/24, "3 HR": 3/24, "6 HR": 6/24, "12 HR": 0.5, "1 Day": 1, "1 Week": 7, "1 Month": 30}
        for i, (label, val) in enumerate(intervals.items()):
            p_cols[i].metric(label, f"${(daily_profit * val):,.2f}")

        # --- DATA TABLES ---
        st.divider()
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            st.write("**History**")
            st.table(sol_df[['date', 'close']].tail(5).set_index('date'))
        with col_t2:
            st.write("**Forecast**")
            st.table(pd.DataFrame({'Date': forecast_dates, 'Price': forecast_prices}).set_index('Date'))

    else:
        st.error("Market data unavailable.")

if __name__ == "__main__":
    get_sreejan_forecaster()
