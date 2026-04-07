import streamlit as st
import pandas as pd
from logic_scanner import get_all_bei_tickers, get_recommendations_v2

st.set_page_config(page_title="BEI Full Scanner", layout="wide")
st.title("🚀 Full Market Scanner (BEI)")

if st.button("🔍 Scan Seluruh Saham BEI"):
    # 1. Ambil semua kode saham otomatis
    tickers = get_all_bei_tickers()
    st.write(f"Menemukan {len(tickers)} saham listing. Memulai screening 150 saham teraktif...")
    
    progress_bar = st.progress(0)
    
    with st.spinner('Menganalisis teknikal...'):
        top_picks = get_recommendations_v2(tickers)
        progress_bar.progress(100)
        
        if top_picks:
            st.subheader("🏆 Top 10 Hasil Screening Malam Ini")
            df_res = pd.DataFrame(top_picks)
            
            # Percantik tabel
            st.dataframe(df_res, use_container_width=True)
            
            st.success("Selesai! Ini adalah 10 saham dengan kondisi teknikal terbaik saat ini.")
        else:
            st.warning("Tidak ditemukan saham yang memenuhi kriteria 'Strong Buy' malam ini.")
