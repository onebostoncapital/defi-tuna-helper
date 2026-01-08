import pandas as pd
import requests
import time

def fetch_base_data(interval="1h", symbol="SOLUSDT"):
    """
    Fetches market data with a 'Safety Net' for Streamlit Cloud.
    """
    base_url = "https://api.binance.com/api/v3/klines"
    btc_url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
    
    try:
        # 1. Fetch BTC Price with Safety Check
        btc_res = requests.get(btc_url, timeout=10).json()
        
        # Check if 'price' is actually in the answer from Binance
        if 'price' in btc_res:
            btc_price = float(btc_res['price'])
        else:
            btc_price = 0.0 # Safety Net: set to 0 if blocked
        
        # 2. Fetch SOL Candlestick Data
        params = {'symbol': symbol, 'interval': interval, 'limit': 300}
        res = requests.get(base_url, params=params, timeout=10).json()
        
        # If Binance is blocking the cloud server, 'res' might be an error message
        if not isinstance(res, list):
            return None, btc_price, "Binance Cloud Blocked", False

        # 3. Process into Table
        df = pd.DataFrame(res, columns=[
            'time', 'open', 'high', 'low', 'close', 'volume', 
            'close_time', 'qav', 'num_trades', 'taker_base', 'taker_quote', 'ignore'
        ])
        
        for col in ['open', 'high', 'low', 'close']:
            df[col] = df[col].astype(float)
        
        df['date'] = pd.to_datetime(df['time'], unit='ms')
        
        # 4. Strategy Math
        df['20_ema'] = df['close'].ewm(span=20, adjust=False).mean()
        df['200_sma'] = df['close'].rolling(window=200).mean()
        
        return df, btc_price, None, True
        
    except Exception as e:
        # If everything fails, tell the app what the error was
        return None, 0.0, str(e), False
