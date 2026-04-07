import yfinance as yf
import pandas_ta as ta
import pandas as pd
import requests

def get_all_bei_tickers():
    # Mengambil daftar saham dari sumber publik (Contoh: GitHub Gist atau scraping sederhana)
    # Untuk keakuratan 100%, biasanya kita scraping dari situs IDX, 
    # tapi sebagai shortcut yang stabil, kita gunakan link data csv:
    url = "https://raw.githubusercontent.com/man-c/indo-stock-list/main/stocks.csv"
    try:
        df_list = pd.read_csv(url)
        # Tambahkan .JK di belakang setiap kode
        tickers = [str(s) + ".JK" for s in df_list['Symbol'].tolist()]
        return tickers
    except:
        # Fallback list jika gagal ambil dari internet
        return ["BBCA.JK", "BBRI.JK", "TLKM.JK", "ASII.JK", "BMRI.JK", "BBNI.JK", "GOTO.JK"]

def get_recommendations_v2(full_ticker_list):
    recommendations = []
    
    # Kita proses dalam kelompok kecil (misal 50 saham per batch) agar tidak kena ban
    # Untuk demo, kita batasi dulu ke 100 saham pertama agar aplikasi tidak lemot
    process_list = full_ticker_list[:150] 
    
    # Tarik data masal
    data = yf.download(process_list, period="3mo", interval="1d", group_by='ticker', threads=True)
    
    for ticker in process_list:
        try:
            df = data[ticker].copy()
            df.columns = [col.lower() for col in df.columns]
            df.dropna(inplace=True)
            
            if len(df) < 30: continue

            # Indikator
            df.ta.ema(length=20, append=True)
            df.ta.rsi(length=14, append=True)
            
            last = df.iloc[-1]
            prev = df.iloc[-2]
            
            # Hitung Skor
            score = 0
            # 1. Golden Cross / Price above EMA
            if last['close'] > last['ema_20']: score += 40
            # 2. RSI Rebound (bukan overbought)
            if 40 <= last['rsi_14'] <= 60: score += 30
            # 3. Volume Spike
            if last['volume'] > df['volume'].tail(10).mean(): score += 30

            if score >= 70: # Hanya masukkan yang potensial
                recommendations.append({
                    "Ticker": ticker,
                    "Price": int(last['close']),
                    "Score": score,
                    "RSI": round(last['rsi_14'], 1),
                    "Status": "STRONG BUY" if score == 100 else "WATCHLIST"
                })
        except:
            continue
            
    return sorted(recommendations, key=lambda x: x['Score'], reverse=True)[:10]
