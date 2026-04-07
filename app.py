import streamlit as st
from logic_scanner import get_stock_data, apply_strategy

st.title("📈 Pro-Level Quant Scanner")

ticker = st.sidebar.text_input("Masukkan Kode Saham (contoh: BBCA.JK)", "BBCA.JK")

if st.button("Run Analysis"):
    data = get_stock_data(ticker)
    analyzed_data = apply_strategy(data)
    st.write(analyzed_data.tail())
    st.line_chart(analyzed_data[['EMA_20', 'EMA_50', 'Close']])
