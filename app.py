import streamlit as st
import pandas as pd
from logic_scanner import get_stock_data, apply_strategy

st.set_page_config(page_title="Stock Scanner", layout="wide")
st.title("📈 Pro Stock Scanner")

ticker = st.sidebar.text_input("Kode Saham (Contoh: BBCA.JK)", "BBCA.JK")

if st.button("Run Scan"):
    with st.spinner('Sedang menganalisis...'):
        data = get_stock_data(ticker)
        
        if not data.empty:
            analyzed_data = apply_strategy(data)
            
            st.subheader(f"Hasil Analisis: {ticker}")
            
            # Tampilkan tabel data terakhir (opsional)
            st.dataframe(analyzed_data.tail(5))
            
            # FIX KEYERROR: Gunakan nama kolom huruf kecil sesuai logic_scanner.py
            # pandas-ta secara default menghasilkan kolom 'ema_20' (huruf kecil)
            # yfinance yang sudah kita .lower() akan menjadi 'close'
            
            cols_to_plot = []
            available_cols = analyzed_data.columns.tolist()
            
            # Cek apakah kolom yang kita mau ada di dalam data
            for c in ['close', 'ema_20', 'ema_50']:
                if c in available_cols:
                    cols_to_plot.append(c)
            
            if cols_to_plot:
                st.line_chart(analyzed_data[cols_to_plot])
            else:
                st.warning("Indikator belum muncul. Pastikan logic_scanner menghitung EMA_20.")
                st.write("Kolom yang tersedia:", available_cols)
        else:
            st.error("Data kosong. Periksa kembali kode sahamnya.")
