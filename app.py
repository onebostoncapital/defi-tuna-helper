import ccxt
import pandas as pd
import streamlit as st
import requests
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. ENHANCED DATA ENGINE
@st.cache_data(ttl=15)
def fetch_master_data():
    try:
        exchange = ccxt.kraken()
        # Fetch SOL Data for MAs (Need more bars for 200 SMA)
        sol_bars = exchange.fetch_ohlcv('SOL/USD', timeframe='1d', limit=250)
        df = pd.DataFrame(sol_bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # Emmanuel's Indicators
        df['20_ema'] = df['close'].ewm(span=20, adjust=False).mean()
        df['200_sma'] = df['close'].rolling(window=200).mean()
        
        # BTC & Market Pulse
        btc_ticker = exchange.fetch_ticker('BTC/USD')
        fng_res = requests.get("https://api.alternative.me/fng/").json()
        
        return df, btc_ticker['last'], fng_res['data'][0]
    except:
        return None, None, None

def get_sreejan_forecaster():
    st.set_page_config(page_title="Sreejan Master Pro", page_icon="🟣", layout="wide")

    df, btc_price, fng_data = fetch_master_data()

    # --- TOP BANNER (LOCKED) ---
    if df is not None:
        price = df['close'].iloc[-1]
        vol_24h = df['volume'].iloc[-1] * price
        st.markdown(f"""
            <div style="background-color: #111; padding: 12px; border-radius: 10px; border: 1px solid #333; display: flex; justify-content: space-around;">
                <div><small style="color:#888;">BTC</small><br><b style="color:#FF9900;">${btc_price:,.2f}</b></div>
                <div><small style="color:#888;">SOL</small><br><b style="color:#854CE6;">${price:,.2f}</b></div>
                <div><small style="color:#888;">VOL 24H</small><br><b style="color:#00FFA3;">${vol_24h/1e9:.2f}B</b></div>
                <div><small style="color:#888;">SENTIMENT</small><br><b>{fng_data['value']} ({fng_data['value_classification']})</b></div>
            </div>
        """, unsafe_allow_html=True)

    # --- SIDEBAR (LOCKED RULES) ---
    st.sidebar.header("💰 Investment")
    capital = st.sidebar.number_input("Capital ($)", min_value=10.0, value=10000.0)
    lev_choice = st.sidebar.select_slider("Leverage", options=[1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0], value=1.5)
    btc_trend = st.sidebar.selectbox("Market Bias", ["Bullish 🚀", "Neutral ⚖️", "Bearish 📉"])
    
    # --- EMMANUEL TRADING LOGIC ENGINE ---
    st.divider()
    st.subheader("⚡ Emmanuel-Logic Perp Signal")
    
    ema20 = df['20_ema'].iloc[-1]
    sma200 = df['200_sma'].iloc[-1]
    df['tr'] = df[['high', 'low', 'close']].max(axis=1) - df[['high', 'low', 'close']].min(axis=1)
    atr = df['tr'].rolling(window=14).mean().iloc[-1]

    # Signal Logic
    if price > sma200 and price > ema20:
        bias, color = "STRONG LONG", "#00FFA3"
        entry, sl, tp1, tp2 = price * 1.002, ema20 * 0.99, price + (atr * 1.5), price + (atr * 3)
    elif price < sma200 and price < ema20:
        bias, color = "STRONG SHORT", "#FF4B4B"
        entry, sl, tp1, tp2 = price * 0.998, ema20 * 1.01, price - (atr * 1.5), price - (atr * 3)
    else:
        bias, color = "NEUTRAL / NO TRADE", "#888"
        entry, sl, tp1, tp2 = 0, 0, 0, 0

    # PROFESIONAL SIGNAL TABLE
    st.markdown(f"""
    <table style="width:100%; border-collapse: collapse; border: 1px solid #333; background-color: #0E1117; font-family: sans-serif;">
        <tr style="background-color: #1A1C23;">
            <th style="padding: 15px; border: 1px solid #333; color: #888;">INDICATIVE BIAS</th>
            <th style="padding: 15px; border: 1px solid #333; color: #888;">ENTRY LEVEL</th>
            <th style="padding: 15px; border: 1px solid #333; color: #888;">STOP LOSS</th>
            <th style="padding: 15px; border: 1px solid #333; color: #888;">TAKE PROFIT 1</th>
            <th style="padding: 15px; border: 1px solid #333; color: #888;">TAKE PROFIT 2</th>
        </tr>
        <tr>
            <td style="padding: 20px; border: 1px solid #333; text-align: center; color: {color}; font-weight: bold; font-size: 20px;">{bias}</td>
            <td style="padding: 20px; border: 1px solid #333; text-align: center; font-size: 18px;">${entry:,.2f}</td>
            <td style="padding: 20px; border: 1px solid #333; text-align: center; color: #FF4B4B; font-size: 18px;">${sl:,.2f}</td>
            <td style="padding: 20px; border: 1px solid #333; text-align: center; color: #00FFA3; font-size: 18px;">${tp1:,.2f}</td>
            <td style="padding: 20px; border: 1px solid #333; text-align: center; color: #00FFA3; font-size: 18px;">${tp2:,.2f}</td>
        </tr>
    </table>
    """, unsafe_allow_html=True)

    # --- STRATEGIC CHART (LOCKED) ---
    st.subheader("📊 Tactical Chart (20 EMA & 200 SMA)")
    hist = df.tail(30)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist['date'], y=hist['close'], name='Price', line=dict(color='white', width=2)))
    fig.add_trace(go.Scatter(x=hist['date'], y=hist['20_ema'], name='20 EMA', line=dict(color='#854CE6', width=2)))
    fig.add_trace(go.Scatter(x=hist['date'], y=hist['200_sma'], name='200 SMA', line=dict(color='#FF9900', width=2, dash='dot')))
    
    # Heatmap Glow (Locked)
    heatmap_range = np.linspace(price - (atr*3), price + (atr*3), 30)
    for hr in heatmap_range:
        fig.add_hrect(y0=hr, y1=hr+(atr*0.1), fillcolor="#854CE6", opacity=0.05, line_width=0)

    fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, use_container_width=True)

    # --- RANGE FORECASTER & SLIDER (LOCKED) ---
    st.divider()
    liq_price = price * (1 - (1 / lev_choice) * 0.45) if lev_choice > 1.0 else 0
    mult = 3.2 if btc_trend == "Bearish 📉" else 2.2 if btc_trend == "Bullish 🚀" else 2.7
    auto_low, auto_high = price - (atr * mult), price + (atr * mult)
    
    st.markdown(f"### **Auto-Generated Recommendation: ${auto_low:,.2f} — ${auto_high:,.2f}**")
    manual_range = st.slider("Manual Range Config", min_value=float(price*0.4), max_value=float(price*1.6), value=(float(auto_low), float(auto_high)), step=0.10)
    m_low, m_high = manual_range

    # --- YIELD GRID (LOCKED: 7 HORIZONS) ---
    daily_p = (capital * lev_choice * 0.0017) * ((price * 0.35) / max(m_high - m_low, 0.01))
    st.subheader(f"💰 Yield Matrix (Daily: ${daily_p:,.2f})")
    y_cols = st.columns(7)
    periods = {"1HR": 1/24, "3HR": 3/24, "6HR": 6/24, "12HR": 0.5, "1 DAY": 1, "1 WEEK": 7, "1 MON": 30}
    for i, (lab, m) in enumerate(periods.items()):
        y_cols[i].metric(lab, f"${(daily_p * m):,.2f}")

    # --- NEWS FOOTER (LOCKED) ---
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
