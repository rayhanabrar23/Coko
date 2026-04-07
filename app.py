import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import time

st.set_page_config(page_title="Professor's Strategy Lab", layout="wide")

def clean_df(df):
    if df.empty: return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    df.dropna(how='all', inplace=True)
    return df

st.title("👨‍🏫 Professor's Lab: High Probability Setup")
st.write("Sistem Analisis Terpadu: Trend + Momentum + Volume + Risk Management")

sectors = {
    "Perbankan (Big 4)": ["BBCA.JK", "BBRI.JK", "BMRI.JK", "BBNI.JK"],
    "Energi & Batubara": ["ADRO.JK", "ITMG.JK", "PTBA.JK", "MEDC.JK", "HRUM.JK"],
    "Metal Mining": ["ANTM.JK", "TINS.JK", "MDKA.JK", "MBMA.JK", "NCKL.JK"],
    "Teknologi": ["GOTO.JK", "ARTO.JK", "BBYB.JK", "BUKA.JK"]
}

selected_sector = st.selectbox("Pilih Sektor untuk Investigasi:", list(sectors.keys()))
tickers = sectors[selected_sector]

if st.button(f"🔍 Jalankan Investigasi & Hitung Support/Resistance"):
    all_results = []
    
    for t in tickers:
        with st.status(f"Menganalisis {t}...", expanded=False) as status:
            try:
                st.write(f"📥 Mengambil data historis...")
                df = yf.download(t, period="1y", interval="1d", progress=False)
                df = clean_df(df)
                
                if df.empty or len(df) < 50:
                    status.update(label=f"❌ {t}: Data Tidak Mencukupi", state="error")
                    continue

                # --- 1. KALKULASI INDIKATOR UTAMA ---
                df['ema_20'] = ta.ema(df['close'], length=20)
                df['ema_50'] = ta.ema(df['close'], length=50)
                df['rsi_14'] = ta.rsi(df['close'], length=14)
                df['vol_ma'] = df['volume'].rolling(window=20).mean()
                
                # MACD
                macd_df = ta.macd(df['close'])
                df = pd.concat([df, macd_df], axis=1)
                df.columns = [c.lower() for c in df.columns]
                
                # --- 2. KALKULASI RISK MANAGEMENT (ATR & PIVOT) ---
                # ATR untuk Stop Loss (2x Volatilitas)
                df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
                
                # Pivot Points untuk Target Resistance (Classic)
                prev_day = df.iloc[-2] # Menggunakan data kemarin untuk pivot hari ini
                pivot = (prev_day['high'] + prev_day['low'] + prev_day['close']) / 3
                r1 = (2 * pivot) - prev_day['low']
                r2 = pivot + (prev_day['high'] - prev_day['low'])
                
                df.dropna(subset=['ema_20', 'macd_12_26_9', 'atr'], inplace=True)
                last = df.iloc[-1]
                
                # --- 3. SCORING LOGIC ---
                score = 0
                checks = []
                
                if last['ema_20'] > last['ema_50']: score += 25
                if last['close'] > last['ema_20']: score += 25
                
                macd_col = [c for c in df.columns if 'macd' in c and 's' not in c and 'h' not in c][0]
                sig_col = [c for c in df.columns if 'macds' in c][0]
                if last[macd_col] > last[sig_col]: score += 25
                
                if last['volume'] > last['vol_ma']: score += 25

                # --- 4. PENENTUAN SL & TP ---
                # Stop Loss = Harga saat ini - (2 * ATR) -> Dibulatkan ke fraksi harga saham (kelipatan 25/50)
                stop_loss = last['close'] - (last['atr'] * 2)
                # Target Profit = Resistance 2 (R2) dari Pivot
                target_profit = r2

                all_results.append({
                    "Ticker": t.replace(".JK", ""),
                    "Price": int(last['close']),
                    "Score": score,
                    "RSI": round(last['rsi_14'], 1),
                    "Stop Loss (SL)": int(stop_loss),
                    "Target Price (TP)": int(target_profit),
                    "Risk:Reward": round((target_profit - last['close']) / (last['close'] - stop_loss), 2),
                    "Decision": "💎 HIGH PROB" if score >= 100 else "✅ SOLID" if score >= 75 else "🟡 WAIT"
                })
                
                status.update(label=f"✅ {t} Selesai", state="complete")

            except Exception as e:
                status.update(label=f"⚠️ {t} Error", state="error")

    # --- FINAL DISPLAY ---
    st.divider()
    st.header("🏆 Final Trading Plan")
    if all_results:
        res_df = pd.DataFrame(all_results).sort_values("Score", ascending=False)
        
        # Tampilkan tabel dengan highlight
        st.dataframe(res_df.style.apply(lambda x: ['background-color: #155724' if x.Decision == "💎 HIGH PROB" else '' for i in x], axis=1), 
                     use_container_width=True, hide_index=True)
        
        st.info("""
        **Cara Membaca Plan:**
        1. **Target Price (TP):** Area Resistance terdekat. Jika harga sampai sini, amankan profit.
        2. **Stop Loss (SL):** Batas toleransi. Jika harga turun di bawah ini, tren sudah patah.
        3. **Risk:Reward:** Cari yang nilainya > 1. Artinya potensi untung lebih besar dari risiko rugi.
        """)
    else:
        st.warning("Gagal memproses data. Silakan coba sektor lain.")
