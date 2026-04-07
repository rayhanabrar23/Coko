import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time

st.set_page_config(page_title="Master Pro Dashboard", layout="wide")

# Fungsi Pembersih MultiIndex yfinance
def clean_df(df):
    if df.empty: return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    df.dropna(how='all', inplace=True)
    return df

# Fungsi Membuat Grafik Candlestick Interaktif (Plotly)
def plot_advanced_chart(ticker_name, df, tp, sl, entry):
    # Buat subplot (Candlestick di atas, Volume di bawah)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.1, subplot_titles=(f'{ticker_name} Live Chart', 'Volume'), 
                        row_width=[0.2, 0.7])

    # 1. Candlestick
    fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'],
                                low=df['low'], close=df['close'], name='Candle'), row=1, col=1)

    # 2. Indikator (EMA)
    fig.add_trace(go.Scatter(x=df.index, y=df['ema_20'], line=dict(color='orange', width=1.5), name='EMA 20'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['ema_50'], line=dict(color='red', width=1.5), name='EMA 50'), row=1, col=1)

    # 3. Garis Plan (TP, SL, ENTRY)
    # Garis Target Price (Hijau)
    fig.add_hline(y=tp, line_width=2, line_dash="dash", line_color="green", annotation_text=f"TP: {int(tp)}", annotation_position="top right", row=1, col=1)
    # Garis Entry Price (Kuning)
    fig.add_hline(y=entry, line_width=2, line_dash="dot", line_color="yellow", annotation_text=f"ENTRY: {int(entry)}", annotation_position="bottom right", row=1, col=1)
    # Garis Stop Loss (Merah)
    fig.add_hline(y=sl, line_width=2, line_dash="dashdot", line_color="red", annotation_text=f"SL: {int(sl)}", annotation_position="bottom right", row=1, col=1)

    # 4. Volume
    colors = ['red' if df['open'].iloc[i] > df['close'].iloc[i] else 'green' for i in range(len(df))]
    fig.add_trace(go.Bar(x=df.index, y=df['volume'], marker_color=colors, name='Volume'), row=2, col=1)

    # Konfigurasi Layout
    fig.update_layout(height=700, template='plotly_dark', xaxis_rangeslider_visible=False,
                      title_text=f"Advanced Chart: {ticker_name}",
                      showlegend=True)
    
    # Matikan judul sumbu X di subplot atas
    fig.update_xaxes(title_text='', row=1, col=1)
    fig.update_xaxes(title_text='Date', row=2, col=1)
    fig.update_yaxes(title_text='Price', row=1, col=1)
    
    st.plotly_chart(fig, use_container_width=True)

# Main App
st.title("👨‍🏫 Professor's Pro Trading Lab")
st.write("Full Technical Analysis Dashboard: Market Hunter -> Advanced Plan -> Interactive Charting")

sectors = {
    "Perbankan (Big 4)": ["BBCA.JK", "BBRI.JK", "BMRI.JK", "BBNI.JK"],
    "Energi & Batubara": ["ADRO.JK", "ITMG.JK", "PTBA.JK", "MEDC.JK", "HRUM.JK"],
    "Metal Mining": ["ANTM.JK", "TINS.JK", "MDKA.JK", "MBMA.JK", "NCKL.JK"],
    "Teknologi": ["GOTO.JK", "ARTO.JK", "BBYB.JK", "BUKA.JK"]
}

selected_sector = st.selectbox("Pilih Sektor:", list(sectors.keys()))
tickers = sectors[selected_sector]

# Gunakan session_state agar chart tidak hilang saat interaksi lain
if 'final_plan_df' not in st.session_state:
    st.session_state.final_plan_df = None
if 'processed_dfs' not in st.session_state:
    st.session_state.processed_dfs = {}

