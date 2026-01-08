import pandas as pd
import requests
import streamlit as st

def fetch_base_data(interval="60", symbol="SOLUSDT"):
    """
    Bulletproof Data Engine using Bybit API for Cloud Stability.
    interval mapping: 1, 5, 15, 30, 60, 240, 720, D
    """
    # Map Streamlit TFs to Bybit TFs
    tf_map = {"1m":"1", "5m":"5", "15m":"15", "30m":"30", "1h":"60", "4h":"240", "12h":"720", "1d":"D"}
    bybit_tf = tf_map.get(interval, "60")
    
    base_url = "https://api.bybit.com/v5/market/kline"
    btc_url = "https://api.bybit.com/v5/market/tickers?category=linear&symbol=BTCUSDT"

    try:
        # 1. Fetch BTC Price
        btc_res = requests.get(btc_url, timeout=10).json()
        btc_price = float(btc_res['result']['list'][0]['lastPrice'])
        
        # 2. Fetch SOL Data
        params = {
            'category': 'linear',
            'symbol': symbol,
            'interval': bybit_tf,
            'limit': 200
        }
        res = requests.get(base_url, params=params, timeout=10).json()
        
        if res['retMsg'] != 'OK':
            return None, btc_price, f"Bybit Error: {res['retMsg']}", False

        # 3. Process into Table
        # Bybit format: [startTime, openPrice, highPrice, lowPrice, closePrice, volume, turnover]
        raw_data = res['result']['list']
        df = pd.DataFrame(raw_data, columns=['time', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
        
        # Bybit returns data newest to oldest, we need oldest to newest for EMA
        df = df.iloc[::-1].reset_index(drop=True)
        
        for col in ['open', 'high', 'low', 'close']:
            df[col] = df[col].astype(float)
        
        df['date'] = pd.to_datetime(df['time'].astype(float), unit='ms')
        
        # 4. Strategy Math
        df['20_ema'] = df['close'].ewm(span=20, adjust=False).mean()
        df['200_sma'] = df['close'].rolling(window=200).mean()
        
        return df, btc_price, None, True
        
    except Exception as e:
        return None, 0.0, f"Connection Failed: {str(e)}", False
