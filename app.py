import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIG ---
st.set_page_config(page_title="Professor's Top-Down Lab", layout="wide")

def clean_df(df):
    if df.empty: return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    return df

# Database Sektor (Bisa kamu tambah sendiri di sini)
market_data = {
    "FINANCE": {
        "Big Banks": ["BBCA.JK", "BBRI.JK", "BMRI.JK", "BBNI.JK"],
        "Digital Banks": ["ARTO.JK", "BBYB.JK"]
    },
    "ENERGY": {
        "Coal": ["ADRO.JK", "ITMG.JK", "PTBA.JK", "HRUM.JK"],
        "Oil & Gas": ["MEDC.JK", "AKRA.JK"]
    },
    "BASIC INFO": {
        "Metal Mining": ["ANTM.JK", "TINS.JK", "MDKA.JK"],
        "Cement": ["SMGR.JK", "INTP.JK"]
    }
}

st.title("🏛️ Professor's Top-Down Terminal")

# --- STEP 1: IHSG OVERVIEW ---
st.subheader("1. Kondisi Pasar (IHSG)")
ihsg = yf.download("^JKSE", period="1y", progress=False)
ihsg = clean_df(ihsg)
if not ihsg.empty:
    last_p = ihsg.iloc[-1]['close']
    prev_p = ihsg.iloc[-2]['close']
    st.metric("IHSG Composite", f"{last_p:.2f}", f"{(last_p-prev_p):.2f}")
    
    fig_ihsg = go.Figure(data=[go.Scatter(x=ihsg.index, y=ihsg['close'], fill='tozeroy', line_color='gold')])
    fig_ihsg.update_layout(height=250, template='plotly_dark', margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig_ihsg, use_container_width=True)

st.divider()

# --- STEP 2: SELECTION ---
st.subheader("2. Pilih Sektor & Industri")
c1, c2 = st.columns(2)
with c1:
    sec = st.selectbox("Sektor:", list(market_data.keys()))
with c2:
    ind = st.selectbox("Industri:", list(market_data[sec].keys()))

tickers = market_data[sec][ind]

# --- STEP 3: MARKET RADAR (TABEL) ---
if st.button(f"🔍 Investigasi Sektor {ind}"):
    st.session_state['run_analysis'] = True

if st.session_state.get('run_analysis'):
    results = []
    for t in tickers:
        d = yf.download(t, period="1y", progress=False)
        d = clean_df(d)
        if not d.empty:
            d['ema20'] = ta.ema(d['close'], length=20)
            d['rsi'] = ta.rsi(d['close'], length=14)
            d['atr'] = ta.atr(d['high'], d['low'], d['close'], length=14)
            l = d.iloc[-1]
            results.append({
                "Ticker": t, "Price": int(l['close']), "RSI": round(l['rsi'], 1),
                "Entry": int(l['ema20']), "SL": int(l['ema20'] - (l['atr']*2)),
                "Status": "🔥 Overbought" if l['rsi'] > 70 else "🧊 Oversold" if l['rsi'] < 30 else "Neutral"
            })
    
    st.write("### 📊 Market Radar")
    st.table(pd.DataFrame(results))

    st.divider()
    
    # --- STEP 4: DETAIL CHART (WAR ROOM) ---
    st.subheader("3. Analisis Chart Mendalam")
    target = st.selectbox("Pilih Saham untuk Chart Detail:", tickers)
    
    df = yf.download(target, period="2y", progress=False)
    df = clean_df(df)
    
    # Kalkulasi Indikator Chart
    df['ema20'] = ta.ema(df['close'], length=20)
    df['ema200'] = ta.ema(df['close'], length=200)
    df['rsi'] = ta.rsi(df['close'], length=14)
    bb = ta.bbands(df['close'], length=20, std=2)
    df = pd.concat([df, bb], axis=1)
    df.columns = [c.lower() for c in df.columns]
    
    # Cari S/R Dinamis
    bbu = [c for c in df.columns if 'bbu' in c][0]
    bbl = [c for c in df.columns if 'bbl' in c][0]

    # Plotting
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_width=[0.15, 0.15, 0.7])
    fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='Price'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['ema20'], line=dict(color='orange'), name='EMA 20'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['ema200'], line=dict(color='white', width=2), name='EMA 200'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df[bbu], line=dict(color='gray', dash='dash'), name='BB Upper'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df[bbl], line=dict(color='gray', dash='dash'), name='BB Lower'), row=1, col=1)
    
    # RSI Row 2
    fig.add_trace(go.Scatter(x=df.index, y=df['rsi'], line=dict(color='purple'), name='RSI'), row=2, col=1)
    # Volume Row 3
    fig.add_trace(go.Bar(x=df.index, y=df['volume'], name='Volume'), row=3, col=1)

    fig.update_layout(height=800, template='plotly_dark', xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)
