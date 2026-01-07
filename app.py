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
        # Fetch 250 bars for long-term SMA accuracy
        sol_bars = exchange.fetch_ohlcv('SOL/USD', timeframe='1d', limit=250)
        btc_bars = exchange.fetch_ohlcv('BTC/USD', timeframe='1d', limit=250)
        
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
        df['rsi'] = 100 - (100 / (1 + (gain / loss)))
        df['btc_corr'] = df['close'].rolling(window=30).corr(btc_df['close'])
        
        # ALPHA: Volume POC (Point of Control)
        # Simplified: Price level with max volume in the tail
        recent = df.tail(20)
        df['poc'] = recent.loc[recent['volume'].idxmax()]['close']
        
        fng_res = requests.get("https://api.alternative.me/fng/").json()
        return df, btc_df['close'].iloc[-1], fng_res['data'][0]
    except:
        return None, None, None

def get_sreejan_forecaster():
    # Page Config
    st.set_page_config(page_title="Sreejan Master Pro", layout="wide")
    
    # CSS for Classic Professional Look
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Libre+Baskerville:ital@1&family=Roboto+Mono:wght@300&display=swap');
        .stApp { background-color: #0A0A0B; color: #E0E0E0; }
        .metric-card { background: #111113; padding: 20px; border: 1px solid #222; border-radius: 4px; }
        h1, h2, h3 { font-family: 'Libre+Baskerville', serif; font-weight: 400; color: #D4AF37; }
        .mono { font-family: 'Roboto Mono', monospace; }
        </style>
    """, unsafe_allow_html=True)

    df, btc_price, fng = fetch_institutional_data()

    if df is not None:
        price = df['close'].iloc[-1]
        rsi = df['rsi'].iloc[-1]
        poc = df['poc'].iloc[-1]
        corr = df['btc_corr'].iloc[-1]
        ema20 = df['20_ema'].iloc[-1]
        sma200 = df['200_sma'].iloc[-1]
        vol_24h = df['volume'].iloc[-1] * price

        # --- 1. INSTITUTIONAL TOP BANNER ---
        cols = st.columns([1.2, 1, 1, 1, 1.2])
        with cols[0]: st.markdown(f"<div class='metric-card'><small>BITCOIN CORE</small><br><b class='mono' style='font-size:22px; color:#F7931A;'>₿ {btc_price:,.2f}</b></div>", unsafe_allow_html=True)
        with cols[1]: st.markdown(f"<div class='metric-card'><small>SOLANA NETWORK</small><br><b class='mono' style='font-size:22px; color:#854CE6;'>🟣 {price:,.2f}</b></div>", unsafe_allow_html=True)
        with cols[2]: st.markdown(f"<div class='metric-card'><small>24H VOLUME</small><br><b class='mono' style='font-size:22px; color:#00FFA3;'>${vol_24h/1e9:.2f}B</b></div>", unsafe_allow_html=True)
        with cols[3]: st.markdown(f"<div class='metric-card'><small>BTC CORRELATION</small><br><b class='mono' style='font-size:22px;'>{corr:.2f}</b></div>", unsafe_allow_html=True)
        with cols[4]: st.markdown(f"<div class='metric-card'><small>MARKET SENTIMENT</small><br><b class='mono' style='font-size:22px;'>{fng['value']} - {fng['value_classification']}</b></div>", unsafe_allow_html=True)

        # --- SIDEBAR (LOCKED ELEMENTS) ---
        st.sidebar.title("Configuration")
        capital = st.sidebar.number_input("Capital Allocation ($)", value=10000.0)
        lev = st.sidebar.select_slider("Leverage (Cap 2.0x)", options=[1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0], value=1.5)
        bias_input = st.sidebar.selectbox("Macro Bias", ["Bullish 🚀", "Neutral ⚖️", "Bearish 📉"])
        
        # --- ALPHA INDICATORS ROW ---
        st.divider()
        m_col1, m_col2, m_col3 = st.columns(3)
        with m_col1:
            st.write("Market Heat (RSI)")
            st.progress(min(max(rsi/100, 0.0), 1.0))
            st.caption(f"{'OVERBOUGHT' if rsi > 70 else 'OVERSOLD' if rsi < 30 else 'NEUTRAL'} | {rsi:.1f}")
        with m_col2:
            st.write("Volume POC (Point of Control)")
            st.markdown(f"<h3 style='margin:0;'>${poc:,.2f}</h3>", unsafe_allow_html=True)
            st.caption("Highest volume concentration price")
        with m_col3:
            st.write("Smart Money Flow")
            flow = "Inflow 📥" if price > poc else "Outflow 📤"
            st.markdown(f"<h3 style='margin:0;'>{flow}</h3>", unsafe_allow_html=True)
            st.caption("Net asset movement vs POC")

        # --- EMMANUEL PERP SIGNAL TABLE (LOCKED LOGIC) ---
        st.subheader("Classical Trading Indicative")
        df['tr'] = df[['high', 'low', 'close']].max(axis=1) - df[['high', 'low', 'close']].min(axis=1)
        atr = df['tr'].rolling(window=14).mean().iloc[-1]
        
        # Logic Gate
        if price > sma200 and price > ema20:
            sig, color = "STRONG LONG", "#00FFA3"
            entry, sl, tp1, tp2 = price * 1.002, price - (atr * 1.5), price + (atr * 1.5), price + (atr * 3)
        elif price < sma200 and price < ema20:
            sig, color = "STRONG SHORT", "#FF4B4B"
            entry, sl, tp1, tp2 = price * 0.998, price + (atr * 1.5), price - (atr * 1.5), price - (atr * 3)
        else:
            sig, color = "WAITING / NEUTRAL", "#888"
            entry, sl, tp1, tp2 = price, price - atr, price + atr, price + (atr*2)

        st.markdown(f"""
        <table style="width:100%; border-collapse: collapse; border: 1px solid #333; font-family: 'Roboto Mono';">
            <tr style="background-color: #111;">
                <th style="padding: 15px; border: 1px solid #333;">POSITION BIAS</th>
                <th style="padding: 15px; border: 1px solid #333;">EXECUTION ENTRY</th>
                <th style="padding: 15px; border: 1px solid #333;">HARD STOP LOSS</th>
                <th style="padding: 15px; border: 1px solid #333;">TARGET ALPHA</th>
                <th style="padding: 15px; border: 1px solid #333;">TARGET BETA</th>
            </tr>
            <tr style="text-align: center;">
                <td style="padding: 20px; border: 1px solid #333; color: {color}; font-weight: bold;">{sig}</td>
                <td style="padding: 20px; border: 1px solid #333;">${entry:,.2f}</td>
                <td style="padding: 20px; border: 1px solid #333; color: #FF4B4B;">${sl:,.2f}</td>
                <td style="padding: 20px; border: 1px solid #333; color: #00FFA3;">${tp1:,.2f}</td>
                <td style="padding: 20px; border: 1px solid #333; color: #00FFA3;">${tp2:,.2f}</td>
            </tr>
        </table>
        """, unsafe_allow_html=True)

        # --- TACTICAL CANDLESTICK CHART ---
        st.subheader("Tactical Horizon Analysis")
        hist = df.tail(50)
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=hist['date'], open=hist['open'], high=hist['high'], low=hist['low'], close=hist['close'], name='SOL Price'))
        fig.add_trace(go.Scatter(x=hist['date'], y=hist['20_ema'], name='20 EMA', line=dict(color='#854CE6', width=2)))
        fig.add_trace(go.Scatter(x=hist['date'], y=hist['200_sma'], name='200 SMA', line=dict(color='#FF9900', width=2, dash='dot')))
        fig.add_hline(y=poc, line_color="#D4AF37", line_dash="dash", annotation_text="POC")
        
        # Liquidity Glow (LOCKED)
        heatmap_range = np.linspace(price - (atr*3), price + (atr*3), 20)
        for hr in heatmap_range:
            fig.add_hrect(y0=hr, y1=hr+(atr*0.1), fillcolor="#854CE6", opacity=0.03, line_width=0)
            
        fig.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)

        # --- RANGE FORECASTER (LOCKED) ---
        st.divider()
        st.subheader("Strategic Range Selection")
        liq_price = price * (1 - (1 / lev) * 0.45) if lev > 1.0 else 0
        mult = 3.2 if bias_input == "Bearish 📉" else 2.2 if bias_input == "Bullish 🚀" else 2.7
        auto_low, auto_high = price - (atr * mult), price + (atr * mult)
        
        st.markdown(f"**Institutional Recommendation: ${auto_low:,.2f} — ${auto_high:,.2f}**")
        m_low, m_high = st.slider("Manual Parameter Tune", float(price*0.4), float(price*1.6), (float(auto_low), float(auto_high)), 0.10)
        
        # Liquidation Alert
        if liq_price > 0 and m_low <= liq_price:
            st.error(f"⚠️ LIQUIDATION THREAT: Range bottom (${m_low:,.2f}) is compromised by Liq Price (${liq_price:,.2f}).")

        # YIELD MATRIX (LOCKED: 7 HORIZONS)
        daily_p = (capital * lev * 0.0017) * ((price * 0.35) / max(m_high - m_low, 0.01))
        st.subheader(f"Projected Yield Matrix (Daily Base: ${daily_p:,.2f})")
        y_cols = st.columns(7)
        periods = {"1HR": 1/24, "3HR": 3/24, "6HR": 6/24, "12HR": 0.5, "1 DAY": 1, "1 WEEK": 7, "1 MON": 30}
        for i, (lab, m) in enumerate(periods.items()):
            y_cols[i].metric(lab, f"${(daily_p * m):,.2f}")

        # NEWS FOOTER
        st.divider()
        news_res = requests.get("https://min-api.cryptocompare.com/data/v2/news/?lang=EN").json()
        n_cols = st.columns(5)
        for idx, art in enumerate(news_res['data'][:5]):
            with n_cols[idx]:
                st.markdown(f"**[{art['title'][:40]}...]({art['url']})**")
                st.caption(f"{art['source']} | {datetime.fromtimestamp(art['published_on']).strftime('%H:%M')}")

if __name__ == "__main__":
    get_sreejan_forecaster()
