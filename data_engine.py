import yfinance as yf
import pandas as pd

def fetch_base_data(interval="1h"):
    try:
        period_map = {
            "1m": "1d", "5m": "1d", "15m": "3d", "30m": "5d", 
            "1h": "7d", "4h": "14d", "12h": "30d", "1d": "60d"
        }
        target_period = period_map.get(interval, "7d")

        # 1. Fetch SOLANA Data
        sol = yf.Ticker("SOL-USD")
        df = sol.history(period=target_period, interval=interval)
        
        if df.empty:
            return None, 0, "No data found for SOL", False

        # 2. FIXING THE KEYERROR: Explicitly handle the Date index
        df = df.reset_index()
        # This renames whatever the first column is (usually Date or Datetime) to 'date'
        df.rename(columns={df.columns[0]: 'date'}, inplace=True)
        
        # Standardize all other columns to lowercase (open, high, low, close)
        df.columns = [str(c).lower() for c in df.columns]

        # 3. Calculate Rules (20 EMA & 200 SMA)
        df['20_ema'] = df['close'].ewm(span=20, adjust=False).mean()
        df['200_sma'] = df['close'].rolling(window=200).mean()
        
        # 4. Fetch BITCOIN Price
        btc = yf.Ticker("BTC-USD")
        btc_data = btc.history(period="1d")
        btc_price = btc_data['Close'].iloc[-1] if not btc_data.empty else 0

        return df, btc_price, None, True

    except Exception as e:
        return None, 0, str(e), False
