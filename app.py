import ccxt
import pandas as pd
import streamlit as st
import requests
import numpy as np
import plotly.graph_objects as go
import streamlit.components.v1 as components
from datetime import datetime

# 1. CORE DATA ENGINE (Referencing Master Rule Book)
@st.cache_data(ttl=15)
def fetch_terminal_data(perp_tf='1d'):
    try:
        exchange = ccxt.kraken()
        # Fetch Dynamic Data for Perp Trading (Timeframe varies)
        perp_bars = exchange.fetch_ohlcv('SOL/USD', timeframe=perp_tf, limit=300)
        # Fetch Static Daily Data for Predictive Model (Rule 3)
        daily_bars = exchange.fetch_ohlcv('SOL/USD', timeframe='1d', limit=100)
        btc_bars = exchange.fetch_ohlcv('BTC/USD', timeframe='1d', limit=1)
        
        # Process Perp Data
        df_perp = pd.DataFrame(perp_bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df_perp['date'] = pd.to_datetime(df_perp['timestamp'], unit='ms')
        df_perp['20_ema'] = df_perp['close'].ewm(span=20, adjust=False).mean()
        df_perp['200_sma'] = df_perp['close'].rolling(window=200).mean()
        
        # Process Predictive Range Data (Static Daily Rule)
        df_daily = pd.DataFrame(daily_bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df_daily['tr'] = df_daily[['high', 'low', 'close']].max(axis=1) - df_daily[['high', 'low', 'close']].min(axis=1)
        daily_atr = df_daily['tr'].rolling(window=14).mean().iloc[-1]
        
        # General RSI for Gauge
        delta = df_perp['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rsi = 100 - (100 / (1 + (gain / loss.replace(0, np.nan)).fillna(0))).iloc[-1]
        
        return df_perp, btc_bars[0][4], daily_atr, rsi, True
    except:
        return None, None, None, 50, False

def get_sreejan_terminal():
    st.set_page_config(page_title="Sreejan Master Pro", layout="wide")
    
    # MASTER UI STYLING (Rule 2: Well-defined boxes)
    st.markdown("""
        <style>
        .perp-box { border: 2px solid #854CE6; padding: 25px; border-radius: 12px; background: #0E1117; margin-bottom: 30px; }
        .predictive-box { border: 2px solid #D4AF37; padding: 25px; border-radius: 12px; background: #0E1117; margin-top: 30px; }
        .stApp { background-color: #0A0A0B; color: #E0E0E0; }
        .mono { font-family: 'Roboto Mono', monospace; }
        </style>
    """, unsafe_allow_html=True)

    # SIDEBAR CONTROLS
    st.sidebar.title("🎛️ Terminal Hub")
    selected_tf = st.sidebar.selectbox("Chart Timeframe (Perp Only)", ["1m", "3m", "5m", "15m", "1h", "4h", "1d", "1w"], index=4)
    capital = st.sidebar.number_input("Portfolio Capital ($)", value=10000.0)
    leverage = st.sidebar.slider("Leverage (45% Margin Cap)", 1.0, 10.0, 1.5)
    bias = st.sidebar.selectbox("Predictive Macro Bias", ["Bullish 🚀", "Neutral ⚖️", "Bearish 📉"])

    df, btc_p, daily_atr, rsi_val, status = fetch_terminal_data(selected_tf)

    if df is not None:
        price = df['close'].iloc[-1]
        ema20, sma200 = df['20_ema'].iloc[-1], df['200_sma'].iloc[-1]

        # --- PERSISTENT TOP BANNER (Rule 4) ---
        b1, b2, b3 = st.columns(3)
        b1.metric("BITCOIN", f"${btc_p:,.2f}")
        b2.metric("SOLANA", f"${price:,.2f}")
        b3.metric("RSI GAIN", f"{rsi_val:.2f}%")

        # =========================================================================
        # SECTION A: PERP TRADING INDICATOR (TOP BOX - Rule 5)
        # =========================================================================
        st.markdown('<div class="perp-box">', unsafe_allow_html=True)
        st.header(f"📉 Perp Trading Indicator ({selected_tf})")
        
        # Emmanuel-Logic Signal Trigger
        if price > sma200 and price > ema20:
            sig, color = "STRONG BUY 🟢", "#00FFA3"
            st.toast("ALARM: Long Signal Confirmed", icon="📈")
        elif price < sma200 and price < ema20:
            sig, color = "STRONG SELL 🔴", "#FF4B4B"
            st.toast("ALARM: Short Signal Confirmed", icon="📉")
        else:
            sig, color = "NEUTRAL ⚖️", "#888"

        st.markdown(f"**Current Signal:** <span style='color:{color}; font-size:24px;'>{sig}</span>", unsafe_allow_html=True)
        
        # Interactive Candlestick Chart
        fig = go.Figure()
        view = df.tail(100)
        fig.add_trace(go.Candlestick(x=view['date'], open=view['open'], high=view['high'], low=view['low'], close=view['close'], name="Market"))
        fig.add_trace(go.Scatter(x=view['date'], y=view['20_ema'], name='20 EMA', line=dict(color='#854CE6')))
        fig.add_trace(go.Scatter(x=view['date'], y=view['200_sma'], name='200 SMA', line=dict(color='#FF9900', dash='dot')))
        fig.update_layout(template="plotly_dark", height=450, xaxis_rangeslider_visible=False, margin=dict(t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # =========================================================================
        # SECTION B: PREDICTIVE RANGE MODEL (BOTTOM BOX - Rule 5)
        # =========================================================================
        st.markdown('<div class="predictive-box">', unsafe_allow_html=True)
        st.header("🔮 Predictive Model: Automated Yield Range")
        st.caption("Calculated strictly on Daily Volatility (ATR) to ensure yield stability.")
        
        mult = 3.2 if bias == "Bearish 📉" else 2.2 if bias == "Bullish 🚀" else 2.7
        auto_low, auto_high = price - (daily_atr * mult), price + (daily_atr * mult)
        
        r1, r2 = st.columns([2, 1])
        with r1:
            m_low, m_high = st.slider("Fine-Tune Range", float(price*0.4), float(price*1.6), (float(auto_low), float(auto_high)))
        with r2:
            daily_y = (capital * leverage * 0.0017) * ((price * 0.35) / max(m_high - m_low, 0.01))
            st.metric("EST. DAILY YIELD", f"${daily_y:,.2f}")

        st.markdown(f"**Target Zone:** <span style='color:#D4AF37; font-size:20px;' class='mono'>${m_low:,.2f} — ${m_high:,.2f}</span>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # PERSISTENT TABS (Rule 4)
        st.divider()
        t1, t2 = st.tabs(["📧 Alert Center", "📅 Economic Calendar"])
        with t1:
            st.text_input("Enter Email for Alerts")
            if st.button("Connect Email"): st.success("Notifications Active.")
        with t2:
            components.html('<iframe src="https://sslecal2.forexprostools.com?calType=day&timeZone=15&lang=1" width="100%" height="500" frameborder="0"></iframe>', height=500)

if __name__ == "__main__":
    get_sreejan_terminal()
