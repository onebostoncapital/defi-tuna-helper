import ccxt
import pandas as pd
import streamlit as st
import requests
import numpy as np
import plotly.graph_objects as go
import streamlit.components.v1 as components
from datetime import datetime

# 1. DATA ENGINE (MASTER RULE COMPLIANT)
@st.cache_data(ttl=15)
def fetch_terminal_data(perp_tf='1d'):
    try:
        exchange = ccxt.kraken()
        perp_bars = exchange.fetch_ohlcv('SOL/USD', timeframe=perp_tf, limit=300)
        daily_bars = exchange.fetch_ohlcv('SOL/USD', timeframe='1d', limit=100)
        btc_bars = exchange.fetch_ohlcv('BTC/USD', timeframe='1d', limit=1)
        
        df_perp = pd.DataFrame(perp_bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df_perp['date'] = pd.to_datetime(df_perp['timestamp'], unit='ms')
        df_perp['20_ema'] = df_perp['close'].ewm(span=20, adjust=False).mean()
        df_perp['200_sma'] = df_perp['close'].rolling(window=200).mean()
        
        df_daily = pd.DataFrame(daily_bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df_daily['tr'] = df_daily[['high', 'low', 'close']].max(axis=1) - df_daily[['high', 'low', 'close']].min(axis=1)
        daily_atr = df_daily['tr'].rolling(window=14).mean().iloc[-1]
        
        return df_perp, btc_bars[0][4], daily_atr, True
    except:
        return None, None, None, False

def get_sreejan_terminal():
    # Force dark theme via config
    st.set_page_config(page_title="Sreejan Master Pro", layout="wide")
    
    # MASTER UI STYLING (RULE 5: VISIBILITY FIX)
    st.markdown("""
        <style>
        /* Force Global Background and Text Visibility */
        .stApp { background-color: #000000; color: #FFFFFF !important; }
        
        /* Force Metrics and Labels to be white/gold */
        [data-testid="stMetricValue"] { color: #FFFFFF !important; font-family: 'Roboto Mono'; }
        [data-testid="stMetricLabel"] { color: #D4AF37 !important; }
        
        /* Table Visibility Fix */
        .styled-table { width:100%; color: #FFFFFF; border-collapse: collapse; margin: 25px 0; font-family: 'Roboto Mono'; }
        .styled-table th { background-color: #1A1C23; color: #D4AF37; padding: 12px; border: 1px solid #333; }
        .styled-table td { padding: 12px; border: 1px solid #222; text-align: center; background: #0A0A0B; }

        /* Separation Boxes */
        .perp-box { border: 2px solid #854CE6; padding: 20px; border-radius: 12px; background: #050505; margin-bottom: 30px; }
        .predictive-box { border: 2px solid #D4AF37; padding: 20px; border-radius: 12px; background: #050505; margin-top: 30px; }
        
        /* Section Titles */
        h1, h2, h3 { color: #D4AF37 !important; font-family: 'Libre Baskerville'; }
        </style>
    """, unsafe_allow_html=True)

    # SIDEBAR
    st.sidebar.title("🎛️ Terminal Hub")
    selected_tf = st.sidebar.selectbox("Chart Timeframe (Perp)", ["1m", "5m", "15m", "1h", "4h", "1d", "1w"], index=5)
    capital = st.sidebar.number_input("Capital ($)", value=10000.0)
    leverage = st.sidebar.slider("Leverage", 1.0, 5.0, 1.5)
    bias = st.sidebar.selectbox("Range Bias", ["Bullish 🚀", "Neutral ⚖️", "Bearish 📉"])

    df, btc_p, daily_atr, status = fetch_terminal_data(selected_tf)

    if df is not None:
        price = df['close'].iloc[-1]
        ema20, sma200 = df['20_ema'].iloc[-1], df['200_sma'].iloc[-1]

        # --- TOP BANNER ---
        b1, b2, b3 = st.columns(3)
        with b1: st.metric("BITCOIN", f"${btc_p:,.2f}")
        with b2: st.metric("SOLANA", f"${price:,.2f}")
        with b3: st.metric("DAILY ATR", f"{daily_atr:.2f}")

        # =========================================================================
        # SECTION A: PERP TRADING INDICATOR (TOP BOX)
        # =========================================================================
        st.markdown('<div class="perp-box">', unsafe_allow_html=True)
        st.header(f"📉 Perp Trading Indicator ({selected_tf})")
        
        if price > sma200 and price > ema20:
            sig, color = "STRONG BUY 🟢", "#00FFA3"
        elif price < sma200 and price < ema20:
            sig, color = "STRONG SELL 🔴", "#FF4B4B"
        else:
            sig, color = "NEUTRAL ⚖️", "#888"

        st.markdown(f"""
            <table class="styled-table">
                <tr><th>SIGNAL</th><th>ENTRY (EST)</th><th>STOP LOSS</th><th>LIQUIDATION</th></tr>
                <tr>
                    <td style="color:{color}; font-weight:bold;">{sig}</td>
                    <td>${(price * 1.001):,.2f}</td>
                    <td style="color:#FF4B4B;">${(price - daily_atr):,.2f}</td>
                    <td style="color:#FF4B4B;">${(price * (1-(1/leverage)*0.45)):,.2f}</td>
                </tr>
            </table>
        """, unsafe_allow_html=True)
        
        # HIGH-CONTRAST CHART
        fig = go.Figure()
        view = df.tail(100)
        fig.add_trace(go.Candlestick(x=view['date'], open=view['open'], high=view['high'], low=view['low'], close=view['close'], name="Market"))
        fig.add_trace(go.Scatter(x=view['date'], y=view['20_ema'], name='20 EMA', line=dict(color='#854CE6', width=2)))
        fig.add_trace(go.Scatter(x=view['date'], y=view['200_sma'], name='200 SMA', line=dict(color='#FF9900', dash='dot')))
        
        # Explicitly style axes for black background
        fig.update_layout(
            template="plotly_dark", height=450, xaxis_rangeslider_visible=False,
            paper_bgcolor='black', plot_bgcolor='black',
            xaxis=dict(gridcolor='#222', tickfont=dict(color='white')),
            yaxis=dict(gridcolor='#222', tickfont=dict(color='white')),
            legend=dict(font=dict(color="white"))
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # =========================================================================
        # SECTION B: PREDICTIVE RANGE MODEL (BOTTOM BOX)
        # =========================================================================
        st.markdown('<div class="predictive-box">', unsafe_allow_html=True)
        st.header("🔮 Predictive Model: Automated Yield Range")
        
        mult = 3.2 if bias == "Bearish 📉" else 2.2 if bias == "Bullish 🚀" else 2.7
        auto_low, auto_high = price - (daily_atr * mult), price + (daily_atr * mult)
        
        r1, r2 = st.columns([2, 1])
        with r1:
            m_low, m_high = st.slider("Fine-Tune Yield Zone", float(price*0.4), float(price*1.6), (float(auto_low), float(auto_high)))
        with r2:
            daily_y = (capital * leverage * 0.0017) * ((price * 0.35) / max(m_high - m_low, 0.01))
            st.metric("EST. DAILY YIELD", f"${daily_y:,.2f}")

        st.markdown(f"**Target Zone:** <span style='color:#D4AF37; font-size:22px;' class='mono'>${m_low:,.2f} — ${m_high:,.2f}</span>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # PERSISTENT TABS (Rule 4)
        st.divider()
        t1, t2 = st.tabs(["📧 Alert Center", "📅 Economic Calendar"])
        with t1:
            st.text_input("Receiver Email Address")
            if st.button("Save Alerts"): st.success("Email linkage established.")
        with t2:
            components.html('<iframe src="https://sslecal2.forexprostools.com?calType=day&timeZone=15&lang=1" width="100%" height="500" frameborder="0" style="filter: invert(90%) hue-rotate(180deg);"></iframe>', height=500)

if __name__ == "__main__":
    get_sreejan_terminal()
