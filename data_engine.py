import pandas as pd
import yfinance as yf
from datetime import datetime

def fetch_base_data(interval="1h", symbol="SOL-USD"):
    """
    Stable Universal Engine using Yahoo Finance.
    Requires 'yfinance' to be listed in requirements.txt.
    """
    # Map Streamlit intervals to Yahoo intervals
    tf_map = {
        "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m", 
        "1h": "1h", "4h": "1h", "12h": "1d", "1d": "1d"
    }
    y_tf = tf_map.get(interval, "1h")
    
    try:
        # 1. Fetch BTC Price
        btc = yf.Ticker("BTC-USD").history(period="1d")
        btc_p = float(btc['Close'].iloc[-1]) if not btc.empty else 0.0
        
        # 2. Fetch SOL Data
        # Use a 60-day window for enough data to calculate 200 SMA
        period = "7d" if y_tf in ["1m", "5m", "15m", "30m"] else "60d"
        sol_df = yf.download(tickers="SOL-USD", period=period, interval=y_tf, progress=False)
        
        if sol_df.empty:
            return None, btc_p, "Yahoo Finance returned empty data.", False

        # 3. Clean and Format
        df = sol_df.copy()
        # Handle Multi-Index columns if Yahoo returns them
        df.columns = [col[0].lower() if isinstance(col, tuple) else col.lower() for col in df.columns]
        df = df.reset_index()
        df = df.rename(columns={'datetime': 'date', 'index': 'date', 'Date': 'date', 'Datetime': 'date'})
        
        # 4. Strategy Math
        df['20_ema'] = df['close'].ewm(span=20, adjust=False).mean()
        df['200_sma'] = df['close'].rolling(window=200).mean()
        
        return df, btc_p, None, True
        
    except Exception as e:
        return None, 0.0, f"Engine Error: {str(e)}", False
