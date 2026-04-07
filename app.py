import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Professor's Ultimate Terminal", layout="wide")

def clean_df(df):
    if df.empty: return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    return df

st.title("👨‍🏫 Professor's Ultimate Trading Terminal")

ticker = st.text_input("Masukkan Kode Saham:", "BBCA.JK").upper()

if st.button("🚀 Jalankan Analisis"):
    with st.status(f"Menganalisis {ticker}...") as status:
        df = yf.download(ticker, period="1y", interval="1d", progress=False)
        df = clean_df(df)
        
        if not df.empty and len(df) > 50:
            # 1. Indikator Dasar
            df['ema_20'] = ta.ema(df['close'], length=20)
            df['ema_50'] = ta.ema(df['close'], length=50)
            df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
            df['rsi_14'] = ta.rsi(df['close'], length=14)
            
            # 2. Bollinger Bands (Sering bikin error)
            bb = ta.bbands(df['close'], length=20, std=2)
            df = pd.concat([df, bb], axis=1)
            
            # Paksa semua jadi lowercase biar aman
            df.columns = [c.lower() for c in df.columns]
            
            # --- SOLUSI KEYERROR: Cari kolom BB secara dinamis ---
            bbu_col = [c for c in df.columns if 'bbu' in c][0]
            bbl_col = [c for c in df.columns if 'bbl' in c][0]
            bbm_col = [c for c in df.columns if 'bbm' in c][0]
            
            # 3. Risk Plan
            prev_day = df.iloc[-2]
            pivot = (prev_day['high'] + prev_day['low'] + prev_day['close']) / 3
            r2 = pivot + (prev_day['high'] - prev_day['low'])
            
            last = df.iloc[-1]
            entry = float(last['ema_20'])
            tp = float(r2)
            sl = entry - (float(last['atr']) * 2)

            # --- 4. VISUALISASI ---
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                                vertical_spacing=0.05, row_width=[0.2, 0.2, 0.6])

            # Candlestick
            fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='Price'), row=1, col=1)
            
            # EMA & Bollinger Bands (Menggunakan variabel kolom dinamis)
            fig.add_trace(go.Scatter(x=df.index, y=df['ema_20'], line=dict(color='orange', width=1), name='EMA 20'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df[bbu_col], line=dict(color='rgba(173, 216, 230, 0.4)', dash='dash'), name='BB Upper'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df[bbl_col], line=dict(color='rgba(173, 216, 230, 0.4)', dash='dash'), name='BB Lower'), row=1, col=1)
            
            # Plot Plan Lines
            fig.add_hline(y=tp, line_color="green", line_dash="dash", annotation_text="TP", row=1, col=1)
            fig.add_hline(y=entry, line_color="yellow", line_dash="dot", annotation_text="Entry", row=1, col=1)
            fig.add_hline(y=sl, line_color="red", line_dash="dash", annotation_text="SL", row=1, col=1)

            # RSI & Volume (Sama seperti sebelumnya)
            fig.add_trace(go.Scatter(x=df.index, y=df['rsi_14'], line=dict(color='purple'), name='RSI'), row=2, col=1)
            v_colors = ['red' if df['open'].iloc[i] > df['close'].iloc[i] else 'green' for i in range(len(df))]
            fig.add_trace(go.Bar(x=df.index, y=df['volume'], marker_color=v_colors, name='Volume'), row=3, col=1)

            fig.update_layout(height=800, template='plotly_dark', xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

            # Metrics
            st.divider()
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Price", f"{int(last['close'])}")
            c2.metric("Entry Plan", f"{int(entry)}")
            c3.metric("Target Profit", f"{int(tp)}")
            c4.metric("Stop Loss", f"{int(sl)}")
            
            status.update(label="Analisis Selesai!", state="complete")
        else:
            st.error("Data tidak cukup atau ticker salah.")
