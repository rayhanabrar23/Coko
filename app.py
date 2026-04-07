import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go

st.title("🧪 Diagnostic Mode: Professor's Lab")

ticker = st.text_input("Tes satu saham (contoh: BBCA.JK):", "BBCA.JK")

if st.button("Test Chart"):
    with st.status("Testing Plotly Engine...") as s:
        # Tarik data
        df = yf.download(ticker, period="6mo", progress=False)
        
        # Bersihkan MultiIndex (PENTING!)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [c.lower() for c in df.columns]

        if not df.empty:
            # Buat grafik super simpel
            fig = go.Figure(data=[go.Candlestick(
                x=df.index,
                open=df['open'], high=df['high'],
                low=df['low'], close=df['close']
            )])
            fig.update_layout(template='plotly_dark', title=f"Visual Test: {ticker}")
            
            st.plotly_chart(fig, use_container_width=True)
            s.update(label="Success! Plotly is working.", state="complete")
        else:
            st.error("Data empty. Cek koneksi internet server.")
