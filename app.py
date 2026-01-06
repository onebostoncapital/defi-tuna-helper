import ccxt
import pandas as pd
import streamlit as st

def get_sreejan_forecaster():
    # SETUP WEB INTERFACE
    st.set_page_config(page_title="Sreejan Range Forecaster", page_icon="📈")
    st.title("🏦 Sreejan Range Forecaster")
    st.markdown("### Optimized for DefiTuna SOL/USD Liquidity")

    # USER INPUTS
    capital = 10000 # Your $10,000 Capital
    st.sidebar.header("Strategy Settings")
    lev_choice = st.sidebar.select_slider("Select Leverage", options=[1.0, 1.5, 2.0])
    
    # PREDICTIVE NEWS SCANNER (Manual Inputs for Simulation)
    st.sidebar.divider()
    st.sidebar.header("🌍 Global News & BTC Sentiment")
    btc_trend = st.sidebar.selectbox("Bitcoin Trend", ["Bullish 🚀", "Neutral ⚖️", "Bearish 📉"])
    geo_news = st.sidebar.selectbox("Geo-Political News", ["Positive", "Uncertain", "Negative"])

    if st.button('Run Sreejan Forecast'):
        try:
            # 1. FETCH DATA
            exchange = ccxt.kraken()
            bars = exchange.fetch_ohlcv('SOL/USD', timeframe='1d', limit=30)
            df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # 2. ATR LOGIC (Core Volatility)
            df['tr'] = df[['high', 'low', 'close']].max(axis=1) - df[['high', 'low', 'close']].min(axis=1)
            atr = df['tr'].rolling(window=14).mean().iloc[-1]
            price = df['close'].iloc[-1]
            
            # 3. PREDICTIVE MODEL ADJUSTMENTS
            # The model adjusts the range 'multiplier' based on news sentiment
            multiplier = 2.5
            sentiment_msg = "Market condition is stable."
            
            if btc_trend == "Bearish 📉" or geo_news == "Negative":
                multiplier = 3.5 # Widens range for safety
                sentiment_msg = "⚠️ High Risk: Negative news detected. Widening range for safety."
            elif btc_trend == "Bullish 🚀":
                multiplier = 2.0 # Tightens range for max fees
                sentiment_msg = "✅ Bullish: BTC is pumping. Tightening range for maximum $ fees."

            # 4. RANGE & PROFIT CALCULATIONS
            low_bound = price - (atr * multiplier)
            high_bound = price + (atr * multiplier)
            
            # Liquidation Price (Approx 35-40% drop for 2x, more for 1.5x)
            if lev_choice == 2.0:
                liq_price = price * 0.715
            elif lev_choice == 1.5:
                liq_price = price * 0.380
            else:
                liq_price = 0 # 1x has no liquidation
            
            # Daily Fee Estimate (based on position size)
            daily_profit = (capital * lev_choice) * 0.0018 # Estimated 0.18% fee yield

            # --- DISPLAY RESULTS ---
            st.divider()
            st.info(f"**Forecaster Note:** {sentiment_msg}")
            
            col1, col2, col3 = st.columns(3)
            col1.metric("SOL Price", f"${price:,.2f}")
            col2.metric("Position Size", f"${capital * lev_choice:,.0f}")
            col3.metric("Est. Daily Profit", f"${daily_profit:,.2f}")

            st.header("🎯 Recommended Settings")
            st.success(f"**Range Lower:** ${low_bound:,.2f} | **Range Upper:** ${high_bound:,.2f}")
            
            if liq_price > 0:
                st.error(f"🔴 **Liquidation Warning:** ${liq_price:,.2f}")
                if low_bound < liq_price:
                    st.write("❌ **DANGER:** Your lower range is below liquidation. REDUCE LEVERAGE!")
            else:
                st.balloons()
                st.write("🟢 **Safe Position:** 1x Leverage has no liquidation price.")

        except Exception as e:
            st.error(f"Connection error: {e}")

if __name__ == "__main__":
    get_sreejan_forecaster()
