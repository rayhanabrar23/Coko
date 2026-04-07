import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Professor's Master Dashboard", layout="wide")

def clean_df(df):
    if df.empty: return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    return df

st.title("👨‍🏫 Professor's Master Dashboard")
st.write("Full Analysis: Strategy Table + Advanced Support & Resistance Chart")

ticker = st.text_input("Masukkan Kode Saham (contoh: ADRO.JK):", "ADRO.JK").upper()

if st.button("🚀 Jalankan Investigasi Total"):
    with st.status(f"Sedang Membedah {ticker}...") as status:
        # 1. Ambil Data
        df = yf.download(ticker, period="2y", interval="1d", progress=False)
        df = clean_df(df)
        
        if not df.empty and len(df) > 100:
            # --- CALCULATIONS ---
            df['ema_20'] = ta.ema(df['close'], length=20)
            df['ema_50'] = ta.ema(df['close'], length=50)
            df['ema_200'] = ta.ema(df['close'], length=200)
            df['rsi_14'] = ta.rsi(df['close'], length=14)
            df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
            
            # Bollinger Bands
            bb = ta.bbands(df['close'], length=20, std=2)
            df = pd.concat([df, bb], axis=1)
            df.columns = [c.lower() for c in df.columns]
            bbu_col = [c for c in df.columns if 'bbu' in c][0]
            bbl_col = [c for c in df.columns if 'bbl' in c][0]
            
            # S/R Klasik (Swing High/Low)
            window_sr = 20
            sup_levels = df[df.low == df.low.rolling(window=window_sr, center=True).min()]['low'].unique()
            res_levels = df[df.high == df.high.rolling(window=window_sr, center=True).max()]['high'].unique()
            
            last = df.iloc[-1]
            entry = float(last['ema_20'])
            tp = res_levels[res_levels > last['close']][0] if len(res_levels[res_levels > last['close']]) > 0 else last['close'] * 1.1
            sl = entry - (float(last['atr']) * 2)
            rr_ratio = (tp - entry) / (entry - sl) if (entry - sl) != 0 else 0

            # --- BAGIAN 1: TABEL RENCANA (Tabel Bawah yg Diminta) ---
            st.subheader("📋 Final Trading Plan")
            plan_data = {
                "Item": ["Last Price", "Entry Target (EMA20)", "Target Profit (TP)", "Stop Loss (SL)", "Risk:Reward Ratio", "RSI Status"],
                "Value": [int(last['close']), int(entry), int(tp), int(sl), round(rr_ratio, 2), round(last['rsi_14'], 1)]
            }
            st.table(pd.DataFrame(plan_data))

            # --- BAGIAN 2: GRAFIK WAR ROOM ---
            st.divider()
            st.subheader(f"📈 Advanced Visualization: {ticker}")
            
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                                vertical_spacing=0.03, row_width=[0.15, 0.15, 0.7])

            # Row 1: Candlestick + All EMA + BB + Classic S/R
            fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='Price'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['ema_20'], line=dict(color='orange', width=1), name='EMA 20'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['ema_50'], line=dict(color='cyan', width=1), name='EMA 50'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['ema_200'], line=dict(color='white', width=1.5), name='EMA 200'), row=1, col=1)
            
            # S/R Lines
            for s in sup_levels[-3:]: # 3 Support terakhir
                fig.add_hline(y=s, line_color="green", line_dash="dash", line_width=1, opacity=0.5, row=1, col=1)
            for r in res_levels[-3:]: # 3 Resistance terakhir
                fig.add_hline(y=r, line_color="red", line_dash="dash", line_width=1, opacity=0.5, row=1, col=1)

            # Row 2: RSI
            fig.add_trace(go.Scatter(x=df.index, y=df['rsi_14'], line=dict(color='purple'), name='RSI'), row=2, col=1)
            fig.add_hline(y=70, line_color="red", line_dash="dot", row=2, col=1)
            fig.add_hline(y=30, line_color="green", line_dash="dot", row=2, col=1)

            # Row 3: Volume
            v_colors = ['red' if df['open'].iloc[i] > df['close'].iloc[i] else 'green' for i in range(len(df))]
            fig.add_trace(go.Bar(x=df.index, y=df['volume'], marker_color=v_colors, name='Volume'), row=3, col=1)

            fig.update_layout(height=900, template='plotly_dark', xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
            
            status.update(label="Investigasi Tuntas!", state="complete")
        else:
            st.error("Gagal menarik data atau ticker tidak valid.")
