import streamlit as st
import pandas as pd
from logic_scanner import get_recommendations_v2

st.set_page_config(page_title="BEI Full Scanner", layout="wide")
st.title("🎯 Nightly Market Hunter")

# Daftar Ticker Masal (Bisa kamu tambah terus sampai ratusan)
full_list = [
    "BBCA.JK", "BBRI.JK", "BMRI.JK", "BBNI.JK", "TLKM.JK", "ASII.JK", "GOTO.JK", "ADRO.JK",
    "ANTM.JK", "TINS.JK", "BRIS.JK", "PTBA.JK", "ITMG.JK", "UNTR.JK", "AMRT.JK", "CPIN.JK",
    "MDKA.JK", "HRUM.JK", "AKRA.JK", "PGAS.JK", "MEDC.JK", "BRPT.JK", "TPIA.JK", "AMMN.JK",
    "BREN.JK", "INKP.JK", "TKIM.JK", "SMGR.JK", "INTP.JK", "EXCL.JK", "ISAT.JK", "BUKA.JK",
    "UNVR.JK", "KLBF.JK", "ICBP.JK", "INDF.JK", "MYOR.JK", "GGRM.JK", "HMSP.JK", "ACES.JK",
    "ERAA.JK", "MAPA.JK", "MAPI.JK", "BBYB.JK", "ARTO.JK", "BULL.JK", "DOID.JK", "LSIP.JK",
    "AALI.JK", "SIMP.JK", "DSNG.JK", "SSMS.JK", "SMRA.JK", "BSDE.JK", "CTRA.JK", "PRAW.JK",
    "PTPP.JK", "ADHI.JK", "WIKA.JK", "SSIA.JK", "AVIA.JK", "MBMA.JK", "NCKL.JK"
]

st.info(f"Sistem siap memindai {len(full_list)} saham teraktif di BEI.")

if st.button("🔍 Mulai Screening Masal"):
    with st.spinner('Menganalisis teknikal... (Ini butuh waktu ~15 detik)'):
        top_picks = get_recommendations_v2(full_list)
        
        if top_picks:
            st.subheader("🏆 Top 10 Saham Potensial Untuk Besok")
            df_final = pd.DataFrame(top_picks)
            
            # Styling sederhana
            st.dataframe(df_final, use_container_width=True)
            
            st.success("Cek saham dengan Score 100. Itu yang secara teknikal paling 'matang'.")
        else:
            st.error("Gagal mendapatkan data. Silakan coba lagi.")
