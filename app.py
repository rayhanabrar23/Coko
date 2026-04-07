import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import time

st.set_page_config(page_title="Professor's Lab V2", layout="wide")

def clean_df(df):
    if df.empty: return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    # Hapus baris yang semua nilainya kosong
    df.dropna(how='all', inplace=True)
    return df

st.title("👨‍🏫 Professor's Trading Lab: Live Investigation")

sectors = {
    "Perbankan (Big 4)": ["BBCA.JK", "BBRI.JK", "BMRI.JK", "BBNI.JK"],
    "Energi & Batubara": ["ADRO.JK", "ITMG.JK", "PTBA.JK", "MEDC.JK", "HRUM.JK"],
    "Metal Mining": ["ANTM.JK", "TINS.JK", "MDKA.JK", "MBMA.JK", "NCKL.JK"],
    "Teknologi": ["GOTO.JK", "ARTO.JK", "BBYB.JK", "BUKA.JK"]
}

selected_sector = st.selectbox("Pilih Sektor Investigasi:", list(sectors.keys()))
tickers = sectors[selected_sector]

if st.button(f"🚀 Mulai Investigasi Sektor {selected_sector}"):
    all_results = []
    
    for t in tickers:
        with st.status(f"Menganalisis {t}...", expanded=False) as status:
            try:
                st.write(f"📥 Downloading data 1 tahun...")
                df = yf.download(t, period="1y", interval="1d", progress=False)
                df = clean_df(df)
                
                if df.empty or len(df) < 50:
                    status.update(label=f"❌ {t}: Data Kurang/Kosong", state="error")
                    continue

                # --- KALKULASI INSTRUMEN ---
                st.write("🧪 Menghitung Indikator...")
                
                # Gunakan metode yang lebih aman untuk memastikan kolom terbuat
                df['ema_20'] = ta.ema(df['close'], length=20)
                df['ema_50'] = ta.ema(df['close'], length=50)
                df['rsi_14'] = ta.rsi(df['close'], length=14)
                
                # MACD Manual handling
                macd_df = ta.macd(df['close'])
                df = pd.concat([df, macd_df], axis=1)
                
                # Beresin nama kolom MACD (Kadang namanya MACD_12_26_9)
                df.columns = [c.lower() for c in df.columns]
                
                # Volume MA
                df['vol_ma'] = df['volume'].rolling(window=20).mean()
                
                # Ambil baris terakhir yang tidak NaN
                df.dropna(subset=['ema_20', 'macd_12_26_9'], inplace=True)
                last = df.iloc[-1]
                
                # --- CHECKLIST ---
                score = 0
                checks = []
                
                # 1. Trend
                if last['ema_20'] > last['ema_50']:
                    score += 25
                    checks.append("✅ **Trend:** Major Trend is Bullish (EMA20 > EMA50).")
                else:
                    checks.append("❌ **Trend:** Major Trend is Weak.")

                # 2. Price Position
                if last['close'] > last['ema_20']:
                    score += 25
                    checks.append(f"✅ **Price:** {last['close']} above Support EMA20.")
                else:
                    checks.append("❌ **Price:** Below EMA20.")

                # 3. MACD Momentum
                # Cari kolom macd yang dinamis namanya
                macd_col = [c for c in df.columns if 'macd' in c and 's' not in c and 'h' not in c][0]
                sig_col = [c for c in df.columns if 'macds' in c][0]
                
                if last[macd_col] > last[sig_col]:
                    score += 25
                    checks.append("✅ **Momentum:** MACD Golden Cross.")
                else:
                    checks.append("❌ **Momentum:** Bearish Momentum.")

                # 4. Volume (VSA)
                if last['volume'] > last['vol_ma']:
                    score += 25
                    checks.append("✅ **Volume:** Above average (Smart Money presence).")
                else:
                    checks.append("❌ **Volume:** Low interest.")

                for check in checks:
                    st.write(check)

                final_action = "❌ NO SETUP"
                if score >= 100: final_action = "💎 HIGH PROBABILITY"
                elif score >= 75: final_action = "✅ SOLID BUY"
                
                all_results.append({
                    "Ticker": t.replace(".JK", ""),
                    "Price": int(last['close']),
                    "Score": score,
                    "RSI": round(last['rsi_14'], 1),
                    "Decision": final_action
                })
                
                status.update(label=f"✅ {t}: Analisis Selesai (Score: {score})", state="complete")
                time.sleep(0.3)

            except Exception as e:
                st.error(f"Detail Error: {str(e)}")
                status.update(label=f"⚠️ {t}: Gagal Analisis", state="error")

    # --- FINAL REPORT ---
    st.divider()
    st.header("🏆 Professor's Summary")
    if all_results:
        st.dataframe(pd.DataFrame(all_results).sort_values("Score", ascending=False), use_container_width=True)
    else:
        st.warning("Belum ada kandidat yang lolos malam ini.")
