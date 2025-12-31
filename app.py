import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD
from ta.volatility import BollingerBands

# --- Manual Candlestick Pattern Detection Functions ---
def detect_doji(open_, high, low, close, tolerance=0.1):
    """Detect Doji: body very small compared to range"""
    body = abs(open_ - close)
    range_ = high - low
    return body <= tolerance * range_

def detect_hammer(open_, high, low, close):
    """Detect Bullish Hammer: small upper body, long lower shadow"""
    body = abs(open_ - close)
    range_ = high - low
    lower_shadow = min(open_, close) - low
    upper_shadow = high - max(open_, close)
    return (lower_shadow >= 2 * body) and (upper_shadow <= body) and (body <= 0.3 * range_)

def detect_shooting_star(open_, high, low, close):
    """Detect Bearish Shooting Star: small lower body, long upper shadow"""
    body = abs(open_ - close)
    range_ = high - low
    upper_shadow = high - max(open_, close)
    lower_shadow = min(open_, close) - low
    return (upper_shadow >= 2 * body) and (lower_shadow <= body) and (body <= 0.3 * range_)

def detect_bullish_engulfing(open_, high, low, close):
    """Detect Bullish Engulfing: current green candle fully engulfs previous red candle"""
    prev_open, prev_close = open_.shift(1), close.shift(1)
    bullish_engulf = (
        (prev_close < prev_open) &  # previous bearish
        (close > open_) &           # current bullish
        (open_ < prev_close) &      # opens below previous close
        (close > prev_open)         # closes above previous open
    )
    return bullish_engulf

# -------------------------------------------------------

st.set_page_config(page_title="Trading Chart Analyzer", layout="wide")
st.title("📈 Trading Chart Pattern & Indicator Detector")

st.markdown("""
Enter a stock ticker, select timeframe, and analyze candlestick charts with technical indicators and pattern detection.
""")

col1, col2 = st.columns(2)
with col1:
    ticker = st.text_input("Stock Ticker", value="AAPL").upper()
with col2:
    period = st.selectbox("Period", ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "max"], index=5)

interval = st.selectbox("Interval", ["1m", "5m", "15m", "30m", "1h", "1d"], index=5)

if st.button("🔍 Load & Analyze Chart"):
    with st.spinner("Downloading data and analyzing..."):
        data = yf.download(ticker, period=period, interval=interval, progress=False)
        
        if data.empty or len(data) < 50:
            st.error("No data found or insufficient data for this ticker/period.")
        else:
            # Indicators (using 'ta' library - reliable on Streamlit Cloud)
            data['RSI'] = RSIIndicator(close=data['Close'], window=14).rsi()
            macd = MACD(close=data['Close'])
            data['MACD'] = macd.macd()
            data['MACD_signal'] = macd.macd_signal()

            bb = BollingerBands(close=data['Close'], window=20, window_dev=2)
            data['BB_upper'] = bb.bollinger_hband()
            data['BB_middle'] = bb.bollinger_mavg()
            data['BB_lower'] = bb.bollinger_lband()

            # Candlestick Patterns (manual detection - returns 100 for bullish, -100 for bearish where applicable)
            data['Doji'] = detect_doji(data['Open'], data['High'], data['Low'], data['Close']).astype(int) * 100
            data['Hammer'] = detect_hammer(data['Open'], data['High'], data['Low'], data['Close']).astype(int) * 100
            data['ShootingStar'] = detect_shooting_star(data['Open'], data['High'], data['Low'], data['Close']).astype(int) * (-100)
            data['Engulfing'] = detect_bullish_engulfing(data['Open'], data['High'], data['Low'], data['Close']).astype(int) * 100

            # Plot
            fig = make_subplots(
                rows=4, cols=1,
                shared_xaxes=True,
                subplot_titles=("Candlestick + Bollinger Bands", "MACD", "RSI", "Volume"),
                row_heights=[0.5, 0.15, 0.15, 0.15],
                vertical_spacing=0.05
            )

            # Candlestick
            fig.add_trace(go.Candlestick(
                x=data.index, open=data['Open'], high=data['High'],
                low=data['Low'], close=data['Close'], name="Price"
            ), row=1, col=1)

            # Bollinger Bands
            fig.add_trace(go.Scatter(x=data.index, y=data['BB_upper'], name="Upper BB", line=dict(color="gray", dash="dash")), row=1, col=1)
            fig.add_trace(go.Scatter(x=data.index, y=data['BB_middle'], name="Middle BB", line=dict(color="blue")), row=1, col=1)
            fig.add_trace(go.Scatter(x=data.index, y=data['BB_lower'], name="Lower BB", line=dict(color="gray", dash="dash")), row=1, col=1)

            # Pattern markers
            hammer = data[data['Hammer'] == 100]
            if not hammer.empty:
                fig.add_trace(go.Scatter(x=hammer.index, y=hammer['Low'] * 0.98, mode='markers',
                                         marker=dict(symbol='triangle-up', size=15, color='lime'),
                                         name='Bullish Hammer'), row=1, col=1)

            doji = data[data['Doji'] == 100]
            if not doji.empty:
                fig.add_trace(go.Scatter(x=doji.index, y=doji['Close'], mode='markers',
                                         marker=dict(symbol='diamond', size=12, color='yellow'),
                                         name='Doji'), row=1, col=1)

            engulfing = data[data['Engulfing'] == 100]
            if not engulfing.empty:
                fig.add_trace(go.Scatter(x=engulfing.index, y=engulfing['Low'] * 0.98, mode='markers',
                                         marker=dict(symbol='arrow-up', size=14, color='green'),
                                         name='Bullish Engulfing'), row=1, col=1)

            shooting = data[data['ShootingStar'] == -100]
            if not shooting.empty:
                fig.add_trace(go.Scatter(x=shooting.index, y=shooting['High'] * 1.02, mode='markers',
                                         marker=dict(symbol='triangle-down', size=15, color='red'),
                                         name='Shooting Star'), row=1, col=1)

            # MACD
            fig.add_trace(go.Scatter(x=data.index, y=data['MACD'], name="MACD"), row=2, col=1)
            fig.add_trace(go.Scatter(x=data.index, y=data['MACD_signal'], name="Signal"), row=2, col=1)

            # RSI
            fig.add_trace(go.Scatter(x=data.index, y=data['RSI'], name="RSI", line=dict(color="purple")), row=3, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)

            # Volume
            fig.add_trace(go.Bar(x=data.index, y=data['Volume'], name="Volume"), row=4, col=1)

            fig.update_layout(height=1000, xaxis_rangeslider_visible=False, title=f"{ticker} Analysis")
            st.plotly_chart(fig, use_container_width=True)

            # Recent patterns table
            patterns = data[(data['Doji'] != 0) | (data['Hammer'] != 0) | 
                            (data['Engulfing'] != 0) | (data['ShootingStar'] != 0)].tail(15)
            if not patterns.empty:
                st.subheader("🕯️ Recent Candlestick Patterns Detected")
                display_patterns = patterns[['Doji', 'Hammer', 'Engulfing', 'ShootingStar']].replace({100: 'Bullish', -100: 'Bearish', 0: ''})
                st.dataframe(display_patterns)

            st.success("Analysis complete! Educational purposes only – not financial advice.")