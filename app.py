import ccxt
import pandas as pd
import streamlit as st

# This function ensures data is refreshed every 60 seconds
@st.cache_data(ttl=60)
def fetch_live_sol_data():
    try:
        exchange = ccxt.kraken()
        # Fetching fresh Daily (1d) data for SOL/USD
        bars = exchange.fetch_ohlcv('SOL/USD', timeframe='1d', limit=30)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        return df
    except Exception as e:
        return None

def get_sreejan_forecaster():
    st.set_page_config(page_title="Sreejan Range Forecaster", page_icon="📈", layout="wide")
    st.title("🏦 Sreejan Range Forecaster")
    st.markdown("### Interactive Leveraged Yield Strategy for SOL/USD")

    # --- SIDEBAR SETTINGS ---
    st.sidebar.header("💰 Investment Settings")
    capital = 10000  # Fixed $10,000 Capital
    st.sidebar.write(f"Initial Capital: **${capital:,.0f}**")
    
    # LEVERAGE SLIDER
    lev_choice = st.sidebar.select_slider(
        "Select Leverage", 
        options=[1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0],
        value=1.5
    )
    
    # NEWS & SENTIMENT
    st.sidebar.divider()
    st.sidebar.header("🌍 Market Sentiment")
    btc_trend = st.sidebar.selectbox("Bitcoin Trend", ["Bullish 🚀", "Neutral ⚖️", "Bearish 📉"])
    geo_news = st.sidebar.selectbox("Global News", ["Positive", "Uncertain", "Negative"])

    # --- CALCULATION LOGIC ---
    df = fetch_live_sol_data()
    
    if df is not None:
        # ATR Volatility Calculation
        df['tr'] = df[['high', 'low', 'close']].max(axis=1) - df[['high', 'low', 'close']].min(axis=1)
        atr = df['tr'].rolling(window=14).mean().iloc[-1]
        price = df['close'].iloc[-1]
        
        # Predictive Multiplier based on News
        multiplier = 2.5
        if btc_trend == "Bearish 📉" or geo_news == "Negative":
            multiplier = 3.5  # Wider range for safety
            st.sidebar.warning("Model: Bearish news detected. Range widened.")
        elif btc_trend == "Bullish 🚀":
            multiplier = 2.0  # Tighter range for more fees
            st.sidebar.success("Model: Bullish trend detected. Range tightened.")

        # Range Bounds
        low_bound = price - (atr * multiplier)
        high_bound = price + (atr * multiplier)
        
        # Liquidation Math (Estimated for SOL at specific leverage)
        # Formula: Price * (1 - (1/Leverage) * Margin_Buffer)
        if lev_choice > 1.0:
            liq_price = price * (1 - (1 / lev_choice) * 0.45) 
        else:
            liq_price = 0
            
        # Profit Projections (Estimated 0.15% base daily yield on position size)
        position_size = capital * lev_choice
        daily_profit = position_size * 0.0018  # 0.18% average daily fee
        weekly_profit = daily_profit * 7

        # --- MAIN DASHBOARD DISPLAY ---
        col1, col2, col3 = st.columns(3)
        col1.metric("Live SOL Price", f"${price:,.2f}")
        col2.metric("Total Position", f"${position_size:,.2f}", f"{lev_choice}x Leverage")
        col3.metric("Liq. Price", f"${liq_price:,.2f}" if liq_price > 0 else "SAFE")

        st.divider()

        # PROFIT SECTION
        st.subheader("📊 Projected Earnings (Fees)")
        p_col1, p_col2 = st.columns(2)
        p_col1.success(f"**Estimated Daily Profit:** ${daily_profit:,.2f}")
        p_col2.success(f"**Estimated Weekly Profit:** ${weekly_profit:,.2f}")

        # RANGE RECOMMENDATION
        st.subheader("🎯 Recommended Range Settings")
        st.info(f"Set your DefiTuna range to: **${low_bound:,.2f} — ${high_bound:,.2f}**")
        
        # SAFETY ALERTS
        if liq_price > 0 and low_bound < liq_price:
            st.error(f"🚨 **DANGER:** Your lower range (${low_bound:,.2f}) is below your Liquidation Price (${liq_price:,.2f}). If the price hits your lower bound, you are at extreme risk. Please lower your leverage or widen the range.")
        elif liq_price > 0:
            st.warning(f"🛡️ **Safety Buffer:** You have a ${low_bound - liq_price:,.2f} cushion between your range floor and liquidation.")
            
    else:
        st.error("Failed to connect to exchange. Please check your internet or refresh the page.")

if __name__ == "__main__":
    get_sreejan_forecaster()
