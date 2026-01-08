import pandas as pd
import yfinance as yf
import streamlit as st

@st.cache_data(ttl=30)
def fetch_base_data(interval="1h", symbol="SOL-USD"):
    tf_map = {"1m":"1m", "5m":"5m", "15m":"15m", "30m":"30m", "1h":"1h", "4h":"1h", "12h":"1d", "1d":"1d"}
    y_tf = tf_map.get(interval, "1h")
    try:
        btc = yf.Ticker("BTC-USD").history(period="1d")
        btc_p = float(btc['Close'].iloc[-1]) if not btc.empty else 0.0
        
        # Pull enough data for the 200 SMA
        period = "7d" if y_tf in ["1m", "5m", "15m", "30m"] else "max"
        df = yf.download(tickers=symbol, period=period, interval=y_tf, progress=False)
        
        if df.empty: return None, btc_p, "Market Offline", False
        
        df.columns = [col[0].lower() if isinstance(col, tuple) else col.lower() for col in df.columns]
        df = df.reset_index().rename(columns={'Date': 'date', 'Datetime': 'date'})
        
        # Indicators for Consensus Matrix
        df['20_ema'] = df['close'].ewm(span=20, adjust=False).mean()
        df['200_sma'] = df['close'].rolling(window=200).mean()
        
        return df, btc_p, None, True
    except:
        return None, 0.0, "API Error", False
