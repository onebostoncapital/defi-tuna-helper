import ccxt
import pandas as pd
import streamlit as st
import requests
import numpy as np
import plotly.graph_objects as go
import base64
from datetime import datetime

# 1. INSTITUTIONAL DATA ENGINE (CORE REFINED)
@st.cache_data(ttl=15)
def fetch_institutional_data():
    try:
        exchange = ccxt.kraken()
        sol_bars = exchange.fetch_ohlcv('SOL/USD', timeframe='1d', limit=300)
        btc_bars = exchange.fetch_ohlcv('BTC/USD', timeframe='1d', limit=300)
        
        df = pd.DataFrame(sol_bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
        btc_df = pd.DataFrame(btc_bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        df['20_ema'] = df['close'].ewm(span=20, adjust=False).mean()
        df['200_sma'] = df['close'].rolling(window=200).mean()
        
        # Alpha Indicators
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss.replace(0, np.nan)
        df['rsi'] = 100 - (100 / (1 + rs.fillna(0)))
        df['btc_corr'] = df['close'].rolling(window=30).corr(btc_df['close'])
        
        # Volume POC
        recent = df.tail(20)
        df['poc'] = recent.loc[recent['volume'].idxmax()]['close'] if not recent.empty else df['close'].iloc[-1]
        
        try:
            fng_res = requests.get("https://api.alternative.me/fng/", timeout=5).json()
            fng_data = fng_res['data'][0]
        except:
            fng_data = {'value': '50', 'value_classification': 'Neutral'}

        return df, btc_df['close'].iloc[-1], fng_data, True
    except:
        return None, None, None, False

# 2. AUDIO TRIGGER FUNCTION
def play_alert_sound():
    # Subtle "Success" chime for signal trigger
    audio_base64 = "UklGRjIAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=" # Placeholder silent ping
    # For a real sound, you would use a base64 encoded mp3 string here.
    audio_html = f'<audio autoplay><source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3"></audio>'
    st.markdown(audio_html, unsafe_allow_html=True)

def get_sreejan_forecaster():
    st.set_page_config(page_title="Sreejan Master Pro", layout="wide")
    
    # CLASSIC DESIGN & TOOLTIP CSS
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Libre+Baskerville&family=Roboto+Mono&display=swap');
        .stApp { background-color: #0A0A0B; color: #E0E0E0; }
        .metric-card { background: #111113; padding: 20px; border: 1px solid #222; border-radius: 4px; text-align: center; position: relative;}
        h1, h2, h3 { font-family: 'Libre+Baskerville', serif; color: #D4AF37; }
        .mono { font-family: 'Roboto Mono', monospace; }
        
        /* HOVER TOOLTIP SYSTEM */
        .tooltip { position: relative; display: inline-block; cursor: help; border-bottom: 1px dotted #D4AF37; }
        .tooltip .tooltiptext {
            visibility: hidden; width: 200px; background-color: #1A1A1D; color: #fff;
            text-align: center; border-radius: 6px; padding: 10px; position: absolute;
            z-index: 1000; bottom: 125%; left: 50%; margin-left: -100px; opacity: 0;
            transition: opacity 0.3s; border: 1px solid #D4AF37; font-family: sans-serif; font-size: 12px;
        }
        .tooltip:hover .tooltiptext { visibility: visible; opacity: 1; }
        
        /* STATUS INDICATOR */
        .status-dot { height: 10px; width: 10px; border-radius: 50%; display: inline-block; margin-right: 5px; }
        </style>
    """, unsafe_allow_html=True)

    df, btc_price, fng, status = fetch_institutional_data()

    # --- TOP STATUS & BANNER ---
    s_col1, s_col2 = st.columns([8, 2])
    with s_col2:
        dot_color = "#00FFA3" if status else "#FF4B4B"
        st.markdown(f"<div style='text-align: right;'><span class='status-dot' style='background-color:{dot_color}'></span>System Active</div>", unsafe_allow_html=True)

    if df is not None:
        price = df['close'].iloc[-1]
        rsi = df['rsi'].iloc[-1]
        poc = df['poc'].iloc[-1]
        ema20 = df['20_ema'].iloc[-1]
        sma200 = df['200_sma'].iloc[-1]
        atr = (df['high'] - df['low']).rolling(window=14).mean().iloc[-1]

        # --- BANNER WITH TOOLTIPS ---
        cols = st.columns([1, 1, 1, 1, 1])
        with cols[0]: st.markdown(f"<div class='metric-card'><small>BTC PRICE</small><br><b class='mono' style='color:#F7931A;'>₿ {btc_price:,.2f}</b></div>", unsafe_allow_html=True)
        with cols[1]: st.markdown(f"<div class='metric-card'><small>SOL PRICE</small><br><b class='mono' style='color:#854CE6;'>🟣 {price:,.2f}</b></div>", unsafe_allow_html=True)
        with cols[4]: 
            st.markdown(f"""
                <div class='metric-card'>
                    <small class='tooltip'>MARKET SENTIMENT
                        <span class='tooltiptext'>Fear & Greed Index: 0-30 = Extreme Fear (Buying Opp), 70-100 = Extreme Greed (Take Profit).</span>
                    </small><br>
                    <b class='mono'>{fng['value']} ({fng['value_classification']})</b>
                </div>
            """, unsafe_allow_html=True)

        # --- EMMANUEL PERP SIGNAL & TRIGGER ---
        st.subheader("⚡ Execution Signal")
        if price > sma200 and price > ema20:
            sig, color = "STRONG LONG 🟢", "#00FFA3"
            entry, sl, tp1, tp2 = price * 1.002, price - (atr * 1.5), price + (atr * 1.5), price + (atr * 3)
            # Notification Trigger
            st.toast("🚨 ALERT: Long Signal Triggered!", icon="📈")
            play_alert_sound()
        elif price < sma200 and price < ema20:
            sig, color = "STRONG SHORT 🔴", "#FF4B4B"
            entry, sl, tp1, tp2 = price * 0.998, price + (atr * 1.5), price - (atr * 1.5), price - (atr * 3)
            st.toast("🚨 ALERT: Short Signal Triggered!", icon="📉")
            play_alert_sound()
        else:
            sig, color = "NEUTRAL ⚪", "#888"
            entry, sl, tp1, tp2 = price, price - atr, price + atr, price + (atr*2)

        st.markdown(f"""
        <table style="width:100%; border-collapse: collapse; border: 1px solid #333; font-family: 'Roboto Mono'; background-color: #0E1117;">
            <tr style="background-color: #1A1C23; color:#888;">
                <th style="padding: 15px; border: 1px solid #333;">BIAS</th>
                <th style="padding: 15px; border: 1px solid #333;">ENTRY</th>
                <th style="padding: 15px; border: 1px solid #333;">STOP LOSS</th>
                <th style="padding: 15px; border: 1px solid #333;">TP 1</th>
                <th style="padding: 15px; border: 1px solid #333;">TP 2</th>
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

        # --- TACTICAL CHART ---
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=df.tail(40)['date'], open=df.tail(40)['open'], high=df.tail(40)['high'], low=df.tail(40)['low'], close=df.tail(40)['close']))
        fig.add_trace(go.Scatter(x=df.tail(40)['date'], y=df.tail(40)['20_ema'], name='20 EMA', line=dict(color='#854CE6')))
        fig.add_trace(go.Scatter(x=df.tail(40)['date'], y=df.tail(40)['200_sma'], name='200 SMA', line=dict(color='#FF9900', dash='dot')))
        fig.update_layout(template="plotly_dark", height=450, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        # --- RANGE & YIELD (LOCKED) ---
        st.sidebar.title("💰 Capital")
        capital = st.sidebar.number_input("Amount ($)", value=10000.0)
        lev = st.sidebar.select_slider("Leverage", options=[1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0], value=1.5)
        
        st.divider()
        auto_low, auto_high = price - (atr * 2.5), price + (atr * 2.5)
        m_low, m_high = st.slider("Manual Range Selection", float(price*0.5), float(price*1.5), (float(auto_low), float(auto_high)))
        
        daily_p = (capital * lev * 0.0017) * ((price * 0.35) / max(m_high - m_low, 0.01))
        st.subheader(f"Projected Yield (Daily: ${daily_p:,.2f})")
        y_cols = st.columns(7)
        periods = {"1H": 1/24, "3H": 3/24, "6H": 6/24, "12H": 0.5, "1D": 1, "1W": 7, "1M": 30}
        for i, (lab, m) in enumerate(periods.items()):
            y_cols[i].metric(lab, f"${(daily_p * m):,.2f}")

if __name__ == "__main__":
    get_sreejan_forecaster()
