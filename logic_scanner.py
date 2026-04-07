import yfinance as yf
import pandas_ta as ta
import pandas as pd  # <--- WAJIB ADA INI

def get_stock_data(ticker):
    # 1. Download data
    df = yf.download(ticker, period="1mo", interval="1h")
    
    if df.empty:
        return df

    # 2. FIX: Menghapus MultiIndex (Sering terjadi di yfinance versi terbaru)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # 3. FIX: Paksa semua kolom jadi huruf kecil agar pandas-ta tidak error
    df.columns = [str(col).lower() for col in df.columns]
    
    return df

def apply_strategy(df):
    if df is None or df.empty:
        return df
    
    # Menghitung EMA dan RSI secara otomatis
    # pandas-ta akan mencari kolom bernama 'close'
    df.ta.ema(length=20, append=True)
    df.ta.rsi(length=14, append=True)
    return df
