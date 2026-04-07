import streamlit as st
import pandas as pd
from logic_scanner import get_recommendations

st.set_page_config(page_title="Top 10 Picks", layout="wide")
st.title("🎯 Nightly Stock Hunter: Top 10 Picks for Tomorrow")

# Daftar saham yang akan di-scan (Bisa kamu tambah sebanyak mungkin)
tickers_to_scan = [
    "BBCA.JK", "BBRI.JK", "BMRI.JK", "BBNI.JK", "ASII.JK", "TLKM.JK", 
    "GOTO.JK", "ADRO.JK", "UNTR.JK", "AMRT.JK", "PGAS.JK", "ANTM.JK", 
    "TINS.JK", "BRIS.JK", "BREN.JK", "AMMN.JK", "DSAK.JK", "INKP.JK"
]

st.sidebar.write(f"Scanning {len(tickers_to_scan)} stocks...")

if st.button("🚀 Mulai Screening"):
    with st.spinner('Memindai pasar... Mohon tunggu sebentar.'):
        top_10 = get_recommendations(tickers_to_scan)
        
        if top_10:
            df_final = pd.DataFrame(top_10)
            
            # Styling Tabel
            def highlight_strong(val):
                return 'background-color: #d4edda; color: #155724' if val == 'STRONG BUY' else ''

            st.subheader("🔥 Top 10 Rekomendasi Saham")
            st.table(df_final.style.applymap(highlight_strong, subset=['Signal']))
            
            st.success("Saran: Fokus pada saham dengan Score 100 dan Signal 'STRONG BUY' untuk probabilitas cuan lebih tinggi.")
        else:
            st.error("Gagal menarik data. Coba lagi dalam beberapa menit.")
