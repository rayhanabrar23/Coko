import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta

st.set_page_config(page_title="Top-Down Scanner", layout="wide")
st.title("🔍 Top-Down Analysis Dashboard")

# --- STEP 1: MARKET CONDITION ---
st.header("Step 1: Market Condition (IHSG)")
if st.button("Check Market Health"):
    ihsg = yf.download("^JKSE", period="1mo", interval="1d")
    if not ihsg.empty:
        # Hitung perubahan hari ini
        change = ((ihsg['Close'].iloc[-1] - ihsg['Close'].iloc[-2]) / ihsg['Close'].iloc[-2]) * 100
        st.metric("Composite Index (IHSG)", f"{ihsg['Close'].iloc[-1]:.2f}", f"{change:.2f}%")
        st.line_chart(ihsg['Close'])
    else:
        st.error("Gagal memuat data IHSG.")

st.divider()

# --- STEP 2: SECTOR SELECTION ---
st.header("Step 2: Choose Your Sector")
sectors = {
    "Big Banks": ["BBCA.JK", "BBRI.JK", "BMRI.JK", "BBNI.JK"],
    "Energy & Coal": ["ADRO.JK", "ITMG.JK", "PTBA.JK", "MEDC.JK", "HRUM.JK"],
    "Digital Banks / Tech": ["GOTO.JK", "ARTO.JK", "BBYB.JK", "BUKA.JK"],
    "Consumer Goods": ["ICBP.JK", "INDF.JK", "UNVR.JK", "AMRT.JK"],
    "Metal Mining": ["ANTM.JK", "TINS.JK", "MDKA.JK", "MBMA.JK", "NCKL.JK"]
}

selected_sector = st.selectbox("Pilih sektor yang ingin dipantau:", list(sectors.keys()))
current_tickers = sectors[selected_sector]

st.divider()

# --- STEP 3: DEEP DIVE ANALYSIS ---
st.header(f"Step 3: Deep Dive {selected_sector}")
if st.button(f"Scan {selected_sector}"):
    with st.spinner("Analyzing stocks in sector..."):
        results = []
        for t in current_tickers:
            df = yf.download(t, period="6mo", interval="1d", progress=False)
            if df.empty: continue
            
            # Bersihkan MultiIndex
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df.columns = [c.lower() for c in df.columns]
            
            # Indikator
            df.ta.ema(length=20, append=True)
            df.ta.rsi(length=14, append=True)
            
            last = df.iloc[-1]
            
            # Kondisi (Checklist)
            is_above_ema = last['close'] > last['ema_20']
            rsi_ok = 40 <= last['rsi_14'] <= 65
            
            results.append({
                "Ticker": t,
                "Price": int(last['close']),
                "Above EMA20": "✅" if is_above_ema else "❌",
                "RSI": round(last['rsi_14'], 1),
                "Status": "🔥 BUY" if is_above_ema and rsi_ok else "Wait"
            })
        
        st.table(pd.DataFrame(results))

st.info("Gunakan Step 3 untuk memvalidasi apakah saham di sektor pilihanmu memang sedang dalam posisi teknikal yang bagus.")
