import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Professor's Ultimate Lab", layout="wide")

def clean_df(df):
    if df.empty: return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    return df

st.title("👨‍🏫 Professor's Ultimate Trading Terminal")
st.write("Indikator: EMA 20/50, MACD, RSI, Volume, Bollinger Bands, & Risk Plan")

# Input Ticker
col_input, _ = st.columns([1, 2])
with col_input:
    ticker = st.text_input("Masukkan Kode Saham (contoh: BBCA.JK, ADRO.JK):", "BBCA.JK").upper()

if st.button("🚀 Jalankan Analisis Mendalam"):
    with st.status(f"Menganalisis {ticker}...") as status:
        # 1. Tarik Data
        df = yf.download(ticker, period="1y", interval="1d", progress=False)
        df = clean_df(df)
        
        if df.empty or len(df) < 50:
            st.error("Data tidak ditemukan atau kurang dari 50 hari.")
            status.update(label="Analisis Gagal", state="error")
        else:
            # 2. Kalkulasi Indikator
            # Trend & Volatility
            df['ema_20'] = ta.ema(df['close'], length=20)
            df['ema_50'] = ta.ema(df['close'], length=50)
            bb = ta.bbands(df['close'], length=20, std=2)
            df = pd.concat([df, bb], axis=1)
            
            # Momentum
            df['rsi_14'] = ta.rsi(df['close'], length=14)
            macd = ta.macd(df['close'])
            df = pd.concat([df, macd], axis=1)
            
            # Risk Management (ATR & Pivot)
            df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
            prev_day = df.iloc[-2]
            pivot = (prev_day['high'] + prev_day['low'] + prev_day['close']) / 3
            r2 = pivot + (prev_day['high'] - prev_day['low'])
            
            # Bersihkan nama kolom hasil concat
            df.columns = [c.lower() for c in df.columns]
            last = df.iloc[-1]
            
            # Plan Logic
            entry = float(last['ema_20'])
            tp = float(r2)
            sl = entry - (float(last['atr']) * 2)

            # --- 3. VISUALISASI (PLOTLY) ---
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                                vertical_spacing=0.05, 
                                row_width=[0.2, 0.2, 0.6],
                                subplot_titles=(f"Price Action & BBands: {ticker}", "RSI", "Volume"))

            # Row 1: Candlestick + EMA + BBands
            fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='Price'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['ema_20'], line=dict(color='orange', width=1), name='EMA 20'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['bbu_20_2.0'], line=dict(color='gray', dash='dash', width=1), name='BB Upper'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['bbl_20_2.0'], line=dict(color='gray', dash='dash', width=1), name='BB Lower'), row=1, col=1)
            
            # Garis Plan
            fig.add_hline(y=tp, line_color="green", line_dash="dash", annotation_text="Target Profit (R2)", row=1, col=1)
            fig.add_hline(y=entry, line_color="yellow", line_dash="dot", annotation_text="Optimal Entry (EMA20)", row=1, col=1)
            fig.add_hline(y=sl, line_color="red", line_dash="dash", annotation_text="Stop Loss (2x ATR)", row=1, col=1)

            # Row 2: RSI
            fig.add_trace(go.Scatter(x=df.index, y=df['rsi_14'], line=dict(color='purple'), name='RSI'), row=2, col=1)
            fig.add_hline(y=70, line_color="red", line_dash="dot", row=2, col=1)
            fig.add_hline(y=30, line_color="green", line_dash="dot", row=2, col=1)

            # Row 3: Volume
            v_colors = ['red' if df['open'].iloc[i] > df['close'].iloc[i] else 'green' for i in range(len(df))]
            fig.add_trace(go.Bar(x=df.index, y=df['volume'], marker_color=v_colors, name='Volume'), row=3, col=1)

            fig.update_layout(height=900, template='plotly_dark', xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

            # --- 4. TRADING CARD SUMMARY ---
            st.divider()
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Current Price", f"{int(last['close'])}")
            c2.metric("Entry Plan", f"{int(entry)}")
            c3.metric("Target (TP)", f"{int(tp)}", f"{((tp/entry)-1)*100:.1f}%")
            c4.metric("Stop Loss", f"{int(sl)}", f"{((sl/entry)-1)*100:.1f}%", delta_color="inverse")
            
            status.update(label="Analisis Selesai!", state="complete")

            st.success(f"💡 **Professor's Tip:** Perhatikan saat harga menyentuh **BB Lower** dan **RSI di bawah 30**, itu seringkali menjadi area 'Pantulan Maut' untuk profit cepat.")
