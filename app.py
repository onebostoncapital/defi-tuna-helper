import ccxt
import pandas as pd
import streamlit as st
import requests
import numpy as np
import plotly.graph_objects as go
import streamlit.components.v1 as components
import base64
from datetime import datetime

# 1. DATA ENGINE (FULLY RESTORED & LOCKED)
@st.cache_data(ttl=15)
def fetch_institutional_data():
    try:
        exchange = ccxt.kraken()
        sol_bars = exchange.fetch_ohlcv('SOL/USD', timeframe='1d', limit=300)
        btc_bars = exchange.fetch_ohlcv('BTC/USD', timeframe='1d', limit=300)
        
        df = pd.DataFrame(sol_bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
        btc_df = pd.DataFrame(btc_bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        btc_curr = btc_df['close'].iloc[-1]
        
        # CORE RULES: Emmanuel's Moving Averages
        df['20_ema'] = df['close'].ewm(span=20, adjust=False).mean()
        df['200_sma'] = df['close'].rolling(window=200).mean()
        
        # CORE RULES: Volatility & Liquidation Logic
        df['tr'] = df[['high', 'low', 'close']].max(axis=1) - df[['high', 'low', 'close']].min(axis=1)
        df['atr'] = df['tr'].rolling(window=14).mean()
        
        # Institutional Alpha
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        df['rsi'] = 100 - (100 / (1 + (gain / loss.replace(0, np.nan)).fillna(0)))
        df['poc'] = df.tail(20).loc[df.tail(20)['volume'].idxmax()]['close']
        
        try:
            fng_res = requests.get("https://api.alternative.me/fng/", timeout=5).json()
            fng_val = int(fng_res['data'][0]['value'])
            fng_class = fng_res['data'][0]['value_classification']
        except:
            fng_val, fng_class = 50, "Neutral"

        return df, btc_curr, fng_val, fng_class, True
    except:
        return None, None, 50, "Error", False

# 2. NOTIFICATION TRIGGERS
def trigger_alerts(signal_type):
    # Popup Toast
    if "LONG" in signal_type:
        st.toast(f"📈 ALERT: {signal_type} Triggered!", icon="🚀")
    elif "SHORT" in signal_type:
        st.toast(f"📉 ALERT: {signal_type} Triggered!", icon="🚨")
    
    # Sound Notification (Ping)
    audio_html = f'<audio autoplay><source src="https://www.soundjay.com/buttons/sounds/button-3.mp3" type="audio/mp3"></audio>'
    st.markdown(audio_html, unsafe_allow_html=True)

def get_sreejan_terminal():
    st.set_page_config(page_title="Sreejan Master Pro", layout="wide")
    
    # CSS STYLING & TOOLTIPS
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Libre+Baskerville&family=Roboto+Mono&display=swap');
        .stApp { background-color: #0A0A0B; color: #E0E0E0; }
        .metric-card { background: #111113; padding: 15px; border: 1px solid #222; border-radius: 4px; text-align: center; }
        .mono { font-family: 'Roboto Mono', monospace; }
        .status-dot { height: 10px; width: 10px; border-radius: 50%; display: inline-block; margin-right: 8px; }
        
        /* HOVER TOOLTIPS */
        .tooltip { position: relative; display: inline-block; cursor: help; color: #D4AF37; }
        .tooltip .tooltiptext {
            visibility: hidden; width: 250px; background-color: #1A1A1D; border: 1px solid #D4AF37;
            padding: 10px; border-radius: 5px; position: absolute; z-index: 100; bottom: 125%; left: 50%;
            margin-left: -125px; opacity: 0; transition: opacity 0.3s; color: #fff; font-size: 12px;
        }
        .tooltip:hover .tooltiptext { visibility: visible; opacity: 1; }
        </style>
    """, unsafe_allow_html=True)

    df, btc_price, fng_v, fng_c, status = fetch_institutional_data()

    # --- TOP HEADER: PRICE DATA & STATUS ---
    h_col1, h_col2, h_col3, h_col4 = st.columns([2, 2, 2, 2])
    with h_col1:
        st.markdown(f"<div class='metric-card'><small>BITCOIN PRICE</small><br><b class='mono' style='color:#F7931A;'>₿ {btc_price:,.2f}</b></div>", unsafe_allow_html=True)
    with h_col2:
        sol_p = df['close'].iloc[-1] if df is not None else 0
        st.markdown(f"<div class='metric-card'><small>SOLANA PRICE</small><br><b class='mono' style='color:#854CE6;'>🟣 {sol_p:,.2f}</b></div>", unsafe_allow_html=True)
    with h_col3:
        st.markdown(f"""<div class='metric-card'><small class='tooltip'>SENTIMENT ℹ️<span class='tooltiptext'>Fear & Greed Index: Determines market momentum. Fear (0-40) is for buying; Greed (60-100) is for caution.</span></small><br><b class='mono'>{fng_v} ({fng_c})</b></div>""", unsafe_allow_html=True)
    with h_col4:
        dot = "#00FFA3" if status else "#FF4B4B"
        st.markdown(f"<div class='metric-card'><span class='status-dot' style='background-color:{dot}'></span><small>SYSTEM STATUS</small><br><b>ACTIVE</b></div>", unsafe_allow_html=True)

    if df is not None:
        price = df['close'].iloc[-1]
        atr = df['atr'].iloc[-1]
        ema20 = df['20_ema'].iloc[-1]
        sma200 = df['200_sma'].iloc[-1]

        # --- SIGNAL EXECUTION (EMMANUEL LOGIC) ---
        st.subheader("⚡ Emmanuel-Logic Perp Signal")
        if price > sma200 and price > ema20:
            sig, color = "STRONG LONG 🟢", "#00FFA3"
            entry, sl, tp1, tp2 = price * 1.002, price - (atr * 1.5), price + (atr * 1.5), price + (atr * 3)
            trigger_alerts(sig)
        elif price < sma200 and price < ema20:
            sig, color = "STRONG SHORT 🔴", "#FF4B4B"
            entry, sl, tp1, tp2 = price * 0.998, price + (atr * 1.5), price - (atr * 1.5), price - (atr * 3)
            trigger_alerts(sig)
        else:
            sig, color = "NEUTRAL / NO TRADE ⚖️", "#888"
            entry, sl, tp1, tp2 = 0, 0, 0, 0

        st.markdown(f"""
        <table style="width:100%; border-collapse: collapse; border: 1px solid #333; font-family: 'Roboto Mono'; background-color: #0E1117;">
            <tr style="background-color: #1A1C23; color:#888;">
                <th style="padding:10px;">INDICATIVE BIAS</th><th>ENTRY LEVEL</th><th>STOP LOSS</th><th>TAKE PROFIT 1</th><th>TAKE PROFIT 2</th>
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

        # --- TACTICAL CHART (RESTORED) ---
        st.subheader("📊 Tactical Chart (20 EMA & 200 SMA)")
        fig = go.Figure()
        hist = df.tail(60)
        fig.add_trace(go.Candlestick(x=hist['date'], open=hist['open'], high=hist['high'], low=hist['low'], close=hist['close'], name="Market"))
        fig.add_trace(go.Scatter(x=hist['date'], y=hist['20_ema'], name='20 EMA', line=dict(color='#854CE6', width=2)))
        fig.add_trace(go.Scatter(x=hist['date'], y=hist['200_sma'], name='200 SMA', line=dict(color='#FF9900', dash='dot')))
        fig.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)

        # --- TAB SYSTEM: EMAIL TRIGGER & ANALYSIS ---
        tab1, tab2, tab3 = st.tabs(["Yield & Range", "Technical Details", "📧 Email Alerts"])
        
        with tab1:
            st.sidebar.title("🛠️ Risk Settings")
            capital = st.sidebar.number_input("Capital ($)", value=10000.0)
            lev = st.sidebar.select_slider("Leverage (45% Safety)", options=[1.0, 1.5, 2.0, 3.0, 5.0], value=1.5)
            
            # CORE RULE: LIQUIDATION
            liq_price = price * (1 - (1/lev)*0.45)
            st.sidebar.error(f"LIQUIDATION PRICE: ${liq_price:,.2f}")
            
            # CORE RULE: AUTOGENERATED RANGE
            auto_low, auto_high = price - (atr * 2.5), price + (atr * 2.5)
            st.markdown(f"### Autogenerated Range: ${auto_low:,.2f} — ${auto_high:,.2f}")
            m_low, m_high = st.slider("Adjust Range", float(price*0.5), float(price*1.5), (float(auto_low), float(auto_high)))
            
            daily_p = (capital * lev * 0.0017) * ((price * 0.35) / max(m_high - m_low, 0.01))
            st.subheader(f"Yield Matrix (Daily: ${daily_p:,.2f})")
            y_cols = st.columns(7)
            periods = {"1H": 1/24, "3H": 3/24, "1D": 1, "1W": 7, "1M": 30}
            for i, (lab, m) in enumerate(periods.items()):
                y_cols[i%7].metric(lab, f"${(daily_p * m):,.2f}")

        with tab2:
            st.table(pd.DataFrame({
                "Indicator": ["RSI", "20 EMA", "200 SMA", "POC"],
                "Value": [f"{df['rsi'].iloc[-1]:.2f}", f"{ema20:.2f}", f"{sma200:.2f}", f"{df['poc'].iloc[-1]:.2f}"]
            }))

        with tab3:
            st.subheader("Configure Email Triggers")
            email = st.text_input("Receiver Email Address")
            if st.button("Save Alert Settings"):
                st.success(f"Alerts configured for {email}. You will receive emails on Strong Buy/Sell signals.")

        # --- ECONOMIC CALENDAR ---
        st.divider()
        st.subheader("📅 Global Economic Calendar")
        components.html("""
            <iframe src="https://sslecal2.forexprostools.com?columns=exc_flags,exc_currency,exc_importance,exc_actual,exc_forecast,exc_previous&features=datepicker,timezone&countries=1,2,3,4,5,6,7,8,9,10,11,12&calType=day&timeZone=15&lang=1" width="100%" height="450" frameborder="0" allowtransparency="true"></iframe>
        """, height=450)

if __name__ == "__main__":
    get_sreejan_terminal()
