import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import time

# --- KONFIGURASI ---
st.set_page_config(page_title="Professor's Lab", layout="wide")

def clean_df(df):
    if df.empty: return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    return df

st.title("👨‍🏫 Professor's Trading Lab: Live Investigation")
st.write("Sistem tidak hanya memberikan hasil, tapi menunjukkan proses 'Due Diligence' pada setiap saham.")

# Daftar Sektor (Sama seperti sebelumnya)
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
    
    # Tempat untuk menampilkan log proses
    log_container = st.container()
    
    with log_container:
        st.subheader("🕵️ Live Investigation Log")
        
        for t in tickers:
            # Gunakan st.status untuk menunjukkan proses tiap saham
            with st.status(f"Menganalisis {t}...", expanded=False) as status:
                try:
                    st.write(f"📥 Menarik data histori 1 tahun untuk {t}...")
                    df = yf.download(t, period="1y", interval="1d", progress=False)
                    df = clean_df(df)
                    
                    if df.empty:
                        status.update(label=f"❌ {t}: Data Kosong", state="error")
                        continue

                    # --- PROSES TEKNIKAL ---
                    st.write("🧪 Menghitung Indikator: EMA, MACD, RSI, & Volume MA...")
                    df.ta.ema(length=20, append=True)
                    df.ta.ema(length=50, append=True)
                    df.ta.macd(append=True)
                    df.ta.rsi(length=14, append=True)
                    df['vol_ma'] = df['volume'].rolling(window=20).mean()
                    
                    last = df.iloc[-1]
                    
                    # --- CHECKLIST INVESTIGASI ---
                    score = 0
                    checks = []
                    
                    # 1. Cek Trend
                    if last['ema_20'] > last['ema_50']:
                        score += 25
                        checks.append("✅ **Trend:** Golden Cross EMA20/50 detected.")
                    else:
                        checks.append("❌ **Trend:** Bearish (EMA20 < EMA50).")
                        
                    # 2. Cek Posisi Harga
                    if last['close'] > last['ema_20']:
                        score += 25
                        checks.append(f"✅ **Price:** {int(last['close'])} above Support EMA20.")
                    else:
                        checks.append("❌ **Price:** Below EMA20 (Weakness).")
                        
                    # 3. Cek MACD (Momentum)
                    if last['macd_12_26_9'] > last['macds_12_26_9']:
                        score += 25
                        checks.append("✅ **Momentum:** MACD Bullish Cross.")
                    else:
                        checks.append("❌ **Momentum:** MACD Bearish/Flat.")
                        
                    # 4. Cek Volume (Big Money)
                    if last['volume'] > last['vol_ma']:
                        score += 25
                        checks.append(f"✅ **Volume:** {int(last['volume'])} > MA Volume (Accumulation).")
                    else:
                        checks.append("❌ **Volume:** Below Average (Low Interest).")

                    # Tampilkan Checklist di dalam status
                    for check in checks:
                        st.write(check)

                    # Update status label berdasarkan skor
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
                    
                    status.update(label=f"✅ {t}: Investigation Complete (Score: {score})", state="complete")
                    time.sleep(0.5) # Jeda sedikit agar proses terlihat "manusiawi"
                
                except Exception as e:
                    status.update(label=f"⚠️ {t}: Error {str(e)}", state="error")

    # --- TABEL HASIL AKHIR ---
    st.divider()
    st.header("🏆 Final Recommendation List")
    if all_results:
        final_df = pd.DataFrame(all_results).sort_values("Score", ascending=False)
        
        # Menampilkan tabel dengan gaya profesor
        st.dataframe(final_df, use_container_width=True, hide_index=True)
        
        # Kesimpulan Otomatis
        top_pick = final_df.iloc[0]
        if top_pick['Score'] >= 75:
            st.balloons()
            st.success(f"Berdasarkan investigasi, **{top_pick['Ticker']}** adalah kandidat terkuat untuk entry besok pagi.")
    else:
        st.warning("Tidak ada saham yang lolos kriteria investigasi malam ini.")
