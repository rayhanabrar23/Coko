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
.universe-badge {
    display:inline-block; background:#0a1428; border:1px solid #2244aa;
    color:#4488ff; padding:2px 10px; border-radius:12px; font-size:12px; margin:2px;
}
div[data-testid="stDataFrame"] { background: #0a0d15 !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────
# UNIVERSE DATABASE — IDX OFFICIAL INDICES
# ─────────────────────────────────────────────────────────

IDX30 = [
    "AADI","ADRO","AMMN","ANTM","AMRT","ASII","BBCA","BBNI","BBRI","BBTN",
    "BMRI","BRIS","BUKA","CPIN","EXCL","GOTO","ICBP","INCO","INDF","ISAT",
    "ITMG","KLBF","MDKA","MEDC","MIKA","PGEO","PTBA","TLKM","TOWR","UNTR"
]

LQ45 = IDX30 + [
    "ACES","AKRA","ARTO","BELI","BNGA","BSDE","CTRA","EMTK","GGRM","HMSP",
    "INTP","JSMR","MAPI","MYOR","PGAS","PNBN","PWON","SMGR","TBIG","TINS",
    "TKIM","UNVR","HEAL","BYAN","CMRY","DCII","DSSA","NCKL","INKP","SILO"
]
LQ45 = list(dict.fromkeys(LQ45))[:45]

IDX80_EXTRA = [
    "AVIA","BDMN","BKSL","BUMI","CDIA","DEWA","ENRG","GEMS","GIAA","JPFA",
    "MEDC","MTEL","NISP","NCKL","PGEO","SMRA","SSIA","TAPG","TCPI","TBIG",
    "SIDO","PYFA","ARCO","BRPT","FILM","ARCI","BBHI","CUAN","VKTR","SOHO",
    "MDIY","BSIM","BIPI","JSMR","MAPI","PNBN","INKP","MYOR","CBDK","GGRM"
]
IDX80 = list(dict.fromkeys(LQ45 + IDX80_EXTRA))[:80]

IDX_HIDIV20 = [
    "ADRO","ANTM","ASII","BBCA","BBNI","BBRI","BMRI","CPIN","GGRM","HMSP",
    "INDF","ITMG","KLBF","MEDC","PGAS","PTBA","SMGR","TLKM","UNTR","UNVR"
]

IDX_GROWTH30 = [
    "ARTO","BELI","BRIS","BUKA","CMRY","DCII","DSSA","EMTK","GOTO","HEAL",
    "MIKA","MDKA","MTEL","NCKL","PGEO","SILO","TBIG","TOWR","VKTR","AMMN",
    "AADI","CUAN","BRMS","MBMA","TCPI","BREN","PANI","ARCO","CBDK","PGUN"
]

IDX_SMC = [
    "ACES","AKRA","BDMN","BNGA","BSDE","CTRA","GIAA","INTP","JPFA","JSMR",
    "MAPI","MYOR","NISP","PNBN","PWON","SMGR","SMRA","SSIA","TAPG","TINS",
    "SIDO","PYFA","SOHO","FILM","AVIA","BBHI","BUMI","GEMS","ARCI","DEWA",
    "ENRG","BIPI","BSIM","MDIY","CDIA","BBTN","MEGA","MLPT","NSSS","MSIN"
]

MANUAL_SECTORS = {
    "FINANCE":    ["BBCA","BBRI","BMRI","BBNI","BRIS","ARTO","BNGA","PNBN","MEGA","BDMN","NISP","BTPN","BBHI","BSIM","BBTN","BNLI","BBSI"],
    "ENERGY":     ["ADRO","ITMG","PTBA","MEDC","AKRA","PGAS","ENRG","GEMS","AADI","BYAN","DSSA","TCPI","INDY","BIPI"],
    "HEALTHCARE": ["MIKA","HEAL","SILO","KLBF","SIDO","PYFA","SOHO","MIKA","BKSL"],
    "BASIC MAT":  ["ANTM","TINS","MDKA","SMGR","INTP","TPIA","INCO","NCKL","AMMN","ARCI","BRMS","MBMA","CITA","ADMR","EMAS"],
    "CONSUMER":   ["ACES","MAPI","AMRT","ICBP","INDF","GGRM","HMSP","UNVR","MYOR","CPIN","JPFA","CMRY","AVIA","MDIY"],
    "INFRA":      ["TLKM","ISAT","EXCL","TOWR","TBIG","JSMR","MTEL","GIAA","PGAS","PGEO"],
    "PROPERTY":   ["BSDE","PWON","CTRA","SMRA","SSIA","CBDK","BKSL","PANI","MKPI"],
    "TECH/DIGITAL":["GOTO","BUKA","EMTK","DCII","BELI","BBHI","ARTO","COIN","VKTR"],
}

INDEX_UNIVERSE = {
    "IDX30 (Blue Chip, ~30 saham)":       IDX30,
    "LQ45 (Liquid 45, ~45 saham)":        LQ45,
    "IDX80 (Broad Market, ~80 saham)":    IDX80,
    "IDX High Dividend 20":               IDX_HIDIV20,
    "IDX Growth30":                        IDX_GROWTH30,
    "IDX SMC Liquid (Small-Mid Cap)":     IDX_SMC,
    "ALL IDX (Combined, ~180 unik)":      list(dict.fromkeys(IDX80 + IDX_GROWTH30 + IDX_SMC + IDX_HIDIV20)),
}

SECTOR_PROXY = {
    "FINANCE":"BBCA","ENERGY":"ADRO","HEALTHCARE":"KLBF","BASIC MAT":"ANTM",
    "CONSUMER":"ICBP","INFRA":"TLKM","PROPERTY":"BSDE","TECH":"GOTO",
}

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
# ANALYSIS ENGINE — REVISED FOR AGGRESSIVE DAILY TRADE
# ─────────────────────────────────────────────────────────

def detect_patterns(df):
    if len(df) < 3: return ["—"]
    patterns = []
    o,h,l,c = df['open'].values, df['high'].values, df['low'].values, df['close'].values
    i = -1
    body = abs(c[i]-o[i]); rng = h[i]-l[i]
    uw = h[i]-max(c[i],o[i]); lw = min(c[i],o[i])-l[i]
    if rng > 0:
        if lw >= 2*body and uw <= 0.3*body:         patterns.append("🔨 Hammer (Bullish)")
        if uw >= 2*body and lw <= 0.3*body:          patterns.append("⬆️ Inv. Hammer")
        if body/rng < 0.1:                           patterns.append("✳️ Doji (Reversal)")
        if rng > 0 and body/rng > 0.85:
            patterns.append("💪 Bullish Marubozu" if c[i]>o[i] else "👇 Bearish Marubozu")
    pb = abs(c[-2]-o[-2])
    if c[-2]<o[-2] and c[i]>o[i] and body>pb:       patterns.append("🟢 Bullish Engulfing")
    if c[-2]>o[-2] and c[i]<o[i] and body>pb:       patterns.append("🔴 Bearish Engulfing")
    if len(df)>=3:
        if c[-3]<o[-3] and abs(c[-2]-o[-2])<0.003*c[-2] and c[i]>o[i]: patterns.append("🌅 Morning Star")
        if c[-3]>o[-3] and abs(c[-2]-o[-2])<0.003*c[-2] and c[i]<o[i]: patterns.append("🌇 Evening Star")
    return patterns or ["— No Pattern"]

def volume_analysis(df, surge_threshold=1.2):
    """
    REVISED: Threshold diturunkan dari 1.5x ke 1.2x untuk menangkap lebih banyak momentum.
    Return: (ratio, label, is_surge_light, is_surge_strong)
    """
    if 'volume' not in df.columns or len(df)<20: return 0,"N/A",False,False
    avg = df['volume'].rolling(20).mean().iloc[-1]
    last = df['volume'].iloc[-1]
    ratio = safe_float(last/avg) if avg>0 else 0
    is_surge_light  = ratio >= 1.2   # Surge ringan — minat mulai masuk
    is_surge_strong = ratio >= 1.5   # Surge kuat — konfirmasi institusional
    label = f"{ratio:.1f}x"
    if is_surge_strong: label += " 🔥🔥"
    elif is_surge_light: label += " 🔥"
    return ratio, label, is_surge_light, is_surge_strong

def score_ticker(df, mode="aggressive"):
    """
    Multi-factor score 0-100.

    CHANGES vs v3 (aggressive mode):
    1. BB Zone: Sekarang juga kasih score untuk momentum play di atas midband (tidak hanya reversal).
    2. RSI: Zona 55-72 dapat score penuh — cocok untuk momentum/breakout play.
    3. Volume: Threshold surge diturunkan ke 1.2x.
    4. Min data requirement: Diturunkan ke 30 candle (dari 52).
    """
    min_candles = 30 if mode == "aggressive" else 52
    if df.empty or len(df) < min_candles: return 0, {}
    df = df.copy()
    df['ema20'] = ta.ema(df['close'], length=20)
    df['ema50'] = ta.ema(df['close'], length=50)
    df['rsi']   = ta.rsi(df['close'], length=14)
    df['atr']   = ta.atr(df['high'], df['low'], df['close'], length=14)
    macd_df     = ta.macd(df['close'], fast=12, slow=26, signal=9)
    if macd_df is not None and not macd_df.empty:
        df['macd']=macd_df.iloc[:,0]; df['sig']=macd_df.iloc[:,1]; df['hist']=macd_df.iloc[:,2]
    else:
        df['macd']=df['sig']=df['hist']=0
    bb = ta.bbands(df['close'], length=20, std=2)
    if bb is not None and not bb.empty:
        df['bb_u']=bb.iloc[:,0]; df['bb_m']=bb.iloc[:,1]; df['bb_l']=bb.iloc[:,2]
    else:
        df['bb_u']=df['bb_m']=df['bb_l']=df['close']

    l=df.iloc[-1]
    cl=safe_float(l['close']); e20=safe_float(l['ema20']); e50=safe_float(l['ema50'])
    rsi=safe_float(l['rsi']); macd=safe_float(l['macd']); sig=safe_float(l['sig'])
    hist=safe_float(l['hist']); bb_l=safe_float(l['bb_l']); bb_m=safe_float(l['bb_m']); bb_u=safe_float(l['bb_u'])

    # ── 1. TREND (0-25) — tidak berubah ──
    ts=0
    if cl>e20: ts+=12
    if cl>e50: ts+=8
    gap=(cl-e20)/e20*100 if e20 else 0
    if -1<=gap<=3: ts+=5
    # Bonus kecil: breakout baru dari EMA20 (gap 3-6%) masih valid untuk momentum play
    elif 3<gap<=6 and mode=="aggressive": ts+=3

    # ── 2. MOMENTUM — RSI (0-25) — REVISED ──
    ms=0
    if mode == "aggressive":
        # FIX: RSI 55-72 = zona momentum ideal untuk daily trade (breakout play)
        if 55 <= rsi <= 72:   ms += 15   # Prime momentum zone
        elif 40 <= rsi < 55:  ms += 12   # Accumulation / rebound zone
        elif 30 <= rsi < 40:  ms += 8    # Oversold — high risk/reward rebound
        elif 72 < rsi <= 78:  ms += 5    # Panas tapi masih bisa lanjut
        # RSI > 78 atau < 30: dapat 0
    else:
        if 40<=rsi<=60: ms+=15
        elif 30<=rsi<40 or 60<rsi<=65: ms+=8

    # MACD — tidak berubah
    if macd > sig: ms += 7
    if hist > 0 and len(df) > 1 and safe_float(df['hist'].iloc[-2]) >= 0 and hist > safe_float(df['hist'].iloc[-2]):
        ms += 3

    # ── 3. VOLUME (0-20) — REVISED ──
    # FIX: Pakai 4 level berbeda, threshold awal diturunkan ke 1.2x
    vr, _, is_surge_light, is_surge_strong = volume_analysis(df)
    if is_surge_strong:   vs = 20
    elif is_surge_light:  vs = 14   # 1.2x–1.5x dapat 14 (sebelumnya 0 kalau < 1.5x)
    elif vr >= 1.0:       vs = 8    # Volume rata-rata — netral
    elif vr >= 0.8:       vs = 4
    else:                 vs = 0

    # ── 4. BB ZONE (0-15) — REVISED ──
    # FIX: Sekarang ada 3 skenario valid, tidak hanya reversal dari lower band
    bs = 0
    if cl <= bb_l * 1.01:
        bs = 15   # Skenario REVERSAL: touch lower BB (tetap sama)
    elif cl <= bb_m:
        bs = 8    # Skenario REBOUND: antara lower dan midband
    elif mode == "aggressive":
        # FIX BARU: Skenario BREAKOUT — harga di atas midband dan melebar
        bb_width = (bb_u - bb_l) / bb_m if bb_m > 0 else 0
        bb_prev_u = safe_float(df['bb_u'].iloc[-2]) if len(df) > 1 else bb_u
        bb_expanding = bb_u > bb_prev_u  # Bandwidth melebar = momentum kuat
        if cl > bb_m and cl < bb_u * 0.97 and bb_expanding:
            bs = 10  # Breakout play — harga di upper half BB dan masih expanding
        elif cl > bb_m and cl < bb_u * 0.97:
            bs = 6   # Di atas midband tapi bandwidth tidak expanding

    # ── 5. PATTERN (0-15) — tidak berubah ──
    pats=detect_patterns(df); ps=0
    for p in pats:
        if any(k in p for k in ['Engulfing','Morning Star','Hammer','Marubozu']): ps=15; break
        elif 'Doji' in p or 'Inv.' in p: ps=max(ps,5)

    score=min(ts+ms+vs+bs+ps,100)
    detail={'Trend':ts,'Momentum':ms,'Volume':vs,'BB Zone':bs,'Pattern':ps}
    return score, detail

def get_signal(df, score, mode="aggressive"):
    """
    REVISED:
    - STRONG BUY: RSI threshold dinaikkan dari <65 ke <72
    - BUY: RSI threshold dinaikkan dari <70 ke <75
    - Tambah kondisi: breakout above EMA20 dengan volume surge dapat upgrade
    """
    l=df.iloc[-1]
    cl=safe_float(l['close']); e20=safe_float(l['ema20'] if 'ema20' in df.columns else l['close'])
    e50=safe_float(l['ema50'] if 'ema50' in df.columns else l['close'])
    rsi=safe_float(l['rsi'] if 'rsi' in df.columns else 50)
    macd=safe_float(l['macd'] if 'macd' in df.columns else 0)
    sig=safe_float(l['sig'] if 'sig' in df.columns else 0)
    atr=safe_float(l['atr'] if 'atr' in df.columns else cl*0.02)

    sl=cl-(1.5*atr); tp=cl+(2.5*atr)
    rr=round((tp-cl)/(cl-sl),2) if (cl-sl)>0 else 0

    # Volume check untuk upgrade signal
    vr, _, is_surge_light, is_surge_strong = volume_analysis(df)

    if mode == "aggressive":
        # FIX: RSI threshold dinaikkan — 55-72 adalah prime zone untuk momentum play
        if score>=70 and cl>e20 and rsi<72 and macd>sig:
            # Bonus: volume surge kuat = STRONG BUY bahkan di RSI lebih tinggi
            if is_surge_strong and rsi < 76:
                return "⚡ STRONG BUY","#00ff99",sl,tp,rr
            return "⚡ STRONG BUY","#00ff99",sl,tp,rr
        # FIX: BUY threshold RSI dinaikkan dari <70 ke <75
        elif score>=55 and cl>e20 and rsi<75:
            return "✅ BUY","#44dd88",sl,tp,rr
        # FIX BARU: Near-breakout — harga baru tembus EMA20 dari bawah + volume surge
        elif score>=50 and cl>e20*0.99 and cl<=e20*1.015 and is_surge_light and macd>sig:
            return "🚀 BREAKOUT WATCH","#44aaff",sl,tp,rr
        elif rsi>78 or (cl<e50 and cl<e20 and score<35):
            return "❌ SELL/AVOID","#ff4466",sl,tp,rr
        elif score<40:
            return "⚠️ WEAK/SKIP","#ff8844",sl,tp,rr
        else:
            return "🔄 HOLD/WATCH","#ffcc00",sl,tp,rr
    else:
        # Mode konservatif — original logic
        if score>=70 and cl>e20 and rsi<65 and macd>sig:   return "⚡ STRONG BUY","#00ff99",sl,tp,rr
        elif score>=55 and cl>e20 and rsi<70:               return "✅ BUY","#44dd88",sl,tp,rr
        elif rsi>75 or (cl<e50 and cl<e20 and score<35):   return "❌ SELL/AVOID","#ff4466",sl,tp,rr
        elif score<40:                                      return "⚠️ WEAK/SKIP","#ff8844",sl,tp,rr
        else:                                               return "🔄 HOLD/WATCH","#ffcc00",sl,tp,rr

def analyze_full(ticker, period="1y", mode="aggressive"):
    df=yf.download(ticker,period=period,progress=False); df=clean_df(df)
    min_candles = 30 if mode == "aggressive" else 52
    if df.empty or len(df)<min_candles: return None
    df['ema20']=ta.ema(df['close'],length=20); df['ema50']=ta.ema(df['close'],length=50)
    df['rsi']=ta.rsi(df['close'],length=14); df['atr']=ta.atr(df['high'],df['low'],df['close'],length=14)
    macd_df=ta.macd(df['close'],fast=12,slow=26,signal=9)
    if macd_df is not None and not macd_df.empty:
        df['macd']=macd_df.iloc[:,0]; df['sig']=macd_df.iloc[:,1]; df['hist']=macd_df.iloc[:,2]
    else:
        df['macd']=df['sig']=df['hist']=0
    bb=ta.bbands(df['close'],length=20,std=2)
    if bb is not None and not bb.empty:
        df['bb_u']=bb.iloc[:,0]; df['bb_m']=bb.iloc[:,1]; df['bb_l']=bb.iloc[:,2]
    else:
        df['bb_u']=df['bb_m']=df['bb_l']=df['close']
    df['vol_ma20']=df['volume'].rolling(20).mean()
    return df

def calc_sr(df):
    if len(df)<20: return [],[]
    hh=df['high'].rolling(5,center=True).max()
    ll=df['low'].rolling(5,center=True).min()
    res=sorted(df[df['high']==hh]['high'].dropna().unique(),reverse=True)[:3]
    sup=sorted(df[df['low']==ll]['low'].dropna().unique())[:3]
    return list(res), list(sup)

# ─────────────────────────────────────────────────────────
# INTERPRETASI ENGINE
# ─────────────────────────────────────────────────────────

def interpret_analysis(ticker, score, detail, signal, df, sl, tp, rr, pats, vr, vsurge_light, vsurge_strong, ihsg_change=0.0):
    l = df.iloc[-1]
    cl   = safe_float(l['close'])
    rsi  = safe_float(l['rsi']   if 'rsi'   in df.columns else 50)
    e20  = safe_float(l['ema20'] if 'ema20' in df.columns else cl)
    e50  = safe_float(l['ema50'] if 'ema50' in df.columns else cl)
    macd = safe_float(l['macd']  if 'macd'  in df.columns else 0)
    sig  = safe_float(l['sig']   if 'sig'   in df.columns else 0)
    atr  = safe_float(l['atr']   if 'atr'   in df.columns else cl * 0.02)
    name = ticker.replace(".JK","")

    pros = []; cons = []; cautions = []

    # TREND
    gap_pct = (cl - e20) / e20 * 100 if e20 else 0
    if cl > e20 and cl > e50:
        pros.append(f"Harga berada di atas EMA20 ({e20:,.0f}) dan EMA50 ({e50:,.0f}), tren naik jangka pendek dan menengah masih kuat.")
    elif cl > e20 and cl <= e50:
        cautions.append(f"Harga sudah di atas EMA20 ({gap_pct:+.1f}%), tapi masih di bawah EMA50 — tren menengah belum recovery penuh.")
    elif -1.5 <= gap_pct < 0:
        cautions.append(f"Harga sedikit di bawah EMA20 ({gap_pct:.1f}%) — masih dalam toleransi untuk setup breakout. Pantau apakah ada candle penembus.")
    else:
        cons.append(f"Harga ({cl:,.0f}) masih di bawah EMA20 ({e20:,.0f}) dan EMA50 ({e50:,.0f}). Tren masih negatif.")

    if -0.5 <= gap_pct <= 3:
        pros.append(f"Posisi harga {gap_pct:+.1f}% dari EMA20 — zona entry ideal sebelum breakout terjadi.")
    elif 3 < gap_pct <= 6:
        cautions.append(f"Harga sudah {gap_pct:.1f}% di atas EMA20. Masih acceptable untuk momentum play tapi sizing lebih kecil.")
    elif gap_pct > 6:
        cautions.append(f"Harga {gap_pct:.1f}% di atas EMA20 — sudah cukup jauh, risiko koreksi ke EMA20 meningkat.")

    # MOMENTUM — RSI (revised interpretation)
    if 55 <= rsi <= 72:
        pros.append(f"RSI {rsi:.1f} berada di zona momentum prime (55–72). Ini sweet spot untuk daily trade breakout — cukup kuat tapi belum overbought ekstrem.")
    elif 40 <= rsi < 55:
        pros.append(f"RSI {rsi:.1f} di zona akumulasi — saham sedang istirahat dan siap kembali naik.")
    elif rsi < 35:
        pros.append(f"RSI {rsi:.1f} oversold ekstrem — peluang rebound teknikal sangat tinggi, tapi pastikan ada konfirmasi candle bullish.")
    elif 72 < rsi <= 78:
        cautions.append(f"RSI {rsi:.1f} mulai panas. Masih bisa lanjut kalau volume kuat, tapi kurangi sizing dan perketat SL.")
    elif rsi > 78:
        cons.append(f"RSI {rsi:.1f} overbought berlebihan (>78). Probabilitas koreksi dalam 1–2 hari sangat tinggi. Hindari entry baru.")

    # MACD
    if macd > sig:
        hist_val = safe_float(l['hist'] if 'hist' in df.columns else 0)
        prev_hist = safe_float(df['hist'].iloc[-2] if 'hist' in df.columns and len(df)>1 else 0)
        if hist_val > prev_hist:
            pros.append(f"MACD golden cross dan histogram terus membesar — momentum beli semakin akseleratif. Ini sinyal terkuat.")
        else:
            pros.append(f"MACD di atas signal line (bullish) — tekanan beli masih dominan.")
    else:
        cons.append(f"MACD masih di bawah signal line. Tunggu golden cross untuk konfirmasi entry.")

    # VOLUME — revised dengan 2 level surge
    if vsurge_strong:
        pros.append(f"Volume {vr:.1f}x rata-rata 20 hari — surge kuat 🔥🔥. Konfirmasi institusional, breakout dengan volume ini jauh lebih reliable.")
    elif vsurge_light:
        pros.append(f"Volume {vr:.1f}x rata-rata — surge ringan 🔥. Minat beli mulai masuk, perhatikan apakah volume terus meningkat di sesi berikutnya.")
    elif vr >= 1.0:
        cautions.append(f"Volume di rata-rata ({vr:.1f}x). Pergerakan belum dikonfirmasi volume besar — valid tapi waspadai false move.")
    else:
        cautions.append(f"Volume sepi ({vr:.1f}x rata-rata). Pergerakan harga tanpa volume solid rentan reversal tiba-tiba.")

    # BOLLINGER BAND — revised dengan skenario breakout
    if 'bb_l' in df.columns and 'bb_m' in df.columns:
        bb_l = safe_float(l['bb_l']); bb_m = safe_float(l['bb_m']); bb_u = safe_float(l['bb_u'])
        if cl <= bb_l * 1.01:
            pros.append(f"Harga menyentuh lower BB ({bb_l:,.0f}) — zona oversold BB, sering berbalik ke midband ({bb_m:,.0f}).")
        elif cl <= bb_m:
            pros.append(f"Harga antara lower BB dan midband — zona akumulasi yang bagus untuk entry sebelum rebound ke upper band.")
        elif cl > bb_m and cl < bb_u * 0.97:
            bb_width = (bb_u - bb_l) / bb_m if bb_m > 0 else 0
            if bb_width > 0.04:
                pros.append(f"Harga di upper half BB dan bandwidth masih melebar — ini tanda momentum breakout yang sehat, bukan overbought.")
            else:
                cautions.append(f"Harga di atas midband BB tapi bandwidth mulai menyempit — momentum bisa melambat.")
        elif cl >= bb_u * 0.97:
            cons.append(f"Harga mendekati upper BB ({bb_u:,.0f}). Untuk reversal play hindari entry di sini; untuk momentum play, set SL ketat.")

    # PATTERN
    pat_str = pats[0] if pats else "—"
    if any(k in pat_str for k in ['Engulfing','Morning Star','Hammer','Marubozu']):
        pros.append(f"Pola candlestick bullish '{pat_str.replace('🟢','').replace('🔨','').replace('🌅','').replace('💪','').strip()}' terdeteksi — konfirmasi visual pembalikan atau lanjutan naik.")
    elif any(k in pat_str for k in ['Bearish','Evening Star']):
        cons.append(f"Pola bearish terdeteksi — waspada tekanan jual meningkat.")
    elif 'Doji' in pat_str:
        cautions.append(f"Pola Doji — pasar ragu-ragu. Tunggu candle konfirmasi sebelum masuk.")

    # MARKET CONTEXT
    if ihsg_change > 0.5:
        pros.append(f"IHSG momentum positif ({ihsg_change:+.2f}%) — tailwind dari market secara keseluruhan.")
    elif ihsg_change < -0.5:
        cautions.append(f"IHSG sedang melemah ({ihsg_change:+.2f}%). Bahkan setup bagus bisa ikut tertekan market.")

    # R:R
    if rr >= 2.0:
        pros.append(f"Risk:Reward 1:{rr} — secara matematis menguntungkan. Risiko Rp 1 untuk potensi Rp {rr}.")
    elif 1.5 <= rr < 2.0:
        cautions.append(f"R:R 1:{rr} — di batas minimum. Masih acceptable tapi jangan masuk kalau ada keraguan lain.")
    else:
        cautions.append(f"R:R hanya 1:{rr} — terlalu kecil. Skip setup ini, cari entry yang lebih baik.")

    # VERDICT
    score_cons = len(cons); score_pros = len(pros)
    if "STRONG BUY" in signal or ("BUY" in signal and score_cons == 0 and score_pros >= 4):
        verdict_title = f"✅ LAYAK DIBELI — Setup {name} Tergolong Kuat"
        verdict_color = "#00ff99"; confidence = "TINGGI"; conf_color = "#00ff99"
        verdict_open = f"Skor {score}/100 — saham <b>{name}</b> di Rp {cl:,.0f} menunjukkan setup beli yang kuat untuk daily trade."
    elif "BREAKOUT WATCH" in signal:
        verdict_title = f"🚀 BREAKOUT SETUP — {name} Siap Menerobos EMA20"
        verdict_color = "#44aaff"; confidence = "MOMENTUM"; conf_color = "#44aaff"
        verdict_open = f"Skor {score}/100 — <b>{name}</b> di Rp {cl:,.0f} sedang dalam posisi kritis di dekat EMA20 dengan volume mulai naik. Setup breakout yang perlu dipantau ketat."
    elif "BUY" in signal and score_cons <= 1:
        verdict_title = f"🟡 BOLEH DIPERTIMBANGKAN — Setup {name} Cukup Layak"
        verdict_color = "#ffcc00"; confidence = "SEDANG"; conf_color = "#ffcc00"
        verdict_open = f"Skor {score}/100 — <b>{name}</b> di Rp {cl:,.0f} punya setup yang layak untuk daily trade dengan beberapa catatan."
    elif "SELL" in signal or "WEAK" in signal or score_cons >= 3:
        verdict_title = f"❌ TIDAK DISARANKAN — {name} Belum Siap"
        verdict_color = "#ff4466"; confidence = "RENDAH"; conf_color = "#ff4466"
        verdict_open = f"Skor {score}/100 — <b>{name}</b> di Rp {cl:,.0f} belum memiliki setup yang aman saat ini."
    else:
        verdict_title = f"⏳ TUNGGU KONFIRMASI — {name} Transisi"
        verdict_color = "#aaaaff"; confidence = "MENUNGGU"; conf_color = "#aaaaff"
        verdict_open = f"Skor {score}/100 — {name} sedang transisi. Campuran sinyal positif dan negatif, tunggu konfirmasi lebih jelas."

    if "BUY" in signal and "WEAK" not in signal:
        closing = (
            f"<b>Kesimpulan:</b> Entry area Rp {cl:,.0f}–{cl*1.005:,.0f}, "
            f"SL Rp {sl:,.0f} (−{((cl-sl)/cl*100):.1f}%), "
            f"TP Rp {tp:,.0f} (+{((tp-cl)/cl*100):.1f}%). "
            f"Hold 1–3 hari trading."
        )
    elif "BREAKOUT" in signal:
        closing = (
            f"<b>Strategi:</b> Pantau penembusan EMA20 ({e20:,.0f}) dengan volume. "
            f"Entry saat candle konfirmasi menutup di atas EMA20. "
            f"SL Rp {sl:,.0f}, TP Rp {tp:,.0f}."
        )
    else:
        closing = (
            f"<b>Alternatif:</b> Masukkan {name} ke watchlist. Tunggu RSI di 40–65 "
            f"dan MACD golden cross sebelum entry."
        )

    pros_html = "".join([f"<li style='margin-bottom:6px;color:#b0ffcc'>✅ {p}</li>" for p in pros])
    cons_html = "".join([f"<li style='margin-bottom:6px;color:#ffaaaa'>❌ {c}</li>" for c in cons])
    caut_html = "".join([f"<li style='margin-bottom:6px;color:#ffeebb'>⚠️ {w}</li>" for w in cautions])

    support_section = ""
    if pros_html:
        support_section += f"<p style='color:#668;font-size:12px;margin:8px 0 4px'>FAKTOR PENDUKUNG:</p><ul style='margin:0;padding-left:20px'>{pros_html}</ul>"
    if cons_html:
        support_section += f"<p style='color:#668;font-size:12px;margin:10px 0 4px'>FAKTOR PENGHAMBAT:</p><ul style='margin:0;padding-left:20px'>{cons_html}</ul>"
    if caut_html:
        support_section += f"<p style='color:#668;font-size:12px;margin:10px 0 4px'>CATATAN KEHATI-HATIAN:</p><ul style='margin:0;padding-left:20px'>{caut_html}</ul>"

    html = f"""
    <div style='background:linear-gradient(135deg,#080e1a,#0c1525);border:2px solid {verdict_color}44;
                border-left:4px solid {verdict_color};border-radius:12px;padding:20px;margin:16px 0;'>
        <div style='font-size:18px;font-weight:bold;color:{verdict_color};margin-bottom:10px'>
            {verdict_title}
            &nbsp;<span style='font-size:12px;background:{conf_color}22;color:{conf_color};
                          padding:2px 10px;border-radius:10px;border:1px solid {conf_color}44'>
                KEYAKINAN: {confidence}
            </span>
        </div>
        <p style='color:#ccd;line-height:1.7;margin:0 0 14px'>{verdict_open}</p>
        {support_section}
        <div style='margin-top:14px;padding:12px;background:#ffffff08;border-radius:8px;
                    color:#dde;line-height:1.7;font-size:14px;border-left:3px solid {verdict_color}88'>
            {closing}
        </div>
        <p style='color:#445;font-size:11px;margin-top:10px;margin-bottom:0'>
            ⚠️ Analisis teknikal saja — tidak memperhitungkan fundamental, news, atau kondisi makro.
            Gunakan manajemen risiko ketat. Bukan saran investasi.
        </p>
    </div>
    """
    return html, confidence, conf_color


def interpret_scanner_row(row, ihsg_change=0.0):
    name    = row['Ticker']
    score   = row['Score']
    signal  = row['Signal']
    rsi     = row['RSI']
    vsurge  = "🔥" in str(row.get('Vol',''))
    macd_ok = row['MACD'] == "✅"
    ema_ok  = row['EMA20'] == "✅"
    pat     = row.get('Pattern','—')

    reasons  = []
    warnings = []

    if score >= 70:     reasons.append(f"skor tinggi ({score}/100)")
    if vsurge:          reasons.append("volume surge 🔥")
    if macd_ok:         reasons.append("MACD bullish")
    if ema_ok:          reasons.append("di atas EMA20")
    if 55 <= rsi <= 72: reasons.append(f"RSI momentum prime ({rsi})")
    elif 40 <= rsi < 55: reasons.append(f"RSI akumulasi ({rsi})")
    elif rsi < 35:      reasons.append(f"RSI oversold ({rsi}) — potensi rebound")

    if not ema_ok:      warnings.append("harga di bawah EMA20")
    if not macd_ok:     warnings.append("MACD masih bearish")
    if rsi > 75:        warnings.append(f"RSI panas ({rsi})")
    if not vsurge:      warnings.append("volume belum surge")
    if ihsg_change < -0.5: warnings.append("IHSG melemah")

    if "STRONG" in signal and not warnings:
        verdict = f"🟢 <b>BUY SEKARANG</b> — {', '.join(reasons[:3])}. Setup premium."
    elif "BREAKOUT" in signal:
        verdict = f"🚀 <b>PANTAU BREAKOUT</b> — {', '.join(reasons[:2])}. Entry saat penembusan EMA20 konfirmasi."
    elif "BUY" in signal and len(warnings) <= 1:
        w_note = f" Perhatikan: {warnings[0]}." if warnings else ""
        verdict = f"🟡 <b>BUY sizing kecil</b> — {', '.join(reasons[:2])}.{w_note}"
    elif warnings:
        verdict = f"⏳ <b>Tunggu konfirmasi</b> — {', '.join(warnings[:2])}. Masuk setelah reversal konfirmasi."
    else:
        verdict = f"👀 <b>Watchlist</b> — Setup sedang terbentuk."

    return verdict


# ─────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────
st.markdown("""
<h1 style='text-align:center;color:#00bbff;letter-spacing:3px;font-family:monospace;'>
⚡ IDX TERMINAL v4 — AGGRESSIVE DAILY SCANNER
</h1>
<p style='text-align:center;color:#445566;font-family:monospace;'>
Multi-Factor Daily Trade Analyzer · IDX30 / LQ45 / IDX80 / Growth30 / SMC · 180+ Universe
</p>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────
# MODE SELECTOR — BARU
# ─────────────────────────────────────────────────────────
col_mode, col_info = st.columns([1,3])
with col_mode:
    trade_mode = st.radio(
        "⚙️ Trade Mode:",
        ["🚀 Aggressive (Daily)", "🛡️ Conservative"],
        index=0,
        help=(
            "Aggressive: RSI zone 55-72, volume surge 1.2x, BB breakout play, min data 30 candle.\n"
            "Conservative: RSI zone 40-60, volume surge 1.5x, BB reversal only, min data 52 candle."
        )
    )
mode = "aggressive" if "Aggressive" in trade_mode else "conservative"

with col_info:
    if mode == "aggressive":
        st.info(
            "**Mode Aggressive** aktif — "
            "RSI prime zone 55–72 ✅ | "
            "Volume surge dari 1.2x 🔥 | "
            "BB breakout play dihitung ✅ | "
            "Min data 30 candle ✅ | "
            "RSI threshold STRONG BUY dinaikkan ke <72"
        )
    else:
        st.warning(
            "**Mode Conservative** aktif — "
            "RSI ideal 40–60 | "
            "Volume surge 1.5x | "
            "BB reversal only | "
            "Min data 52 candle"
        )

st.divider()

# ─────────────────────────────────────────────────────────
# MARKET PULSE
# ─────────────────────────────────────────────────────────
col_ihsg, col_sector = st.columns([1,1])
ihsg_df = pd.DataFrame(); ihsg_change=0.0

with col_ihsg:
    st.subheader("📈 IHSG Market Pulse")
    raw = yf.download("^JKSE",period="1y",progress=False); ihsg_df=clean_df(raw)
    if not ihsg_df.empty:
        ihsg_change=((ihsg_df['close'].iloc[-1]-ihsg_df['close'].iloc[-2])/ihsg_df['close'].iloc[-2])*100
        ihsg_df['ma20']=ihsg_df['close'].rolling(20).mean()
        fig=go.Figure()
        fig.add_trace(go.Scatter(x=ihsg_df.index,y=ihsg_df['close'],fill='tozeroy',
                                 line_color='#00bbff',fillcolor='rgba(0,187,255,0.07)',name='IHSG'))
        fig.add_trace(go.Scatter(x=ihsg_df.index,y=ihsg_df['ma20'],
                                 line=dict(color='orange',width=1.5,dash='dot'),name='MA20'))
        fig.update_layout(height=230,template='plotly_dark',margin=dict(l=0,r=0,t=0,b=0),
                          showlegend=False,xaxis_rangeslider_visible=False)
        st.plotly_chart(fig,use_container_width=True)
        ca,cb,cc,cd=st.columns(4)
        ca.metric("Last",f"{ihsg_df['close'].iloc[-1]:,.0f}")
        cb.metric("Change",f"{ihsg_change:+.2f}%")
        cc.metric("52W High",f"{ihsg_df['high'].max():,.0f}")
        cd.metric("52W Low",f"{ihsg_df['low'].min():,.0f}")

with col_sector:
    st.subheader("🗺️ Sectoral Heatmap (5D)")
    sec_data=[]
    for s,t in SECTOR_PROXY.items():
        try:
            d=clean_df(yf.download(f"{t}.JK",period="10d",progress=False))
            if not d.empty and len(d)>=5:
                perf=((d['close'].iloc[-1]-d['close'].iloc[-5])/d['close'].iloc[-5])*100
                sec_data.append({"Sektor":s,"Perf":round(safe_float(perf),2),"Parent":"IDX","Size":10})
        except: continue
    if sec_data:
        df_s=pd.DataFrame(sec_data)
        fig=px.treemap(df_s,path=['Parent','Sektor'],values='Size',color='Perf',
                       color_continuous_scale='RdYlGn',range_color=[-3,3])
        fig.update_layout(height=230,margin=dict(l=0,r=0,t=0,b=0),template='plotly_dark')
        st.plotly_chart(fig,use_container_width=True)
        best=max(sec_data,key=lambda x:x['Perf']); worst=min(sec_data,key=lambda x:x['Perf'])
        bias = "🟢 BULLISH" if ihsg_change>0.3 else ("🔴 BEARISH" if ihsg_change<-0.3 else "🟡 SIDEWAYS")
        st.caption(f"Market Bias: **{bias}** | 🏆 {best['Sektor']} ({best['Perf']:+.2f}%) | ⚠️ {worst['Sektor']} ({worst['Perf']:+.2f}%)")

st.divider()

# ─────────────────────────────────────────────────────────
# DEEP ANALYSIS — SINGLE TICKER
# ─────────────────────────────────────────────────────────
st.subheader("🔬 Deep Analysis — Single Ticker")
inp1,inp2,inp3 = st.columns([1,2,1])
with inp1:
    manual = st.text_input("🔍 Kode (contoh: BBRI)","").upper()
with inp2:
    sec_sel = st.selectbox("📂 Pilih Sektor:",["—"]+list(MANUAL_SECTORS.keys()))
with inp3:
    tf = st.selectbox("📅 Timeframe:",["6mo","1y","2y"],index=1)

target=None
if manual:
    target=manual if manual.endswith(".JK") else f"{manual}.JK"
elif sec_sel!="—":
    pick=st.selectbox("Pilih Saham:", add_jk(MANUAL_SECTORS[sec_sel]))
    target=pick

if target:
    with st.spinner(f"Menganalisis {target}..."):
        df=analyze_full(target, period=tf, mode=mode)
    if df is not None:
        score,detail=score_ticker(df, mode=mode)
        signal,sig_color,sl,tp,rr=get_signal(df, score, mode=mode)
        l=df.iloc[-1]
        pats=detect_patterns(df)
        vr, vlbl, vsurge_light, vsurge_strong = volume_analysis(df)
        res,sup=calc_sr(df)
        cl=safe_float(l['close']); rsi=safe_float(l['rsi'])
        e20=safe_float(l['ema20']); e50=safe_float(l['ema50'])
        atr=safe_float(l['atr']); macd=safe_float(l['macd']); sig_v=safe_float(l['sig'])

        sc=("score-high" if score>=65 else ("score-mid" if score>=45 else "score-low"))
        tag=("tag-sbuy" if "STRONG" in signal else ("tag-buy" if "BUY" in signal else ("tag-sell" if "SELL" in signal or "WEAK" in signal else "tag-hold")))

        st.markdown(f"### {target}")
        c1,c2,c3,c4,c5 = st.columns(5)
        with c1:
            st.markdown(f"<div class='metric-card'><div style='color:#556;font-size:11px'>CONFLUENCE SCORE</div><div class='{sc}'>{score}/100</div></div>",unsafe_allow_html=True)
        with c2:
            st.markdown(f"<div class='metric-card'><div style='color:#556;font-size:11px'>SIGNAL</div><div style='margin-top:8px'><span class='{tag}'>{signal}</span></div></div>",unsafe_allow_html=True)
        with c3: st.metric("RSI (14)",f"{rsi:.1f}",delta="Oversold" if rsi<35 else ("Overbought" if rsi>72 else "Normal"))
        with c4: st.metric("Volume", vlbl)
        with c5: st.metric("ATR",f"{atr:.0f}",help="Volatilitas harian rata-rata")

        st.write("")
        d1,d2,d3,d4,d5=st.columns(5)
        d1.error(f"❌ SL: {sl:,.0f}")
        d2.success(f"✅ TP: {tp:,.0f}")
        d3.info(f"⚖️ R:R = 1:{rr}")
        gap=(cl-e20)/e20*100 if e20 else 0
        d4.metric("vs EMA20",f"{gap:+.2f}%")
        d5.metric("MACD","Bullish ↑" if macd>sig_v else "Bearish ↓")

        left,mid,right=st.columns(3)
        with left:
            st.markdown("**📊 Score Breakdown**")
            sdf=pd.DataFrame(list(detail.items()),columns=["Factor","Score"])
            sdf["Max"]=[25,25,20,15,15]
            fig_s=go.Figure(go.Bar(x=sdf["Score"],y=sdf["Factor"],orientation='h',
                marker_color=['#00ff99' if s/m>=0.7 else ('#ffcc00' if s/m>=0.4 else '#ff4466') for s,m in zip(sdf["Score"],sdf["Max"])],
                text=sdf["Score"],textposition='auto'))
            fig_s.update_layout(height=200,template='plotly_dark',margin=dict(l=0,r=0,t=0,b=0),xaxis=dict(range=[0,25]))
            st.plotly_chart(fig_s,use_container_width=True)
        with mid:
            st.markdown("**🕯️ Patterns**")
            for p in pats: st.write(p)
            st.markdown("**📐 S/R Levels**")
            if res: st.markdown(f"🔴 R: {' | '.join([f'{r:,.0f}' for r in res[:2]])}")
            if sup: st.markdown(f"🟢 S: {' | '.join([f'{s:,.0f}' for s in sup[:2]])}")
        with right:
            st.markdown("**💡 Trade Setup**")
            risk=cl-sl; rew=tp-cl
            lot10=10_000_000/cl/100 if cl>0 else 0
            st.markdown(f"""
            - 💰 **Entry:** {cl:,.0f} – {cl*1.005:,.0f}
            - ❌ **Max Loss/lot:** Rp {risk*100:,.0f}
            - ✅ **Target/lot:** Rp {rew*100:,.0f}
            - 📦 **Est. lot (10jt):** {lot10:.0f} lot
            - ⏱️ **Hold:** 1–3 hari
            """)

        interp_html, conf_lbl, conf_clr = interpret_analysis(
            target, score, detail, signal, df, sl, tp, rr,
            pats, vr, vsurge_light, vsurge_strong, ihsg_change
        )
        st.markdown(interp_html, unsafe_allow_html=True)

        fig=make_subplots(rows=3,cols=1,shared_xaxes=True,row_heights=[0.55,0.25,0.20],
                          vertical_spacing=0.04,subplot_titles=("Price + Indicators","MACD","RSI + Volume"))
        fig.add_trace(go.Candlestick(x=df.index,open=df['open'],high=df['high'],low=df['low'],close=df['close'],
                                     increasing_line_color='#00ff99',decreasing_line_color='#ff4466',name='Price'),row=1,col=1)
        fig.add_trace(go.Scatter(x=df.index,y=df['ema20'],line=dict(color='orange',width=1.8),name='EMA20'),row=1,col=1)
        fig.add_trace(go.Scatter(x=df.index,y=df['ema50'],line=dict(color='#00aaff',width=1.2,dash='dot'),name='EMA50'),row=1,col=1)
        fig.add_trace(go.Scatter(x=df.index,y=df['bb_u'],line=dict(color='rgba(180,180,255,0.35)',width=1),name='BB',showlegend=False),row=1,col=1)
        fig.add_trace(go.Scatter(x=df.index,y=df['bb_l'],fill='tonexty',fillcolor='rgba(80,80,255,0.04)',
                                  line=dict(color='rgba(180,180,255,0.35)',width=1),showlegend=False),row=1,col=1)
        fig.add_hline(y=sl,line_dash="dash",line_color="#ff4466",annotation_text=f"SL {sl:,.0f}",row=1,col=1)
        fig.add_hline(y=tp,line_dash="dash",line_color="#00ff99",annotation_text=f"TP {tp:,.0f}",row=1,col=1)
        hc=['#00ff99' if v>=0 else '#ff4466' for v in df['hist'].fillna(0)]
        fig.add_trace(go.Bar(x=df.index,y=df['hist'],marker_color=hc,name='Hist',showlegend=False),row=2,col=1)
        fig.add_trace(go.Scatter(x=df.index,y=df['macd'],line=dict(color='#00bbff',width=1.5),name='MACD'),row=2,col=1)
        fig.add_trace(go.Scatter(x=df.index,y=df['sig'],line=dict(color='orange',width=1.5),name='Signal'),row=2,col=1)
        fig.add_trace(go.Scatter(x=df.index,y=df['rsi'],line=dict(color='#bb77ff',width=1.5),name='RSI'),row=3,col=1)
        fig.add_hline(y=72,line_dash="dot",line_color="red",annotation_text="OB (72)",row=3,col=1)
        fig.add_hline(y=30,line_dash="dot",line_color="green",annotation_text="OS (30)",row=3,col=1)
        # Tambah shading RSI prime zone (55-72) di chart
        fig.add_hrect(y0=55,y1=72,fillcolor="rgba(0,255,150,0.05)",line_width=0,row=3,col=1)
        vc=['#00ff99' if c>=o else '#ff4466' for c,o in zip(df['close'],df['open'])]
        fig.add_trace(go.Bar(x=df.index,y=df['volume']/df['volume'].max()*30,marker_color=vc,
                              opacity=0.35,showlegend=False),row=3,col=1)
        fig.update_layout(height=680,template='plotly_dark',xaxis_rangeslider_visible=False,
                          legend=dict(orientation='h',y=1.02),margin=dict(l=0,r=0,t=30,b=0))
        st.plotly_chart(fig,use_container_width=True)
    else:
        st.warning(f"Data tidak cukup untuk {target}.")

st.divider()

# ─────────────────────────────────────────────────────────
# SMART SCANNER
# ─────────────────────────────────────────────────────────
st.subheader("🎯 Smart Scanner — Pilih Universe Indeks IDX")

sc1,sc2,sc3,sc4 = st.columns([2,1,1,1])
with sc1:
    idx_choice = st.selectbox("📊 Universe / Indeks:",list(INDEX_UNIVERSE.keys()))
with sc2:
    also_sector = st.multiselect("➕ Tambah Sektor Manual:",list(MANUAL_SECTORS.keys()))
with sc3:
    # Default min score diturunkan ke 50 untuk mode aggressive
    default_min = 50 if mode == "aggressive" else 55
    min_score = st.slider("Min Score:",0,100,default_min)
with sc4:
    top_n = st.number_input("Top N Hasil:",5,50,10)

selected_universe = INDEX_UNIVERSE[idx_choice]
extra_from_sector = []
for sec in also_sector:
    extra_from_sector.extend(MANUAL_SECTORS[sec])
combined_universe = list(dict.fromkeys(selected_universe + extra_from_sector))

col_info1,col_info2=st.columns([3,1])
with col_info1:
    badge_html=" ".join([f"<span class='universe-badge'>{t}</span>" for t in combined_universe[:40]])
    if len(combined_universe)>40: badge_html+=f" <span class='universe-badge'>+{len(combined_universe)-40} lainnya</span>"
    st.markdown(f"**Universe aktif: {len(combined_universe)} saham**<br>{badge_html}",unsafe_allow_html=True)
with col_info2:
    signal_filter=st.selectbox("Filter Signal:",["Semua BUY","Strong BUY Only","Semua (incl HOLD)"])

st.write("")

with st.expander("⚙️ Filter Tambahan (Advanced)", expanded=False):
    fc1,fc2,fc3=st.columns(3)
    with fc1:
        # REVISED: Default min volume ratio diturunkan ke 0.8 (dari 1.0)
        min_vol_ratio=st.slider("Min Volume Ratio:",0.5,3.0,0.8,0.1)
        # REVISED: Default require_surge = False
        require_surge=st.checkbox("Wajib Volume Surge (🔥 ≥1.2x)",value=False)
        require_surge_strong=st.checkbox("Wajib Volume Surge Kuat (🔥🔥 ≥1.5x)",value=False)
    with fc2:
        # REVISED: Default min RSI diturunkan ke 30, max dinaikkan ke 75
        min_rsi=st.slider("RSI Min:",10,50,30)
        max_rsi=st.slider("RSI Max:",50,90,75)
    with fc3:
        require_macd_bull=st.checkbox("Wajib MACD Bullish Cross",value=False)
        # REVISED: Default require_above_ema = False (dari True)
        require_above_ema=st.checkbox(
            "Wajib Price > EMA20",
            value=False,
            help="Matikan untuk menangkap setup near-breakout (harga baru mau tembus EMA20)"
        )
        # BARU: Near-EMA tolerance
        ema_tolerance = st.slider(
            "Toleransi EMA20 (%):",
            -3.0, 0.0, -1.5, 0.1,
            help="Izinkan harga sampai berapa % di bawah EMA20. -1.5% = masih masuk jika harga max 1.5% di bawah EMA20."
        ) if not require_above_ema else 0.0

if st.button("🚀 MULAI SCAN SEKARANG",use_container_width=True,type="primary"):
    tickers_to_scan = add_jk(combined_universe)
    results=[]; prog=st.progress(0); status=st.empty(); errors=0

    for i,t in enumerate(tickers_to_scan):
        prog.progress((i+1)/len(tickers_to_scan))
        status.markdown(f"🔍 Scanning **{t}** ... ({i+1}/{len(tickers_to_scan)}) | Candidates: **{len(results)}**")
        try:
            # REVISED: Period scan dinaikkan ke 90d untuk cukupi min 30 candle
            d=clean_df(yf.download(t,period="90d",progress=False))
            min_c = 30 if mode=="aggressive" else 52
            if d.empty or len(d)<min_c: continue

            d['ema20_q']=ta.ema(d['close'],length=20)
            d['rsi_q']=ta.rsi(d['close'],length=14)
            last=d.iloc[-1]
            rsi_q=safe_float(last['rsi_q'])
            cl_q=safe_float(last['close'])
            ema_q=safe_float(last['ema20_q'])

            # RSI filter
            if not (min_rsi<=rsi_q<=max_rsi): continue

            # EMA filter — REVISED: support near-EMA tolerance
            if require_above_ema:
                if cl_q < ema_q: continue
            else:
                # Toleransi: harga boleh sampai X% di bawah EMA20
                if ema_q > 0 and (cl_q - ema_q) / ema_q * 100 < ema_tolerance: continue

            sc_val, sc_det = score_ticker(d, mode=mode)
            if sc_val < min_score: continue

            sig, _, sl_v, tp_v, rr_v = get_signal(d, sc_val, mode=mode)
            if "SELL" in sig or "WEAK" in sig: continue
            if signal_filter=="Strong BUY Only" and "STRONG" not in sig: continue
            if signal_filter=="Semua BUY" and "BUY" not in sig and "BREAKOUT" not in sig: continue

            vr, vlbl, vsurge_light, vsurge_strong = volume_analysis(d)
            if require_surge_strong and not vsurge_strong: continue
            if require_surge and not vsurge_light: continue
            if vr < min_vol_ratio: continue

            macd_df2=ta.macd(d['close'],fast=12,slow=26,signal=9)
            if macd_df2 is not None and not macd_df2.empty:
                mc=safe_float(macd_df2.iloc[-1,0]); ms2=safe_float(macd_df2.iloc[-1,1])
            else: mc=ms2=0
            if require_macd_bull and mc<=ms2: continue

            pats=detect_patterns(d)
            results.append({
                "Ticker":     t.replace(".JK",""),
                "Score":      sc_val,
                "Signal":     sig,
                "Price":      int(cl_q),
                "RSI":        round(rsi_q,1),
                "Vol":        vlbl,
                "MACD":       "✅" if mc>ms2 else "❌",
                "EMA20":      "✅" if cl_q>=ema_q else f"⚠️{((cl_q-ema_q)/ema_q*100):.1f}%",
                "SL":         int(sl_v),
                "TP":         int(tp_v),
                "R:R":        f"1:{rr_v}",
                "Pattern":    pats[0] if pats else "—",
                "Trend_s":    sc_det.get('Trend',0),
                "Mom_s":      sc_det.get('Momentum',0),
                "_cl":        cl_q,
                "_vr":        vr,
                "_vsurge_l":  vsurge_light,
                "_vsurge_s":  vsurge_strong,
            })
        except: errors+=1; continue

    prog.empty(); status.empty()

    if results:
        df_res=pd.DataFrame(results).sort_values("Score",ascending=False).head(top_n)
        df_res['Verdict'] = df_res.apply(lambda r: interpret_scanner_row(r, ihsg_change), axis=1)

        def color_score(val):
            if val>=70: return 'background-color:#004422;color:#00ff99'
            elif val>=55: return 'background-color:#332200;color:#ffcc00'
            else: return 'background-color:#2a0010;color:#ff8888'

        display_cols=["Ticker","Score","Signal","Price","RSI","Vol","MACD","EMA20","SL","TP","R:R","Pattern"]
        styled=df_res[display_cols].style.map(color_score,subset=['Score'])
        st.dataframe(styled,use_container_width=True,hide_index=True)
        st.success(f"✅ **{len(df_res)} kandidat** dari {len(tickers_to_scan)} discan | Errors: {errors}")

        st.markdown("### 📝 Interpretasi Tiap Saham")
        for _, row in df_res.iterrows():
            score_v = row['Score']
            sc_clr  = "#00ff99" if score_v>=70 else ("#44aaff" if "BREAKOUT" in row['Signal'] else ("#ffcc00" if score_v>=55 else "#ff4466"))
            st.markdown(f"""
            <div style='background:#0a1020;border:1px solid #1e3050;border-left:3px solid {sc_clr};
                        border-radius:8px;padding:12px 16px;margin:6px 0;display:flex;
                        align-items:flex-start;gap:14px;'>
                <div style='min-width:90px;text-align:center;'>
                    <div style='font-size:16px;font-weight:900;color:#00bbff'>{row['Ticker']}</div>
                    <div style='font-size:20px;font-weight:900;color:{sc_clr}'>{score_v}</div>
                    <div style='font-size:9px;color:#445'>/ 100</div>
                    <div style='font-size:10px;color:#667;margin-top:2px'>Rp {row['Price']:,}</div>
                </div>
                <div style='flex:1;color:#bbc;font-size:13px;line-height:1.7'>{row['Verdict']}</div>
                <div style='min-width:110px;text-align:right;font-size:11px;color:#556'>
                    RSI: {row['RSI']}<br>
                    Vol: {row['Vol']}<br>
                    MACD: {row['MACD']}<br>
                    <span style='color:#ff6666'>SL: {row['SL']:,}</span><br>
                    <span style='color:#66ff99'>TP: {row['TP']:,}</span><br>
                    <span style='color:#aaaaff'>{row['R:R']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("### 🏆 Top 3 Setup Terbaik — Analisis Lengkap")
        top3=df_res.head(3)
        for i,(_, row) in enumerate(top3.iterrows()):
            sc2 = ("score-high" if row['Score']>=65 else "score-mid")
            tg  = ("tag-sbuy"  if "STRONG" in row['Signal'] else "tag-buy")
            medal=["🥇","🥈","🥉"][i]
            sc_clr="#00ff99" if row['Score']>=70 else "#ffcc00"
            try:
                df_top = analyze_full(f"{row['Ticker']}.JK", period="90d", mode=mode)
                if df_top is not None:
                    sc_v2, det_v2 = score_ticker(df_top, mode=mode)
                    sig_v2, _, sl_v2, tp_v2, rr_v2 = get_signal(df_top, sc_v2, mode=mode)
                    pats_v2 = detect_patterns(df_top)
                    vr_v2, _, vsl_v2, vss_v2 = volume_analysis(df_top)
                    full_html, conf_lbl, conf_clr = interpret_analysis(
                        f"{row['Ticker']}.JK", sc_v2, det_v2, sig_v2,
                        df_top, sl_v2, tp_v2, rr_v2, pats_v2, vr_v2, vsl_v2, vss_v2, ihsg_change
                    )
                else:
                    full_html = "<p style='color:#556'>Interpretasi detail tidak tersedia.</p>"
                    conf_lbl, conf_clr = "—", "#666"
            except:
                full_html = "<p style='color:#556'>Interpretasi detail tidak tersedia.</p>"
                conf_lbl, conf_clr = "—", "#666"

            with st.expander(f"{medal} #{i+1} {row['Ticker']} — Score {row['Score']}/100 | {row['Signal']} | Rp {row['Price']:,}", expanded=(i==0)):
                col_a, col_b = st.columns([1, 2])
                with col_a:
                    st.markdown(f"""
                    <div class='metric-card'>
                        <div style='font-size:22px;font-weight:900;color:#00bbff'>{row['Ticker']}</div>
                        <div class='{sc2}'>{row['Score']}/100</div>
                        <div style='margin:8px 0'><span class='{tg}'>{row['Signal']}</span></div>
                        <hr style='border-color:#1e3050'>
                        <div style='font-size:12px;color:#778;text-align:left;line-height:1.9'>
                        💰 Harga: <b>Rp {row['Price']:,}</b><br>
                        📊 RSI: <b>{row['RSI']}</b><br>
                        📦 Volume: <b>{row['Vol']}</b><br>
                        📈 MACD: <b>{row['MACD']}</b><br>
                        📐 EMA20: <b>{row['EMA20']}</b><br>
                        🕯️ Pattern: <b>{row['Pattern']}</b><br>
                        <hr style='border-color:#1e3050;margin:6px 0'>
                        ❌ SL: <span style='color:#ff6666'>{row['SL']:,}</span><br>
                        ✅ TP: <span style='color:#66ff99'>{row['TP']:,}</span><br>
                        ⚖️ R:R: <span style='color:#aaaaff'>{row['R:R']}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                with col_b:
                    st.markdown(full_html, unsafe_allow_html=True)

        st.markdown("### 📊 Distribusi Score — Semua Kandidat")
        fig_dist=go.Figure()
        fig_dist.add_trace(go.Bar(
            x=df_res['Ticker'], y=df_res['Score'],
            marker_color=['#00ff99' if s>=70 else ('#44aaff' if "BREAKOUT" in df_res.loc[df_res['Ticker']==t,'Signal'].values[0] else ('#ffcc00' if s>=55 else '#ff4466'))
                          for s,t in zip(df_res['Score'],df_res['Ticker'])],
            text=df_res['Score'], textposition='outside'
        ))
        fig_dist.add_hline(y=70,line_dash="dot",line_color="#00ff99",annotation_text="Strong Buy Zone")
        fig_dist.add_hline(y=50,line_dash="dot",line_color="#4488ff",annotation_text="Buy Zone (Aggressive)")
        fig_dist.update_layout(height=300,template='plotly_dark',margin=dict(l=0,r=0,t=10,b=0),
                                yaxis=dict(range=[0,105]),showlegend=False)
        st.plotly_chart(fig_dist,use_container_width=True)

        st.divider()
        st.subheader("📋 Morning Review — Panduan Eksekusi")
        mktbias="🟢 BULLISH" if ihsg_change>0.3 else ("🔴 BEARISH" if ihsg_change<-0.3 else "🟡 SIDEWAYS")
        strong_picks=[r['Ticker'] for _,r in df_res.iterrows() if "STRONG" in r['Signal']]
        breakout_picks=[r['Ticker'] for _,r in df_res.iterrows() if "BREAKOUT" in r['Signal']]
        surge_picks=[r['Ticker'] for _,r in df_res.iterrows() if "🔥" in str(r.get('Vol',''))]

        st.markdown(f"""
        <div style='background:#0a1020;border:1px solid #1e3050;border-radius:12px;padding:20px;'>
        <b>🌐 IHSG:</b> {ihsg_df['close'].iloc[-1]:,.0f} <span style='color:{"#00ff99" if ihsg_change>0 else "#ff4466"}'>{ihsg_change:+.2f}%</span> — {mktbias}<br><br>
        <b>⚡ Strong Buy:</b> {', '.join(strong_picks) if strong_picks else '—'}<br>
        <b>🚀 Breakout Watch:</b> {', '.join(breakout_picks) if breakout_picks else '—'}<br>
        <b>🔥 Volume Surge:</b> {', '.join(surge_picks) if surge_picks else '—'}<br><br>
        <b>📌 Panduan Eksekusi ({("Mode Aggressive 🚀" if mode=="aggressive" else "Mode Conservative 🛡️")}):</b>
        <ol style='color:#99aacc;margin-top:8px'>
        <li>Prioritaskan <b>Score ≥ 70 + Volume Surge 🔥</b> + RSI 55–72 → <b>Setup Premium Aggressive</b>.</li>
        <li><b>Breakout Watch 🚀</b>: Entry saat candle konfirmasi menutup di atas EMA20 dengan volume naik. Jangan FOMO masuk sebelum konfirmasi.</li>
        <li>Jika IHSG {mktbias}, {"fokus hanya setup terkuat dan sizing kecil" if "BEARISH" in mktbias else "bisa lebih agresif tapi tetap pakai SL ketat"}.</li>
        <li>RSI 55–72 = <b>momentum prime zone</b> untuk daily trade. RSI 40–55 = akumulasi/rebound setup.</li>
        <li>R:R wajib ≥ 1:2. Kalau R:R < 1:1.5, skip dan cari entry lebih baik.</li>
        <li>Max 20–25% modal per saham. Untuk setup Breakout Watch, sizing 50% dulu sampai konfirmasi.</li>
        </ol>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.warning(f"Tidak ada saham yang memenuhi semua kriteria. Coba turunkan min score atau longgarkan filter.")
        st.info(f"Total discan: {len(tickers_to_scan)} | Errors: {errors}")
