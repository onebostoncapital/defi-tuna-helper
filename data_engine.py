import pandas as pd
import requests
import streamlit as st

def fetch_base_data(interval="1h", symbol="SOLUSDT"):
    """Fetches market data using private API keys from Streamlit Secrets."""
    base_url = "https://api.binance.com/api/v3/klines"
    btc_url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
    
    # Try to grab the API Key from Secrets
    try:
        api_key = st.secrets["BINANCE_API_KEY"]
        headers = {"X-MBX-APIKEY": api_key}
    except:
        headers = {}

    try:
        # 1. Fetch BTC Price
        btc_res = requests.get(btc_url, headers=headers, timeout=10).json()
        btc_price = float(btc_res.get('price', 0.0))
        
        # 2. Fetch SOL Candlestick Data
        params = {'symbol': symbol, 'interval': interval, 'limit': 300}
        res = requests.get(base_url, params=params, headers=headers, timeout=10).json()
        
        if not isinstance(res, list):
            return None, btc_price, "API Limit Reached - Please check Secrets", False

        # 3. Process Data
        df = pd.DataFrame(res, columns=[
            'time', 'open', 'high', 'low', 'close', 'volume', 
            'close_time', 'qav', 'num_trades', 'taker_base', 'taker_quote', 'ignore'
        ])
        for col in ['open', 'high', 'low', 'close']:
            df[col] = df[col].astype(float)
        
        df['date'] = pd.to_datetime(df['time'], unit='ms')
        df['20_ema'] = df['close'].ewm(span=20, adjust=False).mean()
        df['200_sma'] = df['close'].rolling(window=200).mean()
        
        return df, btc_price, None, True
        
    except Exception as e:
        return None, 0.0, str(e), False
