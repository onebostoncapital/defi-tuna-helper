import yfinance as yf
import pandas as pd

def fetch_base_data(interval="1h"):
    try:
        # Step 1: Handle the 12h limitation of yfinance
        fetch_interval = "1h" if interval == "12h" else interval
        period_map = {
            "1m": "1d", "5m": "1d", "15m": "3d", "30m": "5d", 
            "1h": "7d", "4h": "14d", "1d": "60d"
        }
        target_period = period_map.get(fetch_interval, "7d")

        # Step 2: Fetch Data
        sol = yf.Ticker("SOL-USD")
        df = sol.history(period=target_period, interval=fetch_interval)
        
        if df.empty:
            return None, 0, "No data", False

        # Step 3: Virtual 12h Calculation (Resampling)
        if interval == "12h":
            df = df.resample('12h').agg({
                'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
            }).dropna()

        # Step 4: Standardize Columns
        df = df.reset_index()
        df.rename(columns={df.columns[0]: 'date'}, inplace=True)
        df.columns = [str(c).lower() for c in df.columns]

        # Step 5: Indicators (Rules: 20 EMA, 200 SMA)
        df['20_ema'] = df['close'].ewm(span=20, adjust=False).mean()
        df['200_sma'] = df['close'].rolling(window=200).mean()
        
        # Step 6: BTC Price
        btc = yf.Ticker("BTC-USD")
        btc_data = btc.history(period="1d")
        btc_p = btc_data['Close'].iloc[-1] if not btc_data.empty else 0

        return df, btc_p, None, True

    except Exception as e:
        return None, 0, str(e), False
