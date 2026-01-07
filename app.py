import ccxt
import pandas as pd
import streamlit as st
import requests
import numpy as np
import plotly.graph_objects as go
import streamlit.components.v1 as components
from datetime import datetime

# 1. CORE DATA ENGINE
@st.cache_data(ttl=15)
def fetch_institutional_data():
    try:
        exchange = ccxt.kraken()
        sol_bars = exchange.fetch_ohlcv('SOL/USD', timeframe='1d', limit=300)
        btc_bars = exchange.fetch_ohlcv('BTC/USD', timeframe='1d', limit=300)
        
        df = pd.DataFrame(sol_bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
        btc_df = pd.DataFrame(btc_bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Emmanuel's Core Elements
        df['20_ema'] = df['close'].ewm(span=20, adjust=False).mean()
        df['200_sma'] = df['close'].rolling(window=200).mean()
        df['tr'] = df[['high', 'low', 'close']].max(axis=1) - df[['high', 'low', 'close']].min(axis=1)
        df['atr'] = df['tr'].rolling(window=14).mean()
        
        # Technical Indicators for Table
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        df['rsi'] = 100 - (100 / (1 + (gain / loss.replace(0, np.nan)).fillna(0)))
        
        # Volume & Market Alpha
        df['poc'] = df.tail(20).loc[df.tail(20)['volume'].idxmax()]['close']
        
        try:
            fng_res = requests.get("https://api.alternative.me/fng/", timeout=5).json()
            fng_val = int(fng_res['data'][0]['value'])
            fng_class = fng_res['data'][0]['value_classification']
        except:
            fng_val, fng_class = 50, "Neutral"

        return df, btc_df['close'].iloc[-1], fng_val, fng_class, True
    except:
        return None, None, 50, "Error", False

def create_gauge(value, title, color):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = value,
        title = {'text': title, 'font': {'size': 18, 'color': 'white'}},
        gauge = {
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "gray"},
            'bar': {'color': color},
            'bgcolor': "rgba(0,0,0,0)",
            'steps': [
                {'range': [0, 30], 'color': 'rgba(255, 0, 0, 0.3)'},
                {'range': [30, 70], 'color': 'rgba(255, 255, 255, 0.1)'},
                {'range': [70, 100], 'color': 'rgba(0, 255, 163, 0.3)'}],
        }
    ))
    fig.update_layout(height=250, margin=dict(l=20, r=20, t=50, b=20), paper_bgcolor='rgba(0,0,0,0)')
    return fig

