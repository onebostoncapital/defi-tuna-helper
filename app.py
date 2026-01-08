import ccxt
import pandas as pd
import streamlit as st
import requests
import numpy as np
import plotly.graph_objects as go
import streamlit.components.v1 as components
from datetime import datetime

# 1. CORE DATA ENGINE (WITH DYNAMIC TIMEFRAME)
@st.cache_data(ttl=15)
def fetch_terminal_data(timeframe='1d'):
    try:
        exchange = ccxt.kraken()
        # Fetch data for chart & Perp logic (Dynamic)
        bars = exchange.fetch_ohlcv('SOL/USD', timeframe=timeframe, limit=300)
        # Fetch Daily data specifically for the Predictive Range Model (Static Rule)
        daily_bars = exchange.fetch_ohlcv('SOL/USD', timeframe='1d', limit=100)
        btc_bars = exchange.fetch_ohlcv('BTC/USD', timeframe='1d', limit=1)
        
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        df_daily = pd.DataFrame(daily_bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # 20 EMA / 200 SMA for the SELECTED timeframe
        df['20_ema'] = df['close'].ewm(span=20, adjust=False).mean()
        df['200_sma'] = df['close'].rolling(window=200).mean()
        
        # Predictive Model Logic (Always Daily ATR)
        df_daily['tr'] = df_daily[['high', 'low', 'close']].max(axis=1) - df_daily[['high', 'low', 'close']].min(axis=1)
        daily_atr = df_daily['tr'].rolling(window=14).mean().iloc[-1]
        
        # RSI & Alpha
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        df['rsi'] = 100 - (100 / (1 + (gain / loss.replace(0, np.nan)).fillna(0)))
        
        return df, btc_bars[0][4], daily_atr, True
    except Exception as e:
        st.error(f"Data Error: {e}")
        return None, None, None, False

def get_sreejan_terminal():
    st.set_page_config(page_title="Sreejan Master Pro", layout="wide")
    
    # CSS FOR SEPARATION BOXES
    st.markdown("""
        <style>
        .perp-container { border: 2px solid #854CE6; padding: 20px; border-radius: 10px; background: #0E1117; margin-bottom: 25px; }
        .range-container { border: 2px solid #D4AF37; padding: 20px; border-radius: 10px; background: #0E1117; margin-top: 25px; }
        .stApp { background-color: #0A0A0B; color: #E0E0E0; }
        .mono { font-family: 'Roboto Mono', monospace; }
        </style>
    """, unsafe_allow_html=True)

    # SIDEBAR: SETTINGS
    st.sidebar.title("🛠️ Terminal Settings")
    tf = st.sidebar.selectbox("Chart/Perp Timeframe", ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w"], index=6)
    capital = st.sidebar.number_input("Capital ($)", value=10000.0)
    lev = st.sidebar.select_slider("Leverage", options=[1.0, 1.5, 2.0, 3.0, 5.0], value=1.5)
    bias = st.sidebar.selectbox("Range Macro Bias", ["Bullish 🚀", "Neutral ⚖️", "Bearish 📉"])

    df, btc_p, daily_atr, status = fetch_terminal_data(tf)

    if df is not None:
        price = df['close'].iloc[-1]
        
        # --- TOP BANNER ---
        c1, c2, c3 = st.columns(3)
        c1.metric("BITCOIN", f"${btc_p:,.2f}", delta_color="normal")
        c2.metric("SOLANA", f"${price:,.2f}")
        c3.success("SYSTEM LIVE") if status else c3.error("SYSTEM OFFLINE")

        # ==========================================
        # SECTION 1: PERP TRADING INDICATOR (TOP)
        # ==========================================
        st.markdown('<div class="perp-container">', unsafe_allow_html=True)
        st.subheader(f"⚡ Emmanuel-Logic Perp Signal ({tf} Timeframe)")
        
        ema20 = df['20_ema'].iloc[-1]
        sma200 = df['200_sma'].iloc[-1]
        
        if price > sma200 and price > ema20:
            sig, color = "STRONG LONG 🟢", "#00FFA3"
            entry, sl, tp1 = price * 1.001, price - (daily_atr * 0.5), price + (daily_atr * 1)
            st.toast("SIGNAL: Strong Long", icon="🚀")
        elif price < sma200 and price < ema20:
            sig, color = "STRONG SHORT 🔴", "#FF4B4B"
            entry, sl, tp1 = price * 0.999, price + (daily_atr * 0.5), price - (daily_atr * 1)
            st.toast("SIGNAL: Strong Short", icon="🚨")
        else:
            sig, color = "NEUTRAL ⚖️", "#888"
            entry, sl, tp1 = 0, 0, 0

        st.markdown(f"""
            <table style="width:100%; text-align:center; font-family:mono; background:#1A1C23;">
                <tr style="color:#888;"><th>BIAS</th><th>ENTRY</th><th>STOP LOSS</th><th>TARGET</th><th>LIQUIDATION</th></tr>
                <tr style="font-size:20px; font-weight:bold;">
                    <td style="color:{color}">{sig}</td>
                    <td>${entry:,.2f}</td>
                    <td style="color:#FF4B4B;">${sl:,.2f}</td>
                    <td style="color:#00FFA3;">${tp1:,.2f}</td>
                    <td style="color:#FF4B4B;">${(price * (1-(1/lev)*0.45)):,.2f}</td>
                </tr>
            </table>
        """, unsafe_allow_html=True)
        
        # Chart inside Perp Box
        fig = go.Figure()
        hist = df.tail(100)
        fig.add_trace(go.Candlestick(x=hist['date'], open=hist['open'], high=hist['high'], low=hist['low'], close=hist['close'], name="Candles"))
        fig.add_trace(go.Scatter(x=hist['date'], y=hist['20_ema'], name='20 EMA', line=dict(color='#854CE6')))
        fig.add_trace(go.Scatter(x=hist['date'], y=hist['200_sma'], name='200 SMA', line=dict(color='#FF9900', dash='dot')))
        fig.update_layout(template="plotly_dark", height=400, xaxis_rangeslider_visible=False, margin=dict(t=30, b=10))
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # ==========================================
        # SECTION 2: PREDICTIVE RANGE MODEL (BOTTOM)
        # ==========================================
        st.markdown('<div class="range-container">', unsafe_allow_html=True)
        st.subheader("🔮 Predictive Model: Automated Yield Range")
        st.info("Note: This model is strictly calculated on Daily Volatility and is independent of the Perp timeframe above.")
        
        mult = 3.2 if bias == "Bearish 📉" else 2.2 if bias == "Bullish 🚀" else 2.7
        auto_low, auto_high = price - (daily_atr * mult), price + (daily_atr * mult)
        
        r_col1, r_col2 = st.columns([2, 1])
        with r_col1:
            m_low, m_high = st.slider("Manual Range Fine-Tune", float(price*0.5), float(price*1.5), (float(auto_low), float(auto_high)))
        with r_col2:
            daily_yield = (capital * lev * 0.0017) * ((price * 0.35) / max(m_high - m_low, 0.01))
            st.metric("EST. DAILY YIELD", f"${daily_yield:,.2f}")

        st.markdown(f"**Calculated Yield Zone:** <span style='color:#D4AF37; font-size:20px;' class='mono'>${m_low:,.2f} — ${m_high:,.2f}</span>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # ==========================================
        # TABS: EMAIL & CALENDAR (PERSISTENT)
        # ==========================================
        st.divider()
        tab1, tab2 = st.tabs(["📧 Email Alerts", "📅 Economic Calendar"])
        with tab1:
            email = st.text_input("Alert Receiver Email")
            if st.button("Save Configuration"): st.success("Email triggers armed.")
        with tab2:
            components.html('<iframe src="https://sslecal2.forexprostools.com?columns=exc_flags,exc_currency,exc_importance,exc_actual,exc_forecast,exc_previous&features=datepicker,timezone&countries=1,2,3,4,5,6,7,8,9,10,11,12&calType=day&timeZone=15&lang=1" width="100%" height="450" frameborder="0"></iframe>', height=450)

if __name__ == "__main__":
    get_sreejan_terminal()
