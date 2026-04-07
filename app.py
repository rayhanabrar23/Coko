import yfinance as yf
import pandas_ta as ta
import pandas as pd

def get_recommendations_v2(ticker_list):
    recommendations = []
    
    # Ambil data satu-satu biar stabil
    for ticker in ticker_list:
        try:
            df = yf.download(ticker, period="6mo", interval="1d", progress=False) # Period diperpanjang ke 6mo
            
            if df.empty: continue
            
            # Beresin kolom MultiIndex yfinance
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df.columns = [col.lower() for col in df.columns]
            
            # Hitung Indikator
            df.ta.ema(length=20, append=True)
            df.ta.rsi(length=14, append=True)
            
            # Cek apakah indikator berhasil dibuat
            if 'ema_20' not in df.columns:
                continue
                
            last = df.iloc[-1]
            
            # KITA LONGGARKAN FILTERNYA BIAR PASTI MUNCUL HASILNYA
            score = 0
            if last['close'] > last['ema_20']: score += 50
            if 30 <= last['rsi_14'] <= 70: score += 50 # Rentang RSI lebih luas

            # Masukkan semua saham yang berhasil diproses ke list
            recommendations.append({
                "Ticker": ticker.replace(".JK", ""),
                "Price": int(last['close']),
                "Score": score,
                "RSI": round(last['rsi_14'], 1),
                "Status": "READY" if score >= 50 else "MONITOR"
            })
        except:
            continue
            
    # Urutkan berdasarkan skor tertinggi
    return sorted(recommendations, key=lambda x: x['Score'], reverse=True)[:15]
