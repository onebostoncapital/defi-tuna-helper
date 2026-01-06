import ccxt
import pandas as pd
import streamlit as st

# Refresh data every 60 seconds
@st.cache_data(ttl=60)
def fetch_live_sol_data():
    try:
        exchange = ccxt.kraken()
        bars = exchange.fetch_ohlcv('SOL/USD', timeframe='1d', limit=30)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        return df
    except Exception as e:
        return None

def get_sreejan_forecaster():
    st.set_page_config(page_title="Sreejan Range Forecaster", page_icon="📈", layout="wide")
    st.title("🏦 Sreejan Range Forecaster")
    st.markdown("### Interactive Leveraged Yield Strategy for $SOL/USD")

    # --- SIDEBAR: INPUTS ---
    st.sidebar.header("💰 Investment Settings")
    capital = 10000 
    
    # 1. Leverage Slider
    lev_choice = st.sidebar.select_slider(
        "Select Leverage", 
        options=[1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0],
        value=1.5
    )
    
    # 2. Market Sentiment
    st.sidebar.divider()
    st.sidebar.header("🌍 Market Sentiment")
    btc_trend = st.sidebar.selectbox("Bitcoin Trend", ["Bullish 🚀", "Neutral ⚖️", "Bearish 📉"])
    
    # --- DATA & MATH ---
    df = fetch_live_sol_data()
    if df is not None:
        price = df['close'].iloc[-1]
        df['tr'] = df[['high', 'low', 'close']].max(axis=1) - df[['high', 'low', 'close']].min(axis=1)
        atr = df['tr'].rolling(window=14).mean().iloc[-1]

        # Recommended Multiplier Logic
        multiplier = 3.0 if btc_trend == "Bearish 📉" else 2.0 if btc_trend == "Bullish 🚀" else 2.5
        rec_low = price - (atr * multiplier)
        rec_high = price + (atr * multiplier)

        # --- MAIN PANEL: MANUAL RANGE SLIDER ---
        st.subheader("🛠️ Manual Range Adjustment")
        st.write("Adjust the sliders below to set your own custom price boundaries and see how it affects profit.")
        
        # Manual Price Slider (Allows +/- 50% of current price)
        min_p = float(price * 0.5)
        max_p = float(price * 1.5)
        manual_range = st.slider(
            "Select Manual Price Range ($)",
            min_value=min_p,
            max_value=max_p,
            value=(float(rec_low), float(rec_high)),
            step=0.50,
            format="$%.2f"
        )
        
        m_low, m_high = manual_range
        range_width = m_high - m_low

        # --- CALCULATIONS ---
        position_size = capital * lev_choice
        # Fee logic: Tighter ranges earn more fees. 
        # Base assumption: 0.20% daily on a standard ATR range.
        efficiency_factor = (price * 0.4) / range_width # Tighter = higher factor
        daily_profit = (position_size * 0.0018) * efficiency_factor
        weekly_profit = daily_profit * 7
        
        # Liquidation
        liq_price = price * (1 - (1 / lev_choice) * 0.45) if lev_choice > 1.0 else 0

        # --- DISPLAY RESULTS ---
        st.divider()
        col1, col2, col3 = st.columns(3)
        col1.metric("Live SOL Price", f"${price:,.2f}")
        col2.metric("Total Position", f"${position_size:,.0f}", f"{lev_choice}x Leverage")
        col3.metric("Liq. Price", f"${liq_price:,.2f}" if liq_price > 0 else "SAFE")

        st.success(f"### 📈 Estimated Weekly Profit: ${weekly_profit:,.2f}")
        st.write(f"Estimated Daily: ${daily_profit:,.2f}")

        # COMPARE SECTION
        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### ✅ Sreejan Recommended")
            st.write(f"Lower: **${rec_low:,.2f}**")
            st.write(f"Upper: **${rec_high:,.2f}**")
        with c2:
            st.markdown("#### ✍️ Your Manual Selection")
            st.write(f"Lower: **${m_low:,.2f}**")
            st.write(f"Upper: **${m_high:,.2f}**")
            
        if liq_price > 0 and m_low < liq_price:
            st.error(f"🚨 **WARNING:** Your manual Lower Bound (${m_low:,.2f}) is below Liquidation (${liq_price:,.2f})!")

    else:
        st.error("Connection lost. Please refresh the page.")

if __name__ == "__main__":
    get_sreejan_forecaster()
