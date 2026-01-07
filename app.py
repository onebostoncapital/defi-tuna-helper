import ccxt
import pandas as pd
import streamlit as st
import requests
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. INSTITUTIONAL DATA ENGINE
@st.cache_data(ttl=15)
def fetch_institutional_data():
    try:
        exchange = ccxt.kraken()
        # Fetch 300 bars to ensure 200 SMA is calculated even with holidays/gaps
        sol_bars = exchange.fetch_ohlcv('SOL/USD', timeframe='1d', limit=300)
        btc_bars = exchange.fetch_ohlcv('BTC/USD', timeframe='1d', limit=300)
        
        df = pd.DataFrame(sol_bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        btc_df = pd.DataFrame(btc_bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Emmanuel's Indicators (LOCKED)
        df['20_ema'] = df['close'].ewm(span=20, adjust=False).mean()
        df['200_sma'] = df['close'].rolling(window=200).mean()
        
        # ALPHA: RSI & Correlation
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        # Prevent division by zero
        rs = gain / loss.replace(0, np.nan)
        df['rsi'] = 100 - (100 / (1 + rs.fillna(0)))
        
        # BTC Correlation (aligned by timestamp)
        df['btc_corr'] = df['close'].rolling(window=30).corr(btc_df['close'])
        
        # ALPHA: Volume POC (Point of Control)
        recent = df.tail(20)
        df['poc'] = recent.loc[recent['volume'].idxmax()]['close'] if not recent.empty else df['close'].iloc[-1]
        
        # Fear & Greed with fallback
        try:
            fng_res = requests.get("https://api.alternative.me/fng/", timeout=5).json()
            fng_data = fng_res['data'][0]
        except:
            fng_data = {'value': '50', 'value_classification': 'Neutral'}

        return df, btc_df['close'].iloc[-1], fng_data
    except Exception as e:
        st.error(f"Market Data Offline: {e}")
        return None, None, None

def get_sreejan_forecaster():
    st.set_page_config(page_title="Sreejan Master Pro", layout="wide")
    
    # CLASSIC PROFESSIONAL CSS
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Libre+Baskerville:ital@1&family=Roboto+Mono:wght@300&display=swap');
        .stApp { background-color: #0A0A0B; color: #E0E0E0; }
        .metric-card { background: #111113; padding: 20px; border: 1px solid #222; border-radius: 4px; text-align: center;}
        h1, h2, h3 { font-family: 'Libre+Baskerville', serif; font-weight: 400; color: #D4AF37; }
        .mono { font-family: 'Roboto Mono', monospace; }
        </style>
    """, unsafe_allow_html=True)

    df, btc_price, fng = fetch_institutional_data()

    if df is not None:
        price = df['close'].iloc[-1]
        rsi = df['rsi'].iloc[-1]
        poc = df['poc'].iloc[-1]
        corr = df['btc_corr'].iloc[-1] if not pd.isna(df['btc_corr'].iloc[-1]) else 0.0
        ema20 = df['20_ema'].iloc[-1]
        sma200 = df['200_sma'].iloc[-1] if not pd.isna(df['200_sma'].iloc[-1]) else ema20
        vol_24h = df['volume'].iloc[-1] * price

        # --- 1. TOP BANNER (PROFESSIONAL NAMES & SYMBOLS) ---
        cols = st.columns([1.2, 1, 1, 1, 1.2])
        with cols[0]: st.markdown(f"<div class='metric-card'><small>BITCOIN (BTC)</small><br><b class='mono' style='font-size:20px; color:#F7931A;'>₿ {btc_price:,.2f}</b></div>", unsafe_allow_html=True)
        with cols[1]: st.markdown(f"<div class='metric-card'><small>SOLANA (SOL)</small><br><b class='mono' style='font-size:20px; color:#854CE6;'>🟣 {price:,.2f}</b></div>", unsafe_allow_html=True)
        with cols[2]: st.markdown(f"<div class='metric-card'><small>24H VOLUME</small><br><b class='mono' style='font-size:20px; color:#00FFA3;'>📊 {vol_24h/1e9:.2f}B</b></div>", unsafe_allow_html=True)
        with cols[3]: st.markdown(f"<div class='metric-card'><small>BTC CORR</small><br><b class='mono' style='font-size:20px;'>{corr:.2f}</b></div>", unsafe_allow_html=True)
        with cols[4]: st.markdown(f"<div class='metric-card'><small>SENTIMENT</small><br><b class='mono' style='font-size:20px;'>{fng['value']} ({fng['value_classification']})</b></div>", unsafe_allow_html=True)

        # --- SIDEBAR (LOCKED) ---
        st.sidebar.title("💰 Strategy Config")
        capital = st.sidebar.number_input("Capital ($)", value=10000.0)
        lev = st.sidebar.select_slider("Leverage", options=[1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0], value=1.5)
        bias_input = st.sidebar.selectbox("Macro Bias", ["Bullish 🚀", "Neutral ⚖️", "Bearish 📉"])

        # --- MARKET HEAT (RSI) ---
        st.divider()
        st.write("Market Heat (RSI)")
        st.progress(min(max(rsi/100, 0.0), 1.0))
        st.caption(f"{'OVERBOUGHT' if rsi > 70 else 'OVERSOLD' if rsi < 30 else 'NEUTRAL'} | RSI: {rsi:.1f}")

        # --- EMMANUEL PERP SIGNAL (LOCKED) ---
        st.subheader("⚡ Emmanuel-Logic Perp Signal")
        df['tr'] = df[['high', 'low', 'close']].max(axis=1) - df[['high', 'low', 'close']].min(axis=1)
        atr = df['tr'].rolling(window=14).mean().iloc[-1]
        
        if price > sma200 and price > ema20:
            sig, color = "STRONG LONG 🟢", "#00FFA3"
            entry, sl, tp1, tp2 = price * 1.002, price - (atr * 1.2), price + (atr * 1.5), price + (atr * 3)
        elif price < sma200 and price < ema20:
            sig, color = "STRONG SHORT 🔴", "#FF4B4B"
            entry, sl, tp1, tp2 = price * 0.998, price + (atr * 1.2), price - (atr * 1.5), price - (atr * 3)
        else:
            sig, color = "NEUTRAL / NO TRADE ⚪", "#888"
            entry, sl, tp1, tp2 = price, price - atr, price + atr, price + (atr*2)

        st.markdown(f"""
        <table style="width:100%; border-collapse: collapse; border: 1px solid #333; font-family: 'Roboto Mono'; background-color: #0E1117;">
            <tr style="background-color: #1A1C23; color:#888;">
                <th style="padding: 15px; border: 1px solid #333;">INDICATIVE BIAS</th>
                <th style="padding: 15px; border: 1px solid #333;">ENTRY</th>
                <th style="padding: 15px; border: 1px solid #333;">STOP LOSS</th>
                <th style="padding: 15px; border: 1px solid #333;">TARGET 1</th>
                <th style="padding: 15px; border: 1px solid #333;">TARGET 2</th>
            </tr>
            <tr style="text-align: center; font-size: 18px;">
                <td style="padding: 20px; border: 1px solid #333; color: {color}; font-weight: bold;">{sig}</td>
                <td style="padding: 20px; border: 1px solid #333;">${entry:,.2f}</td>
                <td style="padding: 20px; border: 1px solid #333; color: #FF4B4B;">${sl:,.2f}</td>
                <td style="padding: 20px; border: 1px solid #333; color: #00FFA3;">${tp1:,.2f}</td>
                <td style="padding: 20px; border: 1px solid #333; color: #00FFA3;">${tp2:,.2f}</td>
            </tr>
        </table>
        """, unsafe_allow_html=True)

        # --- TACTICAL CANDLESTICK CHART ---
        st.subheader("📊 Tactical Analysis (SOL/USD)")
        hist = df.tail(50)
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=hist['date'], open=hist['open'], high=hist['high'], low=hist['low'], close=hist['close'], name='Price'))
        fig.add_trace(go.Scatter(x=hist['date'], y=hist['20_ema'], name='20 EMA', line=dict(color='#854CE6', width=2)))
        fig.add_trace(go.Scatter(x=hist['date'], y=hist['200_sma'], name='200 SMA', line=dict(color='#FF9900', width=2, dash='dot')))
        fig.add_hline(y=poc, line_color="#D4AF37", line_dash="dash", annotation_text="Volume POC")
        
        fig.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)

        # --- RANGE FORECASTER & YIELD (LOCKED) ---
        st.divider()
        mult = 3.2 if bias_input == "Bearish 📉" else 2.2 if bias_input == "Bullish 🚀" else 2.7
        auto_low, auto_high = price - (atr * mult), price + (atr * mult)
        st.markdown(f"### **Institutional Range: ${auto_low:,.2f} — ${auto_high:,.2f}**")
        m_low, m_high = st.slider("Manual Parameter Tune", float(price*0.3), float(price*1.7), (float(auto_low), float(auto_high)), 0.10)
        
        daily_p = (capital * lev * 0.0017) * ((price * 0.35) / max(m_high - m_low, 0.01))
        st.subheader(f"💰 Yield Matrix (Daily: ${daily_p:,.2f})")
        y_cols = st.columns(7)
        periods = {"1HR": 1/24, "3HR": 3/24, "6HR": 6/24, "12HR": 0.5, "1 DAY": 1, "1 WEEK": 7, "1 MON": 30}
        for i, (lab, m) in enumerate(periods.items()):
            y_cols[i].metric(lab, f"${(daily_p * m):,.2f}")

        # --- NEWS FOOTER (WITH ERROR HANDLING) ---
        st.divider()
        st.subheader("📰 Market Alpha News")
        try:
            news_res = requests.get("https://min-api.cryptocompare.com/data/v2/news/?lang=EN", timeout=5).json()
            if 'data' in news_res:
                n_cols = st.columns(5)
                for idx, art in enumerate(news_res['data'][:5]):
                    with n_cols[idx]:
                        st.markdown(f"**[{art['title'][:45]}...]({art['url']})**")
                        st.caption(f"{art['source']}")
            else:
                st.warning("News data temporarily unavailable from API.")
        except:
            st.warning("Could not connect to News Server.")

if __name__ == "__main__":
    get_sreejan_forecaster()
