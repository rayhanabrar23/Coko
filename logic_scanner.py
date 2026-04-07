import yfinance as yf
import pandas_ta as ta
import pandas as pd

def get_recommendations_v2(ticker_list):
    recommendations = []
    
    # Ambil data masal (Batasi 100 per proses agar tidak error)
    # Kita pakai threads=True agar cepat
    data = yf.download(ticker_list, period="3mo", interval="1d", group_by='ticker', threads=True)
    
    for ticker in ticker_list:
        try:
            # Proteksi jika yfinance mengembalikan data kosong untuk ticker tertentu
            if ticker not in data or data[ticker].empty:
                continue
                
            df = data[ticker].copy()
            df.columns = [col.lower() for col in df.columns]
            df.dropna(inplace=True)
            
            if len(df) < 20: continue

            # Indikator Dasar
            df.ta.ema(length=20, append=True)
            df.ta.rsi(length=14, append=True)
            
            last = df.iloc[-1]
            prev = df.iloc[-2]
            
            # Sistem Skoring
            score = 0
            # 1. Trend (Harga > EMA20)
            if last['close'] > last['ema_20']: score += 40
            # 2. Momentum (RSI Rebound 40-65)
            if 40 <= last['rsi_14'] <= 65: score += 30
            # 3. Volume (Volume hari ini > Rata-rata 5 hari)
            if last['volume'] > df['volume'].tail(5).mean(): score += 30

            # Masukkan hasil jika skor cukup baik
            recommendations.append({
                "Ticker": ticker.replace(".JK", ""),
                "Price": int(last['close']),
                "Score": score,
                "RSI": round(last['rsi_14'], 1),
                "Signal": "STRONG BUY" if score >= 70 else "WATCHLIST"
            })
        except:
            continue
            
    # Urutkan berdasarkan skor tertinggi
    return sorted(recommendations, key=lambda x: x['Score'], reverse=True)[:10]
