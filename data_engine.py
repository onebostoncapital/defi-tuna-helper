import yfinance as yf
import pandas as pd

def fetch_base_data(interval="1h"):
    try:
        y_interval = "1h" if interval == "12h" else interval
        period_map = {"1m":"1d", "5m":"1d", "15m":"3d", "30m":"5d", "1h":"7d", "4h":"14d", "1d":"60d"}
        
        sol = yf.Ticker("SOL-USD")
        df = sol.history(period=period_map.get(y_interval, "7d"), interval=y_interval)
        
        if df.empty: return None, 0, "No Data", False

        if interval == "12h":
            df = df.resample('12h').agg({'Open':'first','High':'max','Low':'min','Close':'last'}).dropna()

        df = df.reset_index()
        df.columns = [str(c).lower() for c in df.columns]
        df.rename(columns={df.columns[0]: 'date'}, inplace=True)

        # Logic Rules: EMA 20 and SMA 200
        df['20_ema'] = df['close'].ewm(span=20, adjust=False).mean()
        df['200_sma'] = df['close'].rolling(window=200).mean()
        
        btc = yf.Ticker("BTC-USD").history(period="1d")
        btc_p = btc['Close'].iloc[-1] if not btc.empty else 0

        return df, btc_p, None, True
    except Exception:
        return None, 0, "Error", False
