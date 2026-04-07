import yfinance as yf
import pandas_ta as ta
import pandas as pd

def get_recommendations(ticker_list):
    # 1. Tarik data semua saham sekaligus (Daily agar akurat untuk swing/besok)
    data = yf.download(ticker_list, period="3mo", interval="1d")
    
    recommendations = []
    
    for ticker in ticker_list:
        try:
            # Ambil data spesifik per ticker
            if len(ticker_list) > 1:
                df = data.xs(ticker, axis=1, level=1).copy()
            else:
                df = data.copy()
            
            df.columns = [col.lower() for col in df.columns]
            if df.empty or len(df) < 50: continue

            # Hitung Indikator Utama
            df.ta.ema(length=20, append=True)
            df.ta.ema(length=50, append=True)
            df.ta.rsi(length=14, append=True)
            
            last = df.iloc[-1]
            prev = df.iloc[-2]
            
            # SISTEM SKORING (0-100)
            score = 0
            reasons = []
            
            # Kriteria 1: Trend Bullish (Harga > EMA 20 & EMA 20 > EMA 50)
            if last['close'] > last['ema_20']:
                score += 40
                reasons.append("Bullish Trend")
            
            # Kriteria 2: Momentum RSI (Ideal 45 - 65, tidak overbought)
            if 45 <= last['rsi_14'] <= 65:
                score += 30
                reasons.append("Ideal Momentum")
            
            # Kriteria 3: Volume Spike (Volume hari ini > Rata-rata volume 5 hari)
            avg_vol = df['volume'].tail(5).mean()
            if last['volume'] > avg_vol:
                score += 30
                reasons.append("Volume Spike")

            recommendations.append({
                "Ticker": ticker,
                "Price": int(last['close']),
                "Score": score,
                "RSI": round(last['rsi_14'], 1),
                "Signal": "STRONG BUY" if score >= 70 else "WATCHLIST",
                "Analysis": ", ".join(reasons)
            })
        except:
            continue
            
    # Urutkan berdasarkan skor tertinggi dan ambil Top 10
    top_picks = sorted(recommendations, key=lambda x: x['Score'], reverse=True)
    return top_picks[:10]
