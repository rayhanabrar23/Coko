import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Professor's Top-Down Lab", layout="wide")

# --- DATABASE SEKTOR & INDUSTRI (Contoh Struktur) ---
# Di dunia nyata, ini bisa ditarik dari API, tapi kita buat mapping manual yang solid dulu
market_data = {
    "FINANCE": {
        "Big Banks": ["BBCA.JK", "BBRI.JK", "BMRI.JK", "BBNI.JK"],
        "Digital Banks": ["ARTO.JK", "BBYB.JK", "BBNK.JK"]
    },
    "ENERGY": {
        "Coal": ["ADRO.JK", "ITMG.JK", "PTBA.JK", "HRUM.JK"],
        "Oil & Gas": ["MEDC.JK", "AKRA.JK", "ENRG.JK"]
    },
    "BASIC INFO": {
        "Metal Mining": ["ANTM.JK", "TINS.JK", "MDKA.JK", "MBMA.JK"],
        "Cement": ["SMGR.JK", "INTP.JK"]
    },
    "TECH": {
        "Internet Services": ["GOTO.JK", "BUKA.JK"],
        "Data Center": ["DCII.JK", "MTDL.JK"]
    }
}

def clean_df(df):
    if df.empty: return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    return df

# --- STEP 1: MONITORING IHSG (BIRD'S EYE VIEW) ---
st.title("🏛️ Professor's Top-Down Terminal")

st.subheader("1. Market Overview (IHSG)")
with st.expander("Lihat Kondisi IHSG Hari Ini", expanded=True):
    ihsg = yf.download("^JKSE", period="6mo", interval="1d", progress=False)
    ihsg = clean_df(ihsg)
    if not ihsg.empty:
        last_ihsg = ihsg.iloc[-1]['close']
        prev_ihsg = ihsg.iloc[-2]['close']
        diff = last_ihsg - prev_ihsg
        st.metric("IHSG (Composite)", f"{last_ihsg:.2f}", f"{diff:.2f} ({ (diff/prev_ihsg)*100 :.2f}%)")
        
        fig_ihsg = go.Figure(data=[go.Scatter(x=ihsg.index, y=ihsg['close'], fill='tozeroy', name="IHSG")])
        fig_ihsg.update_layout(height=300, template='plotly_dark', margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig_ihsg, use_container_width=True)

st.divider()

# --- STEP 2: SECTOR & INDUSTRY SELECTION ---
st.subheader("2. Sector & Industry Explorer")
c1, c2 = st.columns(2)

with c1:
    selected_sector = st.selectbox("Pilih Sektor:", list(market_data.keys()))

with c2:
    selected_industry = st.selectbox("Pilih Industri:", list(market_data[selected_sector].keys()))

tickers = market_data[selected_sector][selected_industry]
st.info(f"Daftar saham di industri **{selected_industry}**: {', '.join(tickers)}")

# --- STEP 3: DEEP DIVE ANALYSIS (THE "CODING" PART) ---
if st.button(f"🔍 Mulai Analisis Mendalam Sektor {selected_industry}"):
    st.divider()
    
    # Kita ambil saham pertama di list sebagai contoh untuk grafik detail (atau bisa buat loop)
    # Untuk efisiensi, kita tampilkan tabel dulu untuk semua saham di industri tersebut
    results = []
    
    for t in tickers:
        df = yf.download(t, period="1y", progress=False)
        df = clean_df(df)
        if not df.empty:
            df['ema_20'] = ta.ema(df['close'], length=20)
            df['rsi_14'] = ta.rsi(df['close'], length=14)
            df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
            
            last = df.iloc[-1]
            entry = last['ema_20']
            sl = entry - (last['atr'] * 2)
            
            results.append({
                "Ticker": t,
                "Price": int(last['close']),
                "RSI": round(last['rsi_14'], 1),
                "Entry Target": int(entry),
                "Stop Loss": int(sl),
                "Status": "🔥 Overbought" if last['rsi_14'] > 70 else "🧊 Oversold" if last['rsi_14'] < 30 else "Neutral"
            })
    
    st.subheader(f"📊 Market Radar: {selected_industry}")
    st.dataframe(pd.DataFrame(results), use_container_width=True)

    # Pilih satu saham untuk visualisasi detail
    selected_ticker = st.selectbox("Pilih Saham untuk Lihat Chart Detail:", tickers)
    
    # --- VISUALISASI ADVANCED (KODE SEBELUMNYA) ---
    df_chart = yf.download(selected_ticker, period="1y", progress=False)
    df_chart = clean_df(df_chart)
    # ... (Tambahkan logika charting lengkap kamu di sini seperti sebelumnya) ...
    st.success(f"Gunakan chart di bawah untuk verifikasi level S/R pada {selected_ticker}")
    # (Copy-paste bagian Plotly make_subplots dari kode sebelumnya ke sini)
