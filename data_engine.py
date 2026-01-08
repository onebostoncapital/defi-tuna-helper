import pandas as pd
import requests
import time

def fetch_base_data(interval="1h", symbol="SOLUSDT"):
    """
    The Heart of the Data Engine. 
    Fetches SOL price data and BTC price for the dashboard.
    """
    base_url = "https://api.binance.com/api/v3/klines"
    btc_url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
    
    try:
        # 1. Fetch BTC Price for the Top Banner
        btc_res = requests.get(btc_url).json()
        btc_price = float(btc_res['price'])
        
        # 2. Fetch SOL Candlestick Data
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': 300 # Enough to calculate a 200 SMA accurately
        }
        
        res = requests.get(base_url, params=params).json()
        
        # 3. Process into a Clean Table
        df = pd.DataFrame(res, columns=[
            'time', 'open', 'high', 'low', 'close', 'volume', 
            'close_time', 'qav', 'num_trades', 'taker_base', 'taker_quote', 'ignore'
        ])
        
        # Convert columns to numbers
        df['close'] = df['close'].astype(float)
        df['open'] = df['open'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        
        # Format the date for the chart
        df['date'] = pd.to_datetime(df['time'], unit='ms')
        
        # 4. Emmanuel Strategy Calculations
        # 20 Exponential Moving Average
        df['20_ema'] = df['close'].ewm(span=20, adjust=False).mean()
        
        # 200 Simple Moving Average
        df['200_sma'] = df['close'].rolling(window=200).mean()
        
        return df, btc_price, None, True
        
    except Exception as e:
        print(f"Data Engine Error: {e}")
        return None, 0, None, False

def get_current_price(symbol="SOLUSDT"):
    """Quick fetch for just the current price."""
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
    try:
        res = requests.get(url).json()
        return float(res['price'])
    except:
        return 0.0