if st.button(f"🔍 Mulai Investigasi Menyeluruh {len(tickers)} Saham"):
    all_results = []
    processed_dfs = {}
    
    for t in tickers:
        with st.status(f"Menyelidiki {t}...", expanded=False) as status:
            try:
                st.write(f"📥 Mengunduh data 1 tahun...")
                df = yf.download(t, period="1y", interval="1d", progress=False)
                df = clean_df(df)
                
                if df.empty or len(df) < 50:
                    status.update(label=f"❌ {t}: Data Tidak Cukup", state="error")
                    continue

                # --- PROFESSOR'S ADVANCED CALCULATIONS ---
                df['ema_20'] = ta.ema(df['close'], length=20)
                df['ema_50'] = ta.ema(df['close'], length=50)
                df['rsi_14'] = ta.rsi(df['close'], length=14)
                df['vol_ma'] = df['volume'].rolling(window=20).mean()
                
                # ATR & Pivot Points (Untuk TP/SL/ENTRY)
                df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
                prev_day = df.iloc[-2]
                pivot = (prev_day['high'] + prev_day['low'] + prev_day['close']) / 3
                r1 = (2 * pivot) - prev_day['low']
                r2 = pivot + (prev_day['high'] - prev_day['low'])

                df.dropna(subset=['ema_20', 'rsi_14', 'atr'], inplace=True)
                last = df.iloc[-1]
                
                # --- SCORING & FINALIZING PLAN ---
                score = 0
                if last['ema_20'] > last['ema_50']: score += 25
                if last['close'] > last['ema_20']: score += 25
                # MACD Bullish Cross simplified for speed
                macd_df = ta.macd(df['close'])
                if macd_df.iloc[-1][0] > macd_df.iloc[-1][1]: score += 25
                if last['volume'] > last['vol_ma']: score += 25

                # ENTRY PRICE PLAN (Kunci Sukses):
                # Seorang pro tidak beli di harga last, tapi antre di support (EMA20) atau harga jenuh beli kemarin.
                entry_price = float(last['ema_20']) # Aturan standar: Antre di EMA20
                
                # SL & TP Plan
                stop_loss = entry_price - (last['atr'] * 2)
                target_profit = r2

                # Validasi Risk:Reward (Wajib > 1)
                rr_ratio = (target_profit - entry_price) / (entry_price - stop_loss)

                # Simpan DataFrame untuk charting
                processed_dfs[t] = df

                all_results.append({
                    "Ticker": t.replace(".JK", ""),
                    "Last Price": int(last['close']),
                    "Entry Price": int(entry_price),
                    "Stop Loss (SL)": int(stop_loss),
                    "Target Price (TP)": int(target_profit),
                    "Risk:Reward": round(rr_ratio, 2),
                    "Score": score,
                    "Decision": "💎 HIGH PROB BUY" if score >= 100 else "✅ SOLID" if score >= 75 else "🟡 WAIT/NO SETUP"
                })
                
                status.update(label=f"✅ {t} Selesai", state="complete")

            except Exception as e:
                status.update(label=f"⚠️ {t} Gagal Analisis", state="error")

    # Update session state
    if all_results:
        st.session_state.final_plan_df = pd.DataFrame(all_results).sort_values("Score", ascending=False)
        st.session_state.processed_dfs = processed_dfs

# --- FINAL DISPLAY & CHARTING ---
st.divider()

# 1. Tampilkan Tabel Plan (Dengan Entry Price)
if st.session_state.final_plan_df is not None:
    st.header("🏆 Final Trading Plan (With Entry Price)")
    
    def highlight_strong(val):
        color = '#155724' if val == "💎 HIGH PROB BUY" else ''
        return f'background-color: {color}'

    st.dataframe(st.session_state.final_plan_df.style.applymap(highlight_strong, subset=['Decision']), 
                 use_container_width=True, hide_index=True)

    # 2. Fitur Charting Interaktif
    st.divider()
    st.header("📈 Interactive Charting & Plan Verification")
    
    # Ambil list ticker yang berhasil di-scan
    available_tickers = list(st.session_state.processed_dfs.keys())
    
    if available_tickers:
        selected_ticker_for_chart = st.selectbox("Pilih Saham untuk Dilihat Grafiknya:", available_tickers, key="chart_selector")
        
        # Ambil data spesifik saham tersebut dari session_state
        if selected_ticker_for_chart:
            chart_df = st.session_state.processed_dfs[selected_ticker_for_chart]
            
            # Ambil data plan dari tabel utama
            plan_data = st.session_state.final_plan_df[st.session_state.final_plan_df['Ticker'] == selected_ticker_for_chart.replace(".JK", "")].iloc[0]
            
            # Gambar Grafik
            plot_advanced_chart(selected_ticker_for_chart, chart_df, 
                                plan_data['Target Price (TP)'], 
                                plan_data['Stop Loss (SL)'], 
                                plan_data['Entry Price'])
            
            # Saran Profesor
            st.success(f"Analisis Profesor untuk **{selected_ticker_for_chart}**: "
                      f"Antre beli di harga **{plan_data['Entry Price']}**. "
                      f"Potensi untung ke **{plan_data['Target Price (TP)']}**, "
                      f"toleransi risiko di **{plan_data['Stop Loss (SL)']}**. "
                      f"Risk:Reward Ratio {plan_data['Risk:Reward']} sangat menarik!")
    else:
        st.warning("Belum ada data saham yang berhasil di-scan untuk ditampilkan grafiknya.")

else:
    st.warning("Gagal mendapatkan data. Pastikan requirements.txt sudah diupdate dengan `plotly`.")
