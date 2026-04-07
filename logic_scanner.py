import yfinance as yf
import pandas_ta as ta

def get_stock_data(ticker):
    df = yf.download(ticker, period="7d", interval="15m") # Untuk Daytrade
    return df

def apply_strategy(df):
    # Contoh Strategi: Golden Cross + RSI
    df.ta.ema(length=20, append=True)
    df.ta.ema(length=50, append=True)
    df.ta.rsi(length=14, append=True)
    return df
