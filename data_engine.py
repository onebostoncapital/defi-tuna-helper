import pandas as pd
import yfinance as yf

def fetch_base_data(interval="1h", symbol="SOL-USD"):
    """Stable engine to prevent Binance blocks."""
    tf_map = {
        "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m", 
        "1h": "1h", "4h": "1h", "12h": "1d", "1d": "1d"
    }
    y_tf = tf_map.get(interval, "1h")
    
    try:
        btc = yf.Ticker("BTC-USD").history(period="1d")
        btc_p = float(btc['Close'].iloc[-1]) if not btc.empty else 0.0
        
        period = "7d" if y_tf in ["1m", "5m", "15m", "30m"] else "60d"
        sol_df = yf.download(tickers="SOL-USD", period=period, interval=y_tf, progress=False)
        
        if sol_df.empty: return None, btc_p, "Data Offline", False

        df = sol_df.copy()
        df.columns = [col[0].lower() if isinstance(col, tuple) else col.lower() for col in df.columns]
        df = df.reset_index().rename(columns={'Date': 'date', 'Datetime': 'date'})
        
        df['20_ema'] = df['close'].ewm(span=20, adjust=False).mean()
        df['200_sma'] = df['close'].rolling(window=200).mean()
        
        return df, btc_p, None, True
    except Exception as e:
        return None, 0.0, str(e), False
