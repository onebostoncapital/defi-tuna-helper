import ccxt
import pandas as pd
import streamlit as st

def get_sol_range():
    # Setup Web Interface
    st.set_page_config(page_title="SOL Range Helper", page_icon="📈")
    st.title("DefiTuna SOL/USD Range Helper")
    st.markdown("This tool calculates the best range for **2x Leverage** based on live market volatility.")
    
    # Add a button so the user can refresh the data
    if st.button('Calculate Best Range Now'):
        exchanges_to_try = ['kraken', 'kucoin', 'binance']
        
        for ex_id in exchanges_to_try:
            try:
                with st.spinner(f'Connecting to {ex_id}...'):
                    exchange = getattr(ccxt, ex_id)()
                    symbol = 'SOL/USD' if ex_id == 'kraken' else 'SOL/USDT'
                    
                    # Fetch data
                    bars = exchange.fetch_ohlcv(symbol, timeframe='1d', limit=30)
                    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    
                    # ATR Logic
                    df['h-l'] = df['high'] - df['low']
                    df['h-pc'] = abs(df['high'] - df['close'].shift(1))
                    df['l-pc'] = abs(df['low'] - df['close'].shift(1))
                    df['tr'] = df[['h-l', 'h-pc', 'l-pc']].max(axis=1)
                    atr = df['tr'].rolling(window=14).mean().iloc[-1]
                    current_price = df['close'].iloc[-1]
                    
                    # Range Logic
                    multiplier = 2.5 
                    low_bound = current_price - (atr * multiplier)
                    high_bound = current_price + (atr * multiplier)
                    
                    # --- WEB DISPLAY ---
                    st.success(f"Data retrieved successfully from {ex_id}")
                    
                    col1, col2 = st.columns(2)
                    col1.metric("Current SOL Price", f"${current_price:,.2f}")
                    col2.metric("Daily Volatility (ATR)", f"${atr:,.2f}")
                    
                    st.header("🎯 Recommended Range")
                    st.info(f"**Lower Bound:** ${low_bound:,.2f}  \n**Upper Bound:** ${high_bound:,.2f}")
                    
                    st.warning(f"⚠️ **Safety Check:** At 2x leverage, your liquidation point is approx **${current_price * 0.70:,.2f}**. Ensure your range stays above this.")
                    
                    with st.expander("View Raw Market Data"):
                        st.write(df.tail(5))
                    
                    return # Exit loop if successful
                    
            except Exception as e:
                st.error(f"{ex_id} failed: {e}")
                continue
    else:
        st.write("Click the button above to pull live market data.")

if __name__ == "__main__":
    get_sol_range()
