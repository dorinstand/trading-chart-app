import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import talib
import pandas as pd

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
            # Indicators
            data['RSI'] = talib.RSI(data['Close'], timeperiod=14)
            data['MACD'], data['MACD_signal'], _ = talib.MACD(data['Close'])
            upper, middle, lower = talib.BBANDS(data['Close'], timeperiod=20)
            data['BB_upper'] = upper
            data['BB_middle'] = middle
            data['BB_lower'] = lower
            
            # Candlestick patterns (100 = bullish, -100 = bearish)
            data['Doji'] = talib.CDLDOJI(data['Open'], data['High'], data['Low'], data['Close'])
            data['Hammer'] = talib.CDLHAMMER(data['Open'], data['High'], data['Low'], data['Close'])
            data['Engulfing'] = talib.CDLENGULFING(data['Open'], data['High'], data['Low'], data['Close'])
            data['ShootingStar'] = talib.CDLSHOOTINGSTAR(data['Open'], data['High'], data['Low'], data['Close'])

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

            engulfing_bull = data[data['Engulfing'] == 100]
            if not engulfing_bull.empty:
                fig.add_trace(go.Scatter(x=engulfing_bull.index, y=engulfing_bull['Low'] * 0.98, mode='markers',
                                         marker=dict(symbol='arrow-up', size=14, color='green'),
                                         name='Bullish Engulfing'), row=1, col=1)

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

            # Recent patterns
            patterns = data[(data['Doji'] != 0) | (data['Hammer'] != 0) | 
                            (data['Engulfing'] != 0) | (data['ShootingStar'] != 0)].tail(15)
            if not patterns.empty:
                st.subheader("🕯️ Recent Candlestick Patterns Detected")
                st.dataframe(patterns[['Doji', 'Hammer', 'Engulfing', 'ShootingStar']].replace({100: 'Bullish', -100: 'Bearish', 0: ''}))
            
            st.success("Analysis complete! Remember: This is educational only – not financial advice.")