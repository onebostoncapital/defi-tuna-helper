import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

def fetch_base_data(interval="1h", symbol="SOL-USD"):
    """
    Stable Universal Engine using Yahoo Finance.
    Requires no API keys and works perfectly on the cloud.
    """
    # Map Streamlit intervals to Yahoo intervals
    # Yahoo supports: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
    tf_map = {
        "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m", 
        "1h": "1h", "4h": "1h", "12h": "1d", "1d": "1d"
    }
    y_tf = tf_map.get(interval, "1h")
    
    # Adjust symbol for Yahoo Finance
    y_symbol = "SOL-USD"
    btc_symbol = "BTC-USD"

    try:
        # 1. Fetch BTC Price for the header
        btc_data = yf.Ticker(btc_symbol).history(period="1d")
        btc_price = float(btc_data['Close'].iloc[-1])
        
        # 2. Fetch SOL Candlestick Data
        # For small timeframes (1m-30m), we can only get the last 7 days
        period = "7d" if y_tf in ["1m", "5m", "15m", "30m"] else "60d"
        sol_df = yf.download(tickers=y_symbol, period=period, interval=y_tf, progress=False)
        
        if sol_df.empty:
            return None, btc_price, "No Data Found on Yahoo", False

        # 3. Format Table
        df = sol_df.copy()
        df.columns = [col[0].lower() if isinstance(col, tuple) else col.lower() for col in df.columns]
        df = df.reset_index()
        df = df.rename(columns={'datetime': 'date', 'index': 'date'})
        
        # 4. Strategy Math (EMA 20 & SMA 200)
        df['20_ema'] = df['close'].ewm(span=20, adjust=False).mean()
        df['200_sma'] = df['close'].rolling(window=200).mean()
        
        return df, btc_price, None, True
        
    except Exception as e:
        return None, 0.0, str(e), False
