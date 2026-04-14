import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime

# ─────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────
st.set_page_config(page_title="IDX Terminal v4", layout="wide", initial_sidebar_state="collapsed")

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
div[data-testid="stDataFrame"] { background: #0a0d15 !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────
# UNIVERSE DATABASE
# ─────────────────────────────────────────────────────────

IDX30 = ["AADI","ADRO","AMMN","ANTM","AMRT","ASII","BBCA","BBNI","BBRI","BBTN","BMRI","BRIS","BUKA","CPIN","EXCL","GOTO","ICBP","INCO","INDF","ISAT","ITMG","KLBF","MDKA","MEDC","MIKA","PGEO","PTBA","TLKM","TOWR","UNTR"]
LQ45 = list(dict.fromkeys(IDX30 + ["ACES","AKRA","ARTO","BELI","BNGA","BSDE","CTRA","EMTK","GGRM","HMSP","INTP","JSMR","MAPI","MYOR","PGAS","PNBN","PWON","SMGR","TBIG","TINS","TKIM","UNVR","HEAL","BYAN","CMRY","DCII","DSSA","NCKL","INKP","SILO"]))[:45]

MANUAL_SECTORS = {
    "FINANCE":    ["BBCA","BBRI","BMRI","BBNI","BRIS","ARTO","BNGA","PNBN","MEGA","BDMN","NISP","BBTN"],
    "ENERGY":     ["ADRO","ITMG","PTBA","MEDC","AKRA","PGAS","ENRG","GEMS","AADI","BYAN"],
    "HEALTHCARE": ["MIKA","HEAL","SILO","KLBF","SIDO","PYFA"],
    "BASIC MAT":  ["ANTM","TINS","MDKA","SMGR","INTP","INCO","NCKL","AMMN","BRMS"],
    "CONSUMER":   ["ACES","MAPI","AMRT","ICBP","INDF","GGRM","HMSP","UNVR","MYOR","CPIN"],
    "INFRA":      ["TLKM","ISAT","EXCL","TOWR","TBIG","JSMR","MTEL","PGEO"],
    "PROPERTY":   ["BSDE","PWON","CTRA","SMRA","SSIA","PANI"],
    "TECH":       ["GOTO","BUKA","EMTK","DCII","BELI"],
}

SECTOR_PROXY = {"FINANCE":"BBCA","ENERGY":"ADRO","HEALTHCARE":"KLBF","BASIC MAT":"ANTM","CONSUMER":"ICBP","INFRA":"TLKM","PROPERTY":"BSDE","TECH":"GOTO"}

def add_jk(tickers):
    return [t if t.endswith(".JK") else f"{t}.JK" for t in tickers]

# ─────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────

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
# ANALYSIS ENGINE
# ─────────────────────────────────────────────────────────

def detect_patterns(df):
    if len(df) < 3: return ["—"]
    patterns = []
    o,h,l,c = df['open'].values, df['high'].values, df['low'].values, df['close'].values
    i = -1
    body = abs(c[i]-o[i]); rng = h[i]-l[i]
    if rng > 0:
        if (min(c[i],o[i])-l[i]) >= 2*body and (h[i]-max(c[i],o[i])) <= 0.3*body: patterns.append("🔨 Hammer (Bullish)")
        if body/rng < 0.1: patterns.append("✳️ Doji (Reversal)")
        if body/rng > 0.85: patterns.append("💪 Marubozu " + ("Bull" if c[i]>o[i] else "Bear"))
    if c[-2]<o[-2] and c[i]>o[i] and body>abs(c[-2]-o[-2]): patterns.append("🟢 Bullish Engulfing")
    return patterns or ["— No Pattern"]

def volume_analysis(df):
    if 'volume' not in df.columns or len(df)<20: return 0,"N/A",False
    avg = df['volume'].rolling(20).mean().iloc[-1]
    last = df['volume'].iloc[-1]
    ratio = safe_float(last/avg) if avg>0 else 0
    return ratio, f"{ratio:.1f}x", ratio>=1.2 # Direlaksasi ke 1.2x

def score_ticker(df):
    if df.empty or len(df)<50: return 0,{}
    df = df.copy()
    df['ema20'] = ta.ema(df['close'], length=20)
    df['ema50'] = ta.ema(df['close'], length=50)
    df['rsi'] = ta.rsi(df['close'], length=14)
    macd = ta.macd(df['close'])
    df['macd'] = macd.iloc[:,0] if macd is not None else 0
    df['sig'] = macd.iloc[:,1] if macd is not None else 0
    bb = ta.bbands(df['close'])
    df['bb_l'] = bb.iloc[:,0] if bb is not None else df['close']

    l = df.iloc[-1]
    cl, e20, e50, rsi = safe_float(l['close']), safe_float(l['ema20']), safe_float(l['ema50']), safe_float(l['rsi'])
    
    # 1. TREND (Max 30) - Bobot dinaikkan
    ts = 0
    if cl > e20: ts += 15
    if cl > e50: ts += 15
    
    # 2. MOMENTUM (Max 30)
    ms = 0
    if 40 <= rsi <= 70: ms += 20 # Range RSI lebih luas
    elif rsi < 40: ms += 10 # Potensi oversold
    if safe_float(l['macd']) > safe_float(l['sig']): ms += 10
    
    # 3. VOLUME (Max 20)
    vr, _, _ = volume_analysis(df)
    vs = min(int(vr * 10), 20)
    
    # 4. BB & PATTERN (Max 20)
    ps = 0
    if cl <= safe_float(l['bb_l']) * 1.01: ps += 10
    if "Engulfing" in str(detect_patterns(df)): ps += 10

    score = min(ts + ms + vs + ps, 100)
    return score, {'Trend':ts, 'Momentum':ms, 'Volume':vs, 'Extra':ps}

def get_signal(df, score):
    l = df.iloc[-1]
    cl = safe_float(l['close'])
    rsi = safe_float(l['rsi'] if 'rsi' in df.columns else 50)
    e20 = safe_float(l['ema20'] if 'ema20' in df.columns else cl)
    macd = safe_float(l['macd'] if 'macd' in df.columns else 0)
    sig = safe_float(l['sig'] if 'sig' in df.columns else 0)
    atr = safe_float(ta.atr(df['high'], df['low'], df['close']).iloc[-1]) if len(df)>14 else cl*0.02

    sl = cl - (1.8 * atr); tp = cl + (2.5 * atr)
    rr = round((tp-cl)/(cl-sl), 2) if (cl-sl)>0 else 0

    # Logika Signal Lebih Adaptif
    if score >= 70 and macd > sig: return "⚡ STRONG BUY", "#00ff99", sl, tp, rr
    elif score >= 55 and cl > e20: return "✅ BUY", "#44dd88", sl, tp, rr
    elif rsi > 75: return "❌ SELL/AVOID", "#ff4466", sl, tp, rr
    elif score < 40: return "⚠️ WEAK/SKIP", "#ff8844", sl, tp, rr
    else: return "🔄 HOLD/WATCH", "#ffcc00", sl, tp, rr

# ─────────────────────────────────────────────────────────
# UI RENDER
# ─────────────────────────────────────────────────────────

st.markdown("<h1 style='text-align:center; color:#00bbff;'>⚡ IDX TERMINAL v4.1</h1>", unsafe_allow_html=True)

# Market Pulse (Sederhana)
ihsg = yf.download("^JKSE", period="5d", progress=False)
if not ihsg.empty:
    curr = ihsg['Close'].iloc[-1]
    prev = ihsg['Close'].iloc[-2]
    diff = ((curr-prev)/prev)*100
    st.metric("IHSG Composite", f"{curr:,.2f}", f"{diff:+.2f}%")

st.divider()

# Analysis Section
col1, col2 = st.columns([1, 3])
with col1:
    ticker_input = st.text_input("Masukkan Kode Saham (contoh: BBRI):", "BBCA").upper()
    ticker = ticker_input if ticker_input.endswith(".JK") else f"{ticker_input}.JK"
    period = st.selectbox("Periode:", ["6mo", "1y", "2y"], index=1)

with st.spinner(f"Menganalisis {ticker}..."):
    data = yf.download(ticker, period=period, progress=False)
    df = clean_df(data)
    
    if not df.empty and len(df) > 50:
        score, details = score_ticker(df)
        signal, color, sl, tp, rr = get_signal(df, score)
        
        with col2:
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"<div class='metric-card'>Score<br><span class='score-high'>{score}/100</span></div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='metric-card'>Signal<br><span style='color:{color}; font-size:24px; font-weight:bold;'>{signal}</span></div>", unsafe_allow_html=True)
            c3.markdown(f"<div class='metric-card'>R:R Ratio<br><span style='font-size:24px;'>1:{rr}</span></div>", unsafe_allow_html=True)

            # Chart
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1, row_heights=[0.7, 0.3])
            fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="Price"), row=1, col=1)
            fig.add_trace(go.Bar(x=df.index, y=df['volume'], name="Volume", marker_color="gray"), row=2, col=1)
            fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
            
            # Trading Plan
            st.info(f"**Trading Plan {ticker_input}:** Entry: {df['close'].iloc[-1]:,.0f} | Stop Loss: {sl:,.0f} | Take Profit: {tp:,.0f}")
    else:
        st.error("Data tidak cukup atau ticker tidak ditemukan.")
