import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# --- CONFIG ---
st.set_page_config(page_title="Professor's Executive Terminal", layout="wide")

def clean_df(df):
    if df.empty: return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    return df

# --- DATABASE SEKTOR ---
market_data = {
    "FINANCE": ["BBCA.JK", "BBRI.JK", "BMRI.JK", "BBNI.JK", "BRIS.JK", "ARTO.JK"],
    "ENERGY": ["ADRO.JK", "ITMG.JK", "PTBA.JK", "MEDC.JK", "AKRA.JK", "PGAS.JK"],
    "HEALTHCARE": ["MIKA.JK", "HEAL.JK", "SILO.JK", "KLBF.JK", "SIDO.JK"],
    "BASIC INFO": ["ANTM.JK", "TINS.JK", "MDKA.JK", "SMGR.JK", "INTP.JK", "TPIA.JK"],
    "CONSUMER": ["ACES.JK", "MAPI.JK", "AMRT.JK", "ICBP.JK", "INDF.JK", "GGRM.JK"],
    "INFRA": ["TLKM.JK", "ISAT.JK", "EXCL.JK", "TOWR.JK", "TBIG.JK", "ADHI.JK"],
    "PROPERTY": ["BSDE.JK", "PWON.JK", "CTRA.JK", "SMRA.JK", "SSIA.JK"]
}

st.title("🏛️ Professor's Executive Terminal")

# --- STEP 1: IHSG & INTERACTIVE SECTOR MAP ---
c1, c2 = st.columns([1, 1])

with c1:
    st.subheader("📈 IHSG Market Pulse")
    ihsg = yf.download("^JKSE", period="1y", progress=False)
    ihsg = clean_df(ihsg)
    if not ihsg.empty:
        fig_ihsg = go.Figure(data=[go.Scatter(x=ihsg.index, y=ihsg['close'], fill='tozeroy', line_color='gold')])
        fig_ihsg.update_layout(height=300, template='plotly_dark', margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig_ihsg, use_container_width=True)

with c2:
    st.subheader("🗺️ Sectoral Map (Relative Momentum)")
    sector_perf = []
    proxy = {"FINANCE":"BBCA.JK", "ENERGY":"ADRO.JK", "HEALTHCARE":"KLBF.JK", "BASIC":"ANTM.JK", "CONSUMER":"ICBP.JK", "INFRA":"TLKM.JK", "PROPERTY":"BSDE.JK"}
    for s, t in proxy.items():
        px_data = yf.download(t, period="5d", progress=False)
        if not px_data.empty:
            perf = ((px_data['Close'].iloc[-1] - px_data['Close'].iloc[0]) / px_data['Close'].iloc[0]) * 100
            sector_perf.append({"Sector": s, "Performance": perf, "Parent": "Market"})
    
    fig_tree = px.treemap(sector_perf, path=['Parent', 'Sector'], values=[10]*len(sector_perf), 
                          color='Performance', color_continuous_scale='RdYlGn', range_color=[-3, 3])
    fig_tree.update_layout(height=300, margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig_tree, use_container_width=True)

st.divider()

# --- STEP 2: SEARCH & EXPLORATION ---
st.subheader("🔍 Stock Finder")
search_col, nav_col = st.columns([1, 2])

with search_col:
    manual_ticker = st.text_input("Ketik Kode Emiten Manual (Contoh: GOTO.JK):", "").upper()

with nav_col:
    sec = st.selectbox("Atau Pilih dari Database Sektor:", ["None"] + list(market_data.keys()))

# Penentuan Target Analisis
target = None
if manual_ticker:
    target = manual_ticker if manual_ticker.endswith(".JK") else f"{manual_ticker}.JK"
elif sec != "None":
    target = st.selectbox("Pilih Saham di Sektor ini:", market_data[sec])

# --- STEP 3: DEEP DIVE ANALYSIS ---
if target:
    st.write(f"### 🛡️ Deep Dive Intelligence: {target}")
    t_obj = yf.Ticker(target)
    
    # Financial Row
    info = t_obj.info
    f1, f2, f3, f4 = st.columns(4)
    f1.metric("P/E Ratio", info.get('trailingPE', 'N/A'))
    f2.metric("PBV", info.get('priceToBook', 'N/A'))
    f3.metric("Dividend Yield", f"{info.get('dividendYield', 0)*100:.2f}%")
    f4.metric("ROE", f"{info.get('returnOnEquity', 0)*100:.2f}%")

    # Interactive Chart
    df = yf.download(target, period="1y", progress=False)
    df = clean_df(df)
    if not df.empty:
        df['ema20'] = ta.ema(df['close'], length=20)
        df['rsi'] = ta.rsi(df['close'], length=14)
        
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_width=[0.3, 0.7], vertical_spacing=0.05)
        fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='Price'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['ema20'], line=dict(color='orange', width=1.5), name='EMA 20'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['rsi'], line=dict(color='purple'), name='RSI'), row=2, col=1)
        fig.update_layout(height=600, template='plotly_dark', xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

# --- STEP 4: DAILY RECOMMENDATION ---
st.divider()
if st.button("🎯 Generate Top 10 Picks"):
    st.subheader("🚀 Morning Buy List")
    picks = []
    all_tickers = [item for sublist in market_data.values() for item in sublist]
    for t in list(set(all_tickers)):
        d = yf.download(t, period="50d", progress=False)
        d = clean_df(d)
        if not d.empty and len(d) > 20:
            d['ema20'] = ta.ema(d['close'], length=20)
            d['rsi'] = ta.rsi(d['close'], length=14)
            l = d.iloc[-1]
            if 0 <= (l['close'] - l['ema20'])/l['ema20'] <= 0.02 and 40 <= l['rsi'] <= 60:
                picks.append({"Ticker": t, "Price": int(l['close']), "RSI": round(l['rsi'], 1), "Signal": "EMA20 Rebound"})
    
    if picks:
        st.table(pd.DataFrame(picks).head(10))
    
    # --- AUTOMATED TOP-DOWN REVIEW ---
    st.write("---")
    st.subheader("🧐 Professor's Market Review")
    
    ihsg_change = ((ihsg['close'].iloc[-1] - ihsg['close'].iloc[-2]) / ihsg['close'].iloc[-2]) * 100
    market_mood = "Bullish" if ihsg_change > 0 else "Bearish"
    
    st.info(f"""
    **Analisis Top-Down Hari Ini:**
    1. **Kondisi Makro:** IHSG saat ini sedang dalam fase **{market_mood}** ({ihsg_change:.2f}%). Harga berada di level {ihsg['close'].iloc[-1]:.0f}.
    2. **Rotasi Sektor:** Berdasarkan Treemap di atas, sektor yang menunjukkan kekuatan relatif paling stabil adalah sektor yang berwarna hijau pekat. 
    3. **Strategi:** Fokus pada emiten di list 'Morning Picks' yang memiliki fundamental ROE > 10% dan harga yang sedang 'istirahat' di EMA 20. 
    4. **Risk Note:** Selalu perhatikan volume saat pembukaan. Jika harga naik tapi volume kecil, waspada *false breakout*.
    """)
