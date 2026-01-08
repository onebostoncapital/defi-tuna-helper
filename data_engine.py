import yfinance as yf
import pandas as pd

def fetch_base_data(interval="1h"):
    try:
        # Map 12h to 1h base for resampling stability
        y_interval = "1h" if interval == "12h" else interval
        period_map = {"1m":"1d", "5m":"1d", "15m":"2d", "30m":"2d", "1h":"7d", "4h":"14d", "1d":"60d"}
        
        sol = yf.Ticker("SOL-USD")
        df = sol.history(period=period_map.get(y_interval, "7d"), interval=y_interval)
        
        if df is None or df.empty: 
            return None, 0, "No Data", False

        if interval == "12h":
            df = df.resample('12h').agg({'Open':'first','High':'max','Low':'min','Close':'last'}).dropna()

        df = df.reset_index()
        df.columns = [str(c).lower() for c in df.columns]
        df.rename(columns={df.columns[0]: 'date'}, inplace=True)

        # Indicators with safety padding
        df['20_ema'] = df['close'].ewm(span=20, adjust=False).mean()
        # Ensure 200 SMA doesn't break on short dataframes
        window = min(200, len(df))
        df['200_sma'] = df['close'].rolling(window=window).mean()
        
        btc = yf.Ticker("BTC-USD").history(period="1d")
        btc_p = btc['Close'].iloc[-1] if not btc.empty else 0

        return df, btc_p, None, True
    except Exception:
        return None, 0, "API Error", False
