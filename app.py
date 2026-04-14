import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np

# ─────────────────────────────────────────────────────────
# CONFIG & STYLE
# ─────────────────────────────────────────────────────────
st.set_page_config(page_title="IDX Terminal v4.2", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
body, .stApp { background-color: #07090f; color: #d0d8e8; }
.metric-card {
    background: linear-gradient(135deg, #0e1420 0%, #111c2e 100%);
    border: 1px solid #1e3050; border-radius: 10px;
    padding: 14px; text-align: center; height: 100%;
}
.score-high { color: #00ff99; font-size: 26px; font-weight: 900; }
.score-mid  { color: #ffcc00; font-size: 26px; font-weight: 900; }
.score-low  { color: #ff4466; font-size: 26px; font-weight: 900; }
.tag-sbuy   { background:#004422; color:#00ff99; padding:3px 10px; border-radius:20px; font-weight:bold; font-size:13px; }
.tag-buy    { background:#002e18; color:#44dd88; padding:3px 10px; border-radius:20px; font-weight:bold; font-size:13px; }
.tag-hold   { background:#332200; color:#ffcc00; padding:3px 10px; border-radius:20px; font-weight:bold; font-size:13px; }
.tag-sell   { background:#3a0010; color:#ff4466; padding:3px 10px; border-radius:20px; font-weight:bold; font-size:13px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────
# DATABASE & HELPERS
# ─────────────────────────────────────────────────────────

MANUAL_SECTORS = {
    "FINANCE": ["BBCA","BBRI","BMRI","BBNI","BRIS","ARTO","BNGA","NISP"],
    "ENERGY": ["ADRO","ITMG","PTBA","MEDC","AKRA","PGAS","ENRG","AADI"],
    "BASIC MAT": ["ANTM","TINS","MDKA","SMGR","INTP","INCO","NCKL","AMMN"],
    "CONSUMER": ["ACES","MAPI","AMRT","ICBP","INDF","GGRM","UNVR","MYOR"],
    "INFRA": ["TLKM","ISAT","EXCL","TOWR","TBIG","JSMR","MTEL","PGEO"],
    "TECH": ["GOTO","BUKA","EMTK","DCII","BELI"]
}

SECTOR_PROXY = {"FINANCE":"BBCA","ENERGY":"ADRO","BASIC MAT":"ANTM","CONSUMER":"ICBP","INFRA":"TLKM","TECH":"GOTO"}

def clean_df(df):
    if df.empty: return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    return df

def safe_float(val, default=0.0):
    try:
        v = float(val)
        return default if (np.isnan(v) or np.isinf(v)) else v
    except: return default

# ─────────────────────────────────────────────────────────
# LOGIC (REVISI: LEBIH ADAPTIF)
# ─────────────────────────────────────────────────────────

def volume_analysis(df):
    if 'volume' not in df.columns or len(df)<20: return 0,"N/A",False
    avg = df['volume'].rolling(20).mean().iloc[-1]
    last = df['volume'].iloc[-1]
    ratio = safe_float(last/avg) if avg>0 else 0
    return ratio, f"{ratio:.1f}x", ratio>=1.2 # Relaksasi volume

def score_ticker(df):
    if df.empty or len(df)<40: return 0,{}
    df = df.copy()
    df['ema20'] = ta.ema(df['close'], length=20)
    df['ema50'] = ta.ema(df['close'], length=50)
    df['rsi'] = ta.rsi(df['close'], length=14)
    macd = ta.macd(df['close'])
    df['macd'] = macd.iloc[:,0] if macd is not None else 0
    df['sig'] = macd.iloc[:,1] if macd is not None else 0
    
    l = df.iloc[-1]
    cl, e20, e50, rsi = safe_float(l['close']), safe_float(l['ema20']), safe_float(l['ema50']), safe_float(l['rsi'])
    
    ts = 0
    if cl > e20: ts += 15
    if cl > e50: ts += 15
    
    ms = 0
    if 35 <= rsi <= 72: ms += 25 # RSI lebih toleran
    if safe_float(l['macd']) > safe_float(l['sig']): ms += 15
    
    vr, _, _ = volume_analysis(df)
    vs = min(int(vr * 10), 30) # Bobot volume

    score = min(ts + ms + vs, 100)
    return score, {'Trend':ts, 'Momentum':ms, 'Volume':vs}

def get_signal(df, score):
    l = df.iloc[-1]
    cl = safe_float(l['close'])
    rsi = safe_float(l['rsi'] if 'rsi' in df.columns else 50)
    e20 = safe_float(l['ema20'] if 'ema20' in df.columns else cl)
    atr = safe_float(ta.atr(df['high'], df['low'], df['close']).iloc[-1]) if len(df)>14 else cl*0.02

    sl = cl - (1.8 * atr); tp = cl + (3 * atr)
    rr = round((tp-cl)/(cl-sl), 2) if (cl-sl)>0 else 0

    if score >= 70: return "⚡ STRONG BUY", "#00ff99", sl, tp, rr
    elif score >= 45 or cl > e20: return "✅ BUY", "#44dd88", sl, tp, rr
    elif rsi > 78: return "❌ SELL/AVOID", "#ff4466", sl, tp, rr
    else: return "🔄 HOLD/WATCH", "#ffcc00", sl, tp, rr

# ─────────────────────────────────────────────────────────
# UI RENDER
# ─────────────────────────────────────────────────────────

st.markdown("<h1 style='text-align:center; color:#00bbff;'>⚡ IDX TERMINAL v4.2</h1>", unsafe_allow_html=True)

# MARKET PULSE (FIXED VERSION)
col_ihsg, col_sector = st.columns([1,1])
with col_ihsg:
    st.subheader("📈 IHSG Market Pulse")
    try:
        raw_ihsg = yf.download("^JKSE", period="1y", progress=False)
        ihsg_df = clean_df(raw_ihsg)
        if not ihsg_df.empty and len(ihsg_df) >= 2:
            curr = safe_float(ihsg_df['close'].iloc[-1])
            prev = safe_float(ihsg_df['close'].iloc[-2])
            diff = ((curr - prev) / prev) * 100
            
            fig_ihsg = go.Figure(go.Scatter(x=ihsg_df.index, y=ihsg_df['close'], fill='tozeroy', line_color='#00bbff'))
            fig_ihsg.update_layout(height=200, margin=dict(l=0,r=0,t=0,b=0), template='plotly_dark', xaxis_rangeslider_visible=False)
            st.plotly_chart(fig_ihsg, use_container_width=True)
            
            ca, cb = st.columns(2)
            ca.metric("Last", f"{curr:,.2f}")
            cb.metric("Change", f"{diff:+.2f}%")
    except: st.write("Data IHSG tidak tersedia")

with col_sector:
    st.subheader("🗺️ Sector Heatmap (5D)")
    sec_data = []
    for s, t in SECTOR_PROXY.items():
        try:
            d = clean_df(yf.download(f"{t}.JK", period="10d", progress=False))
            if not d.empty and len(d) >= 5:
                perf = ((d['close'].iloc[-1] - d['close'].iloc[-5]) / d['close'].iloc[-5]) * 100
                sec_data.append({"Sektor": s, "Perf": round(perf, 2), "Size": 10})
        except: continue
    if sec_data:
        fig_tree = px.treemap(pd.DataFrame(sec_data), path=['Sektor'], values='Size', color='Perf', color_continuous_scale='RdYlGn')
        fig_tree.update_layout(height=230, margin=dict(l=0,r=0,t=0,b=0), template='plotly_dark')
        st.plotly_chart(fig_tree, use_container_width=True)

st.divider()

# DEEP ANALYSIS
ticker_in = st.text_input("🔍 Kode Saham:", "BBRI").upper()
ticker = ticker_in if ticker_in.endswith(".JK") else f"{ticker_in}.JK"

with st.spinner(f"Analisis {ticker}..."):
    df = clean_df(yf.download(ticker, period="1y", progress=False))
    if not df.empty and len(df) > 40:
        score, _ = score_ticker(df)
        signal, sig_color, sl, tp, rr = get_signal(df, score)
        l = df.iloc[-1]
        
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f"<div class='metric-card'>Score<br><span class='score-high'>{score}/100</span></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='metric-card'>Signal<br><span style='color:{sig_color}; font-size:22px;'>{signal}</span></div>", unsafe_allow_html=True)
        c3.metric("RSI", f"{safe_float(l['rsi']):.1f}")
        c4.metric("R:R Ratio", f"1:{rr}")

        # Plotly Chart Detail
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
        fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="Price"), row=1, col=1)
        fig.add_trace(go.Bar(x=df.index, y=df['volume'], name="Volume"), row=2, col=1)
        fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
        
        st.success(f"**Trading Plan {ticker_in}:** Entry: {l['close']:,.0f} | Stop Loss: {sl:,.0f} | Take Profit: {tp:,.0f}")
    else: st.error("Data tidak ditemukan.")
