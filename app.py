import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time

st.set_page_config(page_title="Professor's War Room", layout="wide")

def clean_df(df):
    if df.empty: return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    return df

st.title("👨‍🏫 Professor's War Room: Advanced Charting")

ticker = st.text_input("Masukkan Kode Saham:", "BBCA.JK").upper()

if st.button("🚀 Jalankan Analisis Mendalam"):
    with st.status(f"Menganalisis Medan Perang {ticker}...") as status:
        # 1. Tarik Data (Ambil 2 tahun biar S/R lebih valid)
        df = yf.download(ticker, period="2y", interval="1d", progress=False)
        df = clean_df(df)
        
        if not df.empty and len(df) > 100:
            # --- PROFESSOR'S CALCULATIONS ---
            # 2. Dynamic S/R: EMA 20, 50, & 200 (Benteng Trend)
            df['ema_20'] = ta.ema(df['close'], length=20)
            df['ema_50'] = ta.ema(df['close'], length=50)
            df['ema_200'] = ta.ema(df['close'], length=200) # Long-term support
            
            # 3. Bollinger Bands ( volatility)
            bb = ta.bbands(df['close'], length=20, std=2)
            df = pd.concat([df, bb], axis=1)
            
            # Paksa lowercase & cari kolom dinamis BB
            df.columns = [c.lower() for c in df.columns]
            bbu_col = [c for c in df.columns if 'bbu' in c][0]
            bbl_col = [c for c in df.columns if 'bbl' in c][0]
            
            # 4. Momentum (RSI)
            df['rsi_14'] = ta.rsi(df['close'], length=14)
            
            # 5. Volume Analysis (VSA)
            df['vol_ma'] = df['volume'].rolling(window=20).mean()
            df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)

            # --- S/R HORIZONTAL CLASSIC (Otomatis berdasarkan Swing Highs/Lows) ---
            st.write("🧱 Mencari Benteng Support/Resistance Klasik...")
            window_sr = 20 # Cari S/R di 20 hari terakhir
            
            # Swing Lows (Otoritas Support)
            support_levels = df[df.low == df.low.rolling(window=window_sr, center=True).min()]['low'].unique()
            support_levels.sort() # Ambil 3-4 support terkuat
            
            # Swing Highs (Otoritas Resistance)
            resistance_levels = df[df.high == df.high.rolling(window=window_sr, center=True).max()]['high'].unique()
            resistance_levels.sort() # Ambil 3-4 resistance terkuat

            # Limit levels to show (pilih yang paling dekat dengan harga)
            last_close = df['close'].iloc[-1]
            supports_to_plot = [s for s in support_levels if s < last_close][-3:] # 3 Support terdekat
            resistances_to_plot = [r for r in resistance_levels if r > last_close][:3] # 3 Resistance terdekat

            # --- 6. VISUALISASI JAUH LEBIH DALAM ---
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                                vertical_spacing=0.03, row_width=[0.15, 0.15, 0.7])

            # Row 1: Candlestick + EMA + BB + Classic S/R
            fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='Price'), row=1, col=1)
            
            # Dynamic EMA S/R
            fig.add_trace(go.Scatter(x=df.index, y=df['ema_20'], line=dict(color='orange', width=1), name='EMA 20'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['ema_50'], line=dict(color='cyan', width=1.2), name='EMA 50'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['ema_200'], line=dict(color='white', width=1.5), name='EMA 200 (Long Support)'), row=1, col=1)
            
            # Bollinger Bands
            fig.add_trace(go.Scatter(x=df.index, y=df[bbu_col], line=dict(color='rgba(200,200,200,0.3)', dash='dash'), name='BB Upper'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df[bbl_col], line=dict(color='rgba(200,200,200,0.3)', dash='dash'), name='BB Lower'), row=1, col=1)
            
            # *** HORIZONTAL S/R KLASIK (BARU!) ***
            # Plot Resistance (Merah)
            for res_val in resistances_to_plot:
                fig.add_hline(y=res_val, line_color="rgba(255, 0, 0, 0.7)", line_width=1.5, line_dash="dash", annotation_text=f"R: {int(res_val)}", row=1, col=1)
            
            # Plot Support (Hijau)
            for sup_val in supports_to_plot:
                fig.add_hline(y=sup_val, line_color="rgba(0, 255, 0, 0.7)", line_width=1.5, line_dash="dash", annotation_text=f"S: {int(sup_val)}", row=1, col=1)

            # Row 2: RSI
            fig.add_trace(go.Scatter(x=df.index, y=df['rsi_14'], line=dict(color='purple'), name='RSI'), row=2, col=1)
            fig.add_hline(y=70, line_color="red", line_dash="dot", row=2, col=1)
            fig.add_hline(y=30, line_color="green", line_dash="dot", row=2, col=1)

            # Row 3: Volume & Vol MA
            v_colors = ['red' if df['open'].iloc[i] > df['close'].iloc[i] else 'green' for i in range(len(df))]
            fig.add_trace(go.Bar(x=df.index, y=df['volume'], marker_color=v_colors, name='Volume'), row=3, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['vol_ma'], line=dict(color='white', width=1), name='Vol MA(20)'), row=3, col=1)

            fig.update_layout(height=900, template='plotly_dark', xaxis_rangeslider_visible=False, title_text=f"Professor's War Room: {ticker}")
            st.plotly_chart(fig, use_container_width=True)

            status.update(label="Analisis Perang Selesai!", state="complete")
        else:
            st.error("Data tidak cukup atau ticker salah.")
