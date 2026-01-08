import pandas as pd
import requests
import time

def fetch_base_data(interval="1h", symbol="SOLUSDT"):
    """
    Fetches market data with error handling to prevent blank screens.
    """
    base_url = "https://api.binance.com/api/v3/klines"
    btc_url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
    
    try:
        # 1. Fetch BTC Price
        btc_res = requests.get(btc_url, timeout=5).json()
        btc_price = float(btc_res['price'])
        
        # 2. Fetch SOL Candlestick Data
        params = {'symbol': symbol, 'interval': interval, 'limit': 300}
        res = requests.get(base_url, params=params, timeout=5).json()
        
        if not res or 'code' in res:
            return None, 0, None, False

        # 3. Process Data
        df = pd.DataFrame(res, columns=[
            'time', 'open', 'high', 'low', 'close', 'volume', 
            'close_time', 'qav', 'num_trades', 'taker_base', 'taker_quote', 'ignore'
        ])
        
        for col in ['open', 'high', 'low', 'close']:
            df[col] = df[col].astype(float)
        
        df['date'] = pd.to_datetime(df['time'], unit='ms')
        
        # 4. Indicators
        df['20_ema'] = df['close'].ewm(span=20, adjust=False).mean()
        df['200_sma'] = df['close'].rolling(window=200).mean()
        
        return df, btc_price, None, True
        
    except Exception as e:
        print(f"Data Engine Error: {e}")
        return None, 0, f"Error: {e}", False