def get_sreejan_forecaster():
    st.set_page_config(page_title="Sreejan Master Pro", layout="wide")
    
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Libre+Baskerville&family=Roboto+Mono&display=swap');
        .stApp { background-color: #0A0A0B; color: #E0E0E0; }
        .metric-card { background: #111113; padding: 15px; border: 1px solid #222; border-radius: 4px; text-align: center; }
        h1, h2, h3 { font-family: 'Libre+Baskerville', serif; color: #D4AF37; }
        .mono { font-family: 'Roboto Mono', monospace; }
        .status-dot { height: 10px; width: 10px; border-radius: 50%; display: inline-block; margin-right: 8px; }
        
        /* HOVER TOOLTIP */
        .tooltip { position: relative; display: inline-block; cursor: help; color: #854CE6; text-decoration: underline; }
        .tooltip .tooltiptext {
            visibility: hidden; width: 220px; background-color: #1A1A1D; border: 1px solid #D4AF37;
            padding: 10px; border-radius: 5px; position: absolute; z-index: 100; bottom: 125%; left: 50%;
            margin-left: -110px; opacity: 0; transition: opacity 0.3s; color: #fff; font-size: 12px;
        }
        .tooltip:hover .tooltiptext { visibility: visible; opacity: 1; }
        </style>
    """, unsafe_allow_html=True)

    df, btc_p, fng_v, fng_c, status = fetch_institutional_data()

    # --- TOP ROW: STATUS & GAUGES ---
    t_col1, t_col2, t_col3 = st.columns([1, 1.5, 1])
    
    with t_col1:
        st.markdown(f"### Market Gauges")
        st.plotly_chart(create_gauge(df['rsi'].iloc[-1] if df is not None else 50, "RSI (14)", "#854CE6"), use_container_width=True)
    
    with t_col2:
        st.markdown("<h1 style='text-align: center;'>SREEJAN MASTER PRO</h1>", unsafe_allow_html=True)
        st.markdown(f"<div style='text-align: center;'><span class='status-dot' style='background-color:{'#00FFA3' if status else '#FF4B4B'}'></span>Institutional Feed Live</div>", unsafe_allow_html=True)
    
    with t_col3:
        st.markdown(f"### Sentiment")
        st.plotly_chart(create_gauge(fng_v, "Fear & Greed", "#D4AF37"), use_container_width=True)

    if df is not None:
        price = df['close'].iloc[-1]
        atr = df['atr'].iloc[-1]
        ema20 = df['20_ema'].iloc[-1]
        sma200 = df['200_sma'].iloc[-1]

        # --- SIGNAL TABLE (EMMANUEL LOGIC) ---
        st.subheader("⚡ Signal Summary (Emmanuel-Logic)")
        if price > sma200 and price > ema20:
            sig, color = "STRONG BUY 🟢", "#00FFA3"
            entry, sl, tp1, tp2 = price * 1.002, price - (atr * 1.5), price + (atr * 1.5), price + (atr * 3)
        elif price < sma200 and price < ema20:
            sig, color = "STRONG SELL 🔴", "#FF4B4B"
            entry, sl, tp1, tp2 = price * 0.998, price + (atr * 1.5), price - (atr * 1.5), price - (atr * 3)
        else:
            sig, color = "NEUTRAL ⚖️", "#888"
            entry, sl, tp1, tp2 = price, price - atr, price + atr, price + (atr*2)

        st.markdown(f"""
        <table style="width:100%; border-collapse: collapse; border: 1px solid #333; font-family: 'Roboto Mono'; background-color: #0E1117;">
            <tr style="background-color: #1A1C23; color:#888;">
                <th style="padding:10px;">ACTION</th><th>ENTRY</th><th>STOP LOSS</th><th>TP 1</th><th>TP 2</th>
            </tr>
            <tr style="text-align: center; font-size: 18px;">
                <td style="padding: 15px; border: 1px solid #333; color: {color}; font-weight: bold;">{sig}</td>
                <td style="padding: 15px; border: 1px solid #333;">${entry:,.2f}</td>
                <td style="padding: 15px; border: 1px solid #333; color: #FF4B4B;">${sl:,.2f}</td>
                <td style="padding: 15px; border: 1px solid #333; color: #00FFA3;">${tp1:,.2f}</td>
                <td style="padding: 15px; border: 1px solid #333; color: #00FFA3;">${tp2:,.2f}</td>
            </tr>
        </table>
        """, unsafe_allow_html=True)

        # --- INDICATOR DETAILS TABLE ---
        st.subheader("📊 Technical Indicator Breakdown")
        i_col1, i_col2 = st.columns(2)
        with i_col1:
            st.table(pd.DataFrame({
                "Indicator": ["RSI (14)", "20 EMA", "200 SMA", "ATR (14)"],
                "Value": [f"{df['rsi'].iloc[-1]:.2f}", f"{ema20:.2f}", f"{sma200:.2f}", f"{atr:.4f}"],
                "Action": ["Sell" if df['rsi'].iloc[-1] > 70 else "Buy" if df['rsi'].iloc[-1] < 30 else "Neutral", 
                           "Bullish" if price > ema20 else "Bearish", 
                           "Strong Bull" if price > sma200 else "Strong Bear", "Low Volatility" if atr < 5 else "High Vol"]
            }))

        # --- CORE: AUTOGENERATED RANGE & LIQ ---
        st.sidebar.title("💰 Capital & Risk")
        capital = st.sidebar.number_input("Capital ($)", value=10000.0)
        lev = st.sidebar.select_slider("Leverage", options=[1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0], value=1.5)
        bias = st.sidebar.selectbox("Macro Bias", ["Bullish 🚀", "Neutral ⚖️", "Bearish 📉"])
        
        liq_price = price * (1 - (1/lev)*0.45)
        st.sidebar.markdown(f"<div style='background:#222; padding:10px; border-left:5px solid #FF4B4B;'><b>LIQUIDATION</b><br><span class='mono'>${liq_price:,.2f}</span></div>", unsafe_allow_html=True)
        
        mult = 3.2 if bias == "Bearish 📉" else 2.2 if bias == "Bullish 🚀" else 2.7
        auto_low, auto_high = price - (atr * mult), price + (atr * mult)
        
        # --- ECONOMIC CALENDAR ---
        st.divider()
        st.subheader("📅 Institutional Economic Calendar")
        components.html("""
            <div class="tradingview-widget-container">
              <div class="tradingview-widget-container__widget"></div>
              <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-events.js" async>
              {
              "colorTheme": "dark",
              "isTransparent": true,
              "width": "100%",
              "height": "400",
              "locale": "en",
              "importanceFilter": "-1,0,1"
            }
              </script>
            </div>
        """, height=400)

        # --- RANGE FORECASTER ---
        st.subheader(f"Institutional Range: ${auto_low:,.2f} — ${auto_high:,.2f}")
        m_low, m_high = st.slider("Manual Range Adjustment", float(price*0.3), float(price*1.7), (float(auto_low), float(auto_high)))
        
        daily_p = (capital * lev * 0.0017) * ((price * 0.35) / max(m_high - m_low, 0.01))
        st.subheader(f"Yield Matrix (Daily Avg: ${daily_p:,.2f})")
        y_cols = st.columns(7)
        periods = {"1H": 1/24, "3H": 3/24, "6H": 6/24, "12H": 0.5, "1D": 1, "1W": 7, "1M": 30}
        for i, (lab, m) in enumerate(periods.items()):
            y_cols[i].metric(lab, f"${(daily_p * m):,.2f}")

if __name__ == "__main__":
    get_sreejan_forecaster()
