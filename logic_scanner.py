import yfinance as yf
import pandas_ta as ta

def get_stock_data(ticker):
    # 1. Download data
    df = yf.download(ticker, period="1mo", interval="1h")
    
    # 2. FIX: Menghapus MultiIndex jika ada (penting untuk yfinance terbaru)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # 3. FIX: Memastikan nama kolom huruf kecil semua agar pandas-ta tidak bingung
    df.columns = [col.lower() for col in df.columns]
    
    return df

def apply_strategy(df):
    if df is None or df.empty:
        return df
    
    # Sekarang pandas-ta akan menemukan kolom 'close' dengan mudah
    df.ta.ema(length=20, append=True)
    df.ta.rsi(length=14, append=True)
    return df
