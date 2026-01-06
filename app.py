import ccxt
import pandas as pd
import streamlit as st
import requests

# 1. FETCH LIVE MARKET DATA (Refreshes every 60s)
@st.cache_data(ttl=60)
def fetch_live_sol_data():
    try:
        exchange = ccxt.kraken()
        bars = exchange.fetch_ohlcv('SOL/USD', timeframe='1d', limit=30)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        return df
    except Exception as e:
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
    # PAGE CONFIG (Favicon set to Solana Emoji/Symbol and Title)
    st.set_page_config(
        page_title="Sreejan Range Forecaster", 
        page_icon="🟣", # Solana theme icon
        layout="wide"
    )

    st.title("🏦 Sreejan Range Forecaster")
    st.markdown("### Interactive Leveraged Yield Strategy for $SOL/USD")

    # --- SIDEBAR: INPUTS & SETTINGS ---
    st.sidebar.header("💰 Investment Settings")
    
    # FREE FORM MANUAL INPUT FOR CAPITAL
    capital = st.sidebar.number_input(
        "Enter Investment Amount ($)", 
        min_value=10.0, 
        max_value=1000000.0, 
        value=10000.0, 
        step=100.0
    )
    
    # LEVERAGE DOT SLIDER (1.0 to 2.0 with discrete dots)
    leverage_options = [1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0]
    lev_choice = st.sidebar.select_slider(
        "Select Leverage", 
        options=leverage_options,
        value=1.5
    )
    
    st.sidebar.divider()
    st.sidebar.header("🌍 Market Sentiment")
    btc_trend = st.sidebar.selectbox("Bitcoin Trend", ["Bullish 🚀", "Neutral ⚖️", "Bearish 📉"])
    
    # --- DATA ENGINE ---
    df = fetch_live_sol_data()
    
    if df is not None:
        price = df['close'].iloc[-1]
        df['tr'] = df[['high', 'low', 'close']].max(axis=1) - df[['high', 'low', 'close']].min(axis=1)
        atr = df['tr'].rolling(window=14).mean().iloc[-1]

        # AUTO GENERATED RANGE LOGIC
        multiplier = 3.2 if btc_trend == "Bearish 📉" else 2.2 if btc_trend == "Bullish 🚀" else 2.7
        rec_low = price - (atr * multiplier)
        rec_high = price + (atr * multiplier)

        # --- TOP METRICS ---
        position_size = capital * lev_choice
        liq_price = price * (1 - (1 / lev_choice) * 0.45) if lev_choice > 1.0 else 0
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Live SOL Price ($)", f"${price:,.2f}")
        m2.metric("Total Position ($)", f"${position_size:,.2f}", f"{lev_choice}x Leverage")
        m3.metric("Liquidation Price ($)", f"${liq_price:,.2f}" if liq_price > 0 else "SAFE")

        st.divider()

        # --- CALCULATION CENTER ---
        st.subheader("🎯 Range Strategies")
        
        # DISPLAY BOLD AUTO RANGE ABOVE MANUAL
        st.markdown(f"**Sreejan's Auto-Generated Range: ${rec_low:,.2f} — ${rec_high:,.2f}**")
        
        # MANUAL RANGE SLIDER
        min_val = float(price * 0.6)
        max_val = float(price * 1.4)
        manual_range = st.slider(
            "Manual Range Selection (Adjust for Profit Impact)",
            min_value=min_val,
            max_value=max_val,
            value=(float(rec_low), float(rec_high)),
            step=0.50,
            format="$%.2f"
        )
        
        m_low, m_high = manual_range
        range_width = m_high - m_low
        
        # DYNAMIC PROFIT CALCULATION (Fee efficiency logic)
        efficiency = (price * 0.35) / range_width
        daily_profit = (position_size * 0.0017) * efficiency
        
        # --- PROFIT TIME HORIZONS ---
        st.subheader("📈 Profit Projections")
        
        # Bold Daily Profit as requested
        st.markdown(f"**Estimated Daily: ${daily_profit:,.2f}**")
        
        p1, p2, p3 = st.columns(3)
        p1.write(f"1 Hour: **${daily_profit/24:,.4f}**")
        p1.write(f"3 Hour: **${(daily_profit/24)*3:,.4f}**")
        p2.write(f"6 Hour: **${(daily_profit/24)*6:,.4f}**")
        p2.write(f"12 Hour: **${(daily_profit/24)*12:,.4f}**")
        p3.write(f"1 Week: **${daily_profit*7:,.2f}**")
        p3.write(f"1 Month: **${daily_profit*30:,.2f}**")

        # SAFETY WARNING
        if liq_price > 0 and m_low < liq_price:
            st.error(f"🚨 **DANGER:** Your manual Lower Bound (${m_low:,.2f}) is below Liquidation!")

        # --- NEWS AT THE BOTTOM ---
        st.divider()
        st.subheader("📰 Global News Scanner")
        news_data = fetch_crypto_news()
        if news_data:
            cols = st.columns(len(news_data))
            for i, article in enumerate(news_data):
                with cols[i]:
                    st.markdown(f"**[{article['title'][:50]}...]({article['url']})**")
                    st.caption(f"{article['source']}")
        else:
            st.write("No live news found.")

    else:
        st.error("Connection lost. Please reload.")

if __name__ == "__main__":
    get_sreejan_forecaster()
