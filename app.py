import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta

# Konfigurasi Halaman
st.set_page_config(page_title="Top-Down Market Hunter", layout="wide")

# Fungsi Helper untuk Membersihkan Data yfinance
def clean_df(df):
    if df.empty:
        return df
    # Meratakan MultiIndex jika ada (Fix untuk yfinance terbaru)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    # Paksa kolom jadi huruf kecil
    df.columns = [c.lower() for c in df.columns]
    return df

st.title("🏹 Top-Down Analysis Dashboard")
st.write("Analisis pasar secara terstruktur: Market -> Sector -> Stock.")

# --- STEP 1: MARKET CONDITION (IHSG) ---
st.header("Step 1: Market Condition (IHSG)")
if st.button("📊 Check IHSG Health"):
    with st.spinner("Mengambil data IHSG..."):
        ihsg = yf.download("^JKSE", period="1mo", interval="1d", progress=False)
        ihsg = clean_df(ihsg)
        
        if not ihsg.empty:
            last_price = float(ihsg['close'].iloc[-1])
            prev_price = float(ihsg['close'].iloc[-2])
            change = ((last_price - prev_price) / prev_price) * 100
            
            # Tampilan Metric
            col1, col2 = st.columns([1, 3])
            with col1:
                st.metric("IHSG Close", f"{last_price:.2f}", f"{change:.2f}%")
            with col2:
                st.line_chart(ihsg['close'])
        else:
            st.error("Gagal memuat data IHSG.")

st.divider()

# --- STEP 2: SECTOR SELECTION ---
st.header("Step 2: Choose Sector")
# Daftar sektor yang bisa kamu modifikasi/tambah
sectors = {
    "Perbankan (Big 4)": ["BBCA.JK", "BBRI.JK", "BMRI.JK", "BBNI.JK"],
    "Energi & Batubara": ["ADRO.JK", "ITMG.JK", "PTBA.JK", "MEDC.JK", "HRUM.JK"],
    "Teknologi & Bank Digital": ["GOTO.JK", "ARTO.JK", "BBYB.JK", "BUKA.JK"],
    "Infrastruktur & Telco": ["TLKM.JK", "ISAT.JK", "EXCL.JK", "JSMR.JK"],
    "Consumer Goods": ["ICBP.JK", "INDF.JK", "UNVR.JK", "AMRT.JK", "MYOR.JK"],
    "Metal Mining (Nikel/Emas)": ["ANTM.JK", "TINS.JK", "MDKA.JK", "MBMA.JK", "NCKL.JK"]
}

selected_sector = st.selectbox("Pilih sektor yang sedang ramai/menarik:", list(sectors.keys()))
tickers = sectors[selected_sector]

st.divider()

# --- STEP 3: STOCK DEEP DIVE ---
st.header(f"Step 3: Screening Saham di Sektor {selected_sector}")
if st.button(f"🔍 Scan {len(tickers)} Saham Sektor Ini"):
    with st.spinner(f"Menganalisis teknikal {selected_sector}..."):
        results = []
        for t in tickers:
            try:
                # Ambil data 6 bulan agar EMA 20 & 50 akurat
                df = yf.download(t, period="6mo", interval="1d", progress=False)
                df = clean_df(df)
                
                if df.empty or len(df) < 50:
                    continue
                
                # Hitung Indikator
                df.ta.ema(length=20, append=True)
                df.ta.rsi(length=14, append=True)
                
                last = df.iloc[-1]
                
                # Logika Penilaian (Scoring)
                is_above_ema = last['close'] > last['ema_20']
                rsi_val = last['rsi_14']
                
                # Status: BUY jika di atas EMA dan RSI tidak overbought (>70)
                if is_above_ema and (40 <= rsi_val <= 65):
                    status = "🔥 STRONG BUY"
                elif is_above_ema:
                    status = "👀 WATCHLIST"
                else:
                    status = "❌ AVOID"
                
                results.append({
                    "Ticker": t.replace(".JK", ""),
                    "Price": int(last['close']),
                    "RSI": round(rsi_val, 1),
                    "Above EMA20": "✅" if is_above_ema else "❌",
                    "Status": status
                })
            except:
                continue
        
        if results:
            df_res = pd.DataFrame(results)
            # Menampilkan tabel dengan urutan Status terbaik di atas
            st.table(df_res.sort_values(by="Status"))
            st.success("Analisis selesai. Fokus pada saham dengan status 'STRONG BUY'.")
        else:
            st.warning("Tidak ada data yang berhasil ditarik.")

st.info("💡 Tips: Lakukan screening ini setiap malam setelah market tutup untuk menentukan belanja besok pagi.")
