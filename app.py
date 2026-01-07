import ccxt
import pandas as pd
import streamlit as st
import requests
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. ENHANCED DATA ENGINE (Prices, MAs, RSI)
@st.cache_data(ttl=15)
def fetch_master_data():
    try:
        exchange = ccxt.kraken()
        # Fetch 250 bars to ensure 200 SMA is calculated
        sol_bars = exchange.fetch_ohlcv('SOL/USD', timeframe='1d', limit=250)
        df = pd.DataFrame(sol_bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # INDICATORS
        df['20_ema'] = df['close'].ewm(span=20, adjust=False).mean()
        df['200_sma'] = df['close'].rolling(window=200).mean()
        
        # RSI Calculation (Relative Strength Index)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # BTC & Market Pulse
        btc_ticker = exchange.fetch_ticker('BTC/USD')
        fng_res = requests.get("https://api.alternative.me/fng/").json()
        
        return df, btc_ticker['last'], fng_res['data'][0]
    except Exception as e:
        st.error(f"Data Fetch Error: {e}")
        return None, None, None

def get_sreejan_forecaster():
    st.set_page_config(page_title="Sreejan Master Pro", page_icon="🟣", layout="wide")

    df, btc_price, fng_data = fetch_master_data()

    if df is not None:
        price = df['close'].iloc[-1]
        rsi = df['rsi'].iloc[-1]
        vol_24h = df['volume'].iloc[-1] * price
        
        # --- 1. PROFESSIONAL TOP BANNER ---
        st.markdown(f"""
            <div style="background-color: #0E1117; padding: 15px; border-radius: 12px; border: 1px solid #333; display: flex; justify-content: space-around; align-items: center;">
                <div style="text-align: center;"><p style="margin:0; color:#888; font-size:12px;">BITCOIN (BTC)</p><b style="font-size:20px; color:#FF9900;">₿ ${btc_price:,.2f}</b></div>
                <div style="text-align: center;"><p style="margin:0; color:#888; font-size:12px;">SOLANA (SOL)</p><b style="font-size:20px; color:#854CE6;">🟣 ${price:,.2f}</b></div>
                <div style="text-align: center;"><p style="margin:0; color:#888; font-size:12px;">SOL 24H VOLUME</p><b style="font-size:20px; color:#00FFA3;">📊 ${vol_24h/1e9:.2f}B</b></div>
                <div style="text-align: center;"><p style="margin:0; color:#888; font-size:12px;">FEAR & GREED</p><b style="font-size:20px; color:#FFF;">🎭 {fng_data['value']} ({fng_data['value_classification']})</b></div>
            </div>
        """, unsafe_allow_html=True)

        # --- 2. MARKET HEAT GAUGE (RSI) ---
        heat_label = "OVERBOUGHT 🔴" if rsi > 70 else "OVERSOLD 🟢" if rsi < 30 else "NEUTRAL ⚖️"
        heat_color = "#FF4B4B" if rsi > 70 else "#00FFA3" if rsi < 30 else "#854CE6"
        
        st.markdown(f"<div style='margin-top:20px; text-align:center;'>Market Heat: <span style='color:{heat_color}; font-weight:bold;'>{heat_label} (RSI: {rsi:.1f})</span></div>", unsafe_allow_html=True)
        st.progress(min(max(rsi/100, 0.0), 1.0))

        # --- SIDEBAR (LOCKED ELEMENTS) ---
        st.sidebar.header("💰 Investment")
        capital = st.sidebar.number_input("Capital Amount ($)", min_value=10.0, value=10000.0)
        lev_choice = st.sidebar.select_slider("Select Leverage", options=[1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0], value=1.5)
        btc_trend = st.sidebar.selectbox("Market Sentiment", ["Bullish 🚀", "Neutral ⚖️", "Bearish 📉"])
        if st.sidebar.button("🔄 Force Data Refresh"):
            st.cache_data.clear()
            st.rerun()

        # --- EMMANUEL PERP SIGNAL LOGIC ---
        ema20 = df['20_ema'].iloc[-1]
        sma200 = df['200_sma'].iloc[-1] if not pd.isna(df['200_sma'].iloc[-1]) else ema20
        df['tr'] = df[['high', 'low', 'close']].max(axis=1) - df[['high', 'low', 'close']].min(axis=1)
        atr = df['tr'].rolling(window=14).mean().iloc[-1]

        if price > sma200 and price > ema20:
            bias, b_color = "STRONG LONG 🟢", "#00FFA3"
            entry, sl, tp1, tp2 = price * 1.002, price - (atr * 1.2), price + (atr * 1.5), price + (atr * 3)
        elif price < sma200 and price < ema20:
            bias, b_color = "STRONG SHORT 🔴", "#FF4B4B"
            entry, sl, tp1, tp2 = price * 0.998, price + (atr * 1.2), price - (atr * 1.5), price - (atr * 3)
        else:
            bias, b_color = "NEUTRAL / NO TRADE ⚪", "#888"
            entry, sl, tp1, tp2 = price, price - atr, price + atr, price + (atr*2)

        st.subheader("⚡ Emmanuel-Logic Perp Signal")
        st.markdown(f"""
        <table style="width:100%; border-collapse: collapse; background-color: #0E1117; border: 1px solid #333;">
            <tr style="background-color: #1A1C23; color: #888;">
                <th style="padding: 15px; border: 1px solid #333;">INDICATIVE BIAS</th>
                <th style="padding: 15px; border: 1px solid #333;">ENTRY LEVEL</th>
                <th style="padding: 15px; border: 1px solid #333;">STOP LOSS</th>
                <th style="padding: 15px; border: 1px solid #333;">TARGET 1</th>
                <th style="padding: 15px; border: 1px solid #333;">TARGET 2</th>
            </tr>
            <tr style="text-align: center; font-size: 18px;">
                <td style="padding: 20px; border: 1px solid #333; color: {b_color}; font-weight: bold;">{bias}</td>
                <td style="padding: 20px; border: 1px solid #333;">${entry:,.2f}</td>
                <td style="padding: 20px; border: 1px solid #333; color: #FF4B4B;">${sl:,.2f}</td>
                <td style="padding: 20px; border: 1px solid #333; color: #00FFA3;">${tp1:,.2f}</td>
                <td style="padding: 20px; border: 1px solid #333; color: #00FFA3;">${tp2:,.2f}</td>
            </tr>
        </table>
        """, unsafe_allow_html=True)

        # --- INTERACTIVE TACTICAL CHART ---
        st.subheader("📊 Interactive Tactical Chart (SOL/USD)")
        hist = df.tail(40)
        fig = go.Figure()

        # Candles
        fig.add_trace(go.Candlestick(
            x=hist['date'], open=hist['open'], high=hist['high'], low=hist['low'], close=hist['close'], name='SOL Price'
        ))
        
        # MAs
        fig.add_trace(go.Scatter(x=hist['date'], y=hist['20_ema'], name='20 EMA', line=dict(color='#854CE6', width=2)))
        fig.add_trace(go.Scatter(x=hist['date'], y=hist['200_sma'], name='200 SMA', line=dict(color='#FF9900', width=2, dash='dot')))

        # RULE: Liquidity Heatmap Glow (Locked)
        heatmap_range = np.linspace(price - (atr*3), price + (atr*3), 20)
        for hr in heatmap_range:
            fig.add_hrect(y0=hr, y1=hr+(atr*0.1), fillcolor="#854CE6", opacity=0.03, line_width=0)

        fig.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig, use_container_width=True)

        # --- LIQUIDITY RANGE & YIELD (LOCKED ELEMENTS) ---
        st.divider()
        st.subheader("🎯 Liquidity Range & Yield")
        mult = 3.2 if btc_trend == "Bearish 📉" else 2.2 if btc_trend == "Bullish 🚀" else 2.7
        auto_low, auto_high = price - (atr * mult), price + (atr * mult)
        
        st.markdown(f"### **Auto-Generated Range: ${auto_low:,.2f} — ${auto_high:,.2f}**")
        manual_range = st.slider("Manual Range Config", min_value=float(price*0.3), max_value=float(price*1.7), value=(float(auto_low), float(auto_high)), step=0.10)
        m_low, m_high = manual_range

        # Yield Grid (LOCKED: 7 Horizons)
        daily_p = (capital * lev_choice * 0.0017) * ((price * 0.35) / max(m_high - m_low, 0.01))
        st.markdown(f"#### 💰 Estimated Yield (Daily: ${daily_p:,.2f})")
        y_cols = st.columns(7)
        periods = {"1HR": 1/24, "3HR": 3/24, "6HR": 6/24, "12HR": 0.5, "1 DAY": 1, "1 WEEK": 7, "1 MON": 30}
        for i, (lab, m) in enumerate(periods.items()):
            y_cols[i].metric(lab, f"${(daily_p * m):,.2f}")

        # --- NEWS FOOTER ---
        st.divider()
        st.subheader("📰 Market Alpha")
        news_res = requests.get("https://min-api.cryptocompare.com/data/v2/news/?lang=EN").json()
        n_cols = st.columns(5)
        for idx, art in enumerate(news_res['data'][:5]):
            with n_cols[idx]:
                st.markdown(f"**[{art['title'][:40]}...]({art['url']})**")
                st.caption(art['source'])

if __name__ == "__main__":
    get_sreejan_forecaster()
