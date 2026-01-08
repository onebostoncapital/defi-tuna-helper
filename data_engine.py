import ccxt
import pandas as pd
import numpy as np

def fetch_base_data(timeframe='1d'):
    try:
        exchange = ccxt.kraken()
        sol = exchange.fetch_ohlcv('SOL/USD', timeframe=timeframe, limit=300)
        btc = exchange.fetch_ohlcv('BTC/USD', timeframe='1d', limit=1)
        
        df = pd.DataFrame(sol, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # Rule 1: Emmanuel Logic
        df['20_ema'] = df['close'].ewm(span=20, adjust=False).mean()
        df['200_sma'] = df['close'].rolling(window=200).mean()
        
        # Rule 3: Daily ATR for Range
        df['tr'] = df[['high', 'low', 'close']].max(axis=1) - df[['high', 'low', 'close']].min(axis=1)
        daily_atr = df['tr'].rolling(window=14).mean().iloc[-1]
        
        return df, btc[0][4], daily_atr, True
    except:
        return None, 0, 0, False
