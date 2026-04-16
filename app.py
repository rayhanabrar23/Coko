import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, date, timedelta
import concurrent.futures
import time
import json
from pathlib import Path
import pytz

# ── CONFIG & STYLING ─────────────────────────────────────────────────────────
st.set_page_config(page_title="IDX Terminal v5", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    body, .stApp { background-color: #07090f; color: #d0d8e8; }
    [data-testid="stSidebar"] { background-color: #0b0f1a; border-right: 1px solid #1e3050; }
    .metric-card {
        background: linear-gradient(135deg, #0e1420 0%, #111c2e 100%);
        border: 1px solid #1e3050; border-radius: 10px;
        padding: 14px; text-align: center; height: 100%;
    }
    .score-high { color: #00ff99; font-size: 26px; font-weight: 900; }
    .score-mid  { color: #ffcc00; font-size: 26px; font-weight: 900; }
    .score-low  { color: #ff4466; font-size: 26px; font-weight: 900; }
    .stTable { background-color: #0e1420; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# ── DATA PERSISTENCE ─────────────────────────────────────────────────────────
LOG_FILE = Path("trade_logs.json")

def load_trade_log():
    if LOG_FILE.exists():
        try:
            with open(LOG_FILE, "r") as f:
                return json.load(f)
        except:
            return []
    return []

def save_trade_log(logs):
    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=4)

def fmt_price(val):
    return f"{val:,.0f}".replace(",", ".")

# ── FINANCE ENGINE ───────────────────────────────────────────────────────────
DEFAULT_TICKERS = [
    "BBCA.JK", "BBRI.JK", "BMRI.JK", "BBNI.JK", "TLKM.JK", "ASII.JK", 
    "GOTO.JK", "UNVR.JK", "ICBP.JK", "AMRT.JK", "ADRO.JK", "ITMG.JK",
    "PTBA.JK", "CPIN.JK", "MDKA.JK", "PGAS.JK", "BRIS.JK", "ANTM.JK"
]

@st.cache_data(ttl=3600)
def fetch_data(ticker, period="1y"):
    try:
        df = yf.download(ticker, period=period, interval="1d", progress=False)
        if df.empty or len(df) < 30:
            return None
        
        # FIX: Handle MultiIndex Columns in New yfinance versions
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df.index.name = "Date"
        df = df.reset_index()
        df["Ticker"] = ticker
        
        # Technical Indicators
        df["MA20"] = ta.sma(df["Close"], length=20)
        df["MA50"] = ta.sma(df["Close"], length=50)
        df["RSI"] = ta.rsi(df["Close"], length=14)
        
        # MACD
        macd = ta.macd(df["Close"])
        if macd is not None:
            df = pd.concat([df, macd], axis=1)
            
        # Advanced Scoring Logic
        last_price = float(df["Close"].iloc[-1])
        ma20_last = float(df["MA20"].iloc[-1])
        rsi_last = float(df["RSI"].iloc[-1])
        
        score = 0
        if last_price > ma20_last: score += 40
        if 40 < rsi_last < 65: score += 30
        if rsi_last < 35: score += 20 # Potential Reversal
        
        df["Score"] = score
        return df
    except Exception as e:
        return None

# ── MAIN APP ─────────────────────────────────────────────────────────────────
st.title("📈 IDX Terminal v5")

with st.sidebar:
    st.header("⚙️ Control Panel")
    selected_tickers = st.multiselect("Pilih Saham (Watchlist)", DEFAULT_TICKERS, default=DEFAULT_TICKERS[:6])
    period_choice = st.selectbox("Rentang Waktu", ["1mo", "3mo", "6mo", "1y", "2y"], index=3)
    if st.button("🔄 Paksa Refresh Data"):
        st.cache_data.clear()
        st.rerun()

# Data Loading with Progress
all_data_list = []
if selected_tickers:
    with st.spinner(f"📥 Mengambil data {len(selected_tickers)} saham..."):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = list(executor.map(lambda x: fetch_data(x, period=period_choice), selected_tickers))
            all_data_list = [r for r in results if r is not None]

if not all_data_list:
    st.error("❌ Gagal memuat data. Periksa koneksi internet atau simbol ticker.")
    st.stop()

# ── METRICS GRID ─────────────────────────────────────────────────────────────
cols = st.columns(min(len(all_data_list), 6))
for i, df_stock in enumerate(all_data_list[:6]):
    ticker = df_stock["Ticker"].iloc[-1]
    price = df_stock["Close"].iloc[-1]
    prev_price = df_stock["Close"].iloc[-2]
    change = ((price - prev_price) / prev_price) * 100
    score = int(df_stock["Score"].iloc[-1])
    
    color_class = "score-high" if score >= 70 else "score-mid" if score >= 40 else "score-low"
    
    with cols[i]:
        st.markdown(f"""
        <div class="metric-card">
            <div style="font-size:14px; opacity:0.7;">{ticker}</div>
            <div style="font-size:22px; font-weight:bold;">{fmt_price(price)}</div>
            <div style="color:{'#00ff99' if change >= 0 else '#ff4466'}; font-size:13px;">
                {'▲' if change >= 0 else '▼'} {abs(change):.2f}%
            </div>
            <div class="{color_class}">{score}</div>
        </div>
        """, unsafe_allow_html=True)

st.divider()

# ── CHART ANALYSIS ───────────────────────────────────────────────────────────
col_chart, col_info = st.columns([3, 1])

with col_chart:
    selected_view = st.selectbox("Pilih Saham untuk Detail:", [d["Ticker"].iloc[0] for d in all_data_list])
    df_view = next(d for d in all_data_list if d["Ticker"].iloc[0] == selected_view)
    
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
    
    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df_view['Date'], open=df_view['Open'], high=df_view['High'],
        low=df_view['Low'], close=df_view['Close'], name="Harga"
    ), row=1, col=1)
    
    # MA Lines
    fig.add_trace(go.Scatter(x=df_view['Date'], y=df_view['MA20'], name="MA20", line=dict(color='#ffcc00', width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_view['Date'], y=df_view['MA50'], name="MA50", line=dict(color='#00d9ff', width=1.5)), row=1, col=1)
    
    # RSI
    fig.add_trace(go.Scatter(x=df_view['Date'], y=df_view['RSI'], name="RSI", line=dict(color='#ff00ff', width=1)), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="#ff4466", row=2, col=1, opacity=0.5)
    fig.add_hline(y=30, line_dash="dash", line_color="#00ff99", row=2, col=1, opacity=0.5)
    
    fig.update_layout(height=500, template="plotly_dark", showlegend=False, margin=dict(t=10, b=10, l=10, r=10))
    fig.update_xaxes(rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

with col_info:
    st.subheader("Signal & Info")
    curr_rsi = df_view['RSI'].iloc[-1]
    if curr_rsi > 70: st.error("⚠️ Overbought (Jenuh Beli)")
    elif curr_rsi < 30: st.success("✅ Oversold (Jenuh Jual)")
    else: st.info("Neutral Zone")
    
    st.write(f"**High 52W:** {fmt_price(df_view['High'].max())}")
    st.write(f"**Low 52W:** {fmt_price(df_view['Low'].min())}")

# ── TRADE JOURNAL ────────────────────────────────────────────────────────────
st.divider()
st.header("📝 Trade Journal & Portfolio")

logs = load_trade_log()
c1, c2 = st.columns([1, 2])

with c1:
    with st.form("entry_form", clear_on_submit=True):
        st.subheader("Add Trade")
        t_code = st.text_input("Ticker (e.g. BBCA)")
        t_price = st.number_input("Entry Price", min_value=0)
        t_date = st.date_input("Date", value=date.today())
        if st.form_submit_button("Simpan"):
            if t_code and t_price > 0:
                logs.append({"id": int(time.time()), "date": str(t_date), "ticker": t_code.upper(), "entry": t_price})
                save_trade_log(logs)
                st.rerun()

with c2:
    if logs:
        df_logs = pd.DataFrame(logs)
        st.dataframe(df_logs[["date", "ticker", "entry"]], use_container_width=True)
        
        # Download Section
        csv = df_logs.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Journal (CSV)", data=csv, file_name="my_trades.csv", mime="text/csv")
        
        if st.button("🗑️ Hapus Semua Data"):
            save_trade_log([])
            st.rerun()
    else:
        st.info("Belum ada data transaksi.")
