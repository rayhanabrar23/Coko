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

# ── CONFIG ───────────────────────────────────────────────────────────────────
st.set_page_config(page_title="IDX Terminal v5", layout="wide", initial_sidebar_state="collapsed")

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
.trade-card {
    background: #0a1020; border: 1px solid #1e3050;
    border-radius: 12px; padding: 16px; margin: 8px 0;
}
div[data-testid="stDataFrame"] { background: #0a0d15 !important; }
</style>
""", unsafe_allow_html=True)

# ── UNIVERSE DATABASE ────────────────────────────────────────────────────────

IDX30 = [
    "AADI","ADRO","AMMN","ANTM","AMRT","ASII","BBCA","BBNI","BBRI","BBTN",
    "BMRI","BRIS","BUKA","CPIN","EXCL","GOTO","ICBP","INCO","INDF","ISAT",
    "ITMG","KLBF","MDKA","MEDC","MIKA","PGEO","PTBA","TLKM","TOWR","UNTR"
]
LQ45 = list(dict.fromkeys(IDX30 + [
    "ACES","AKRA","ARTO","BELI","BNGA","BSDE","CTRA","EMTK","GGRM","HMSP",
    "INTP","JSMR","MAPI","MYOR","PGAS","PNBN","PWON","SMGR","TBIG","TINS",
    "TKIM","UNVR","HEAL","BYAN","CMRY","DCII","DSSA","NCKL","INKP","SILO"
]))[:45]
IDX80_EXTRA = [
    "AVIA","BDMN","BKSL","BUMI","GEMS","GIAA","JPFA","MTEL","NISP","NCKL",
    "PGEO","SMRA","SSIA","TAPG","TCPI","TBIG","SIDO","MDIY","BSIM","BIPI",
    "JSMR","MAPI","PNBN","INKP","MYOR","CBDK","GGRM","FILM","CUAN","ARCO"
]
IDX80    = list(dict.fromkeys(LQ45 + IDX80_EXTRA))[:80]
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
    "ENRG","BIPI","BSIM","MDIY","BBTN","MEGA","NSSS","MSIN"
]

MANUAL_SECTORS = {
    "FINANCE":     ["BBCA","BBRI","BMRI","BBNI","BRIS","ARTO","BNGA","PNBN","MEGA","BDMN","NISP","BTPN","BBHI","BSIM","BBTN","BNLI"],
    "ENERGY":      ["ADRO","ITMG","PTBA","MEDC","AKRA","PGAS","ENRG","GEMS","AADI","BYAN","DSSA","TCPI","INDY","BIPI"],
    "HEALTHCARE":  ["MIKA","HEAL","SILO","KLBF","SIDO","PYFA","SOHO"],
    "BASIC MAT":   ["ANTM","TINS","MDKA","SMGR","INTP","TPIA","INCO","NCKL","AMMN","ARCI","BRMS","MBMA"],
    "CONSUMER":    ["ACES","MAPI","AMRT","ICBP","INDF","GGRM","HMSP","UNVR","MYOR","CPIN","JPFA","CMRY","AVIA","MDIY"],
    "INFRA":       ["TLKM","ISAT","EXCL","TOWR","TBIG","JSMR","MTEL","GIAA","PGAS","PGEO"],
    "PROPERTY":    ["BSDE","PWON","CTRA","SMRA","SSIA","CBDK","BKSL","PANI","MKPI"],
    "TECH/DIGITAL":["GOTO","BUKA","EMTK","DCII","BELI","BBHI","ARTO","VKTR"],
}
INDEX_UNIVERSE = {
    "IDX30 (Blue Chip, ~30 saham)":          IDX30,
    "LQ45 (Liquid 45, ~45 saham)":           LQ45,
    "IDX80 (Broad Market, ~80 saham)":       IDX80,
    "IDX High Dividend 20":                  IDX_HIDIV20,
    "IDX Growth30":                           IDX_GROWTH30,
    "IDX SMC Liquid (Small-Mid Cap)":        IDX_SMC,
    "ALL IDX Combined (~180 unik)":          list(dict.fromkeys(IDX80+IDX_GROWTH30+IDX_SMC+IDX_HIDIV20)),
}
SECTOR_PROXY = {
    "FINANCE":"BBCA","ENERGY":"ADRO","HEALTHCARE":"KLBF","BASIC MAT":"ANTM",
    "CONSUMER":"ICBP","INFRA":"TLKM","PROPERTY":"BSDE","TECH":"GOTO",
}

def add_jk(tickers):
    return [t if t.endswith(".JK") else f"{t}.JK" for t in tickers]

# ── HELPERS ──────────────────────────────────────────────────────────────────

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

def fmt_price(val):
    """Format harga tanpa desimal tidak perlu."""
    v = safe_float(val)
    if v == 0: return "—"
    if v >= 1000: return f"{v:,.0f}"
    return f"{v:.0f}"

def fmt_pct(val, decimals=1):
    v = safe_float(val)
    return f"{v:+.{decimals}f}%"

# ── ANALYSIS ENGINE ───────────────────────────────────────────────────────────

def detect_patterns(df):
    if len(df) < 3: return ["—"]
    patterns = []
    o,h,l,c = df['open'].values, df['high'].values, df['low'].values, df['close'].values
    i = -1
    body = abs(c[i]-o[i]); rng = h[i]-l[i]
    uw = h[i]-max(c[i],o[i]); lw = min(c[i],o[i])-l[i]
    if rng > 0:
        if lw >= 2*body and uw <= 0.3*body:   patterns.append("🔨 Hammer (Bullish)")
        if uw >= 2*body and lw <= 0.3*body:   patterns.append("⬆️ Inv. Hammer")
        if body/rng < 0.1:                    patterns.append("✳️ Doji (Reversal)")
        if body/rng > 0.85:
            patterns.append("💪 Bullish Marubozu" if c[i]>o[i] else "👇 Bearish Marubozu")
    pb = abs(c[-2]-o[-2])
    if c[-2]<o[-2] and c[i]>o[i] and body>pb: patterns.append("🟢 Bullish Engulfing")
    if c[-2]>o[-2] and c[i]<o[i] and body>pb: patterns.append("🔴 Bearish Engulfing")
    if len(df)>=3:
        if c[-3]<o[-3] and abs(c[-2]-o[-2])<0.003*c[-2] and c[i]>o[i]: patterns.append("🌅 Morning Star")
        if c[-3]>o[-3] and abs(c[-2]-o[-2])<0.003*c[-2] and c[i]<o[i]: patterns.append("🌇 Evening Star")
    return patterns or ["— No Pattern"]

def volume_analysis(df):
    if 'volume' not in df.columns or len(df)<20: return 0,"N/A",False,False
    avg = df['volume'].rolling(20).mean().iloc[-1]
    last = df['volume'].iloc[-1]
    ratio = safe_float(last/avg) if avg>0 else 0
    is_surge = ratio >= 1.5
    label = f"{ratio:.1f}x" + (" 🔥" if is_surge else "")
    return ratio, label, is_surge, is_surge

def score_ticker(df, mode="aggressive"):
    if df.empty or len(df) < 52: return 0, {}
    df = df.copy()
    df['ema20'] = ta.ema(df['close'], length=20)
    df['ema50'] = ta.ema(df['close'], length=50)
    df['rsi']   = ta.rsi(df['close'], length=14)
    df['atr']   = ta.atr(df['high'], df['low'], df['close'], length=14)
    macd_df     = ta.macd(df['close'], fast=12, slow=26, signal=9)
    if macd_df is not None and not macd_df.empty:
        df['macd']=macd_df.iloc[:,0]; df['sig']=macd_df.iloc[:,1]; df['hist']=macd_df.iloc[:,2]
    else: df['macd']=df['sig']=df['hist']=0
    bb = ta.bbands(df['close'], length=20, std=2)
    if bb is not None and not bb.empty:
        df['bb_u']=bb.iloc[:,0]; df['bb_m']=bb.iloc[:,1]; df['bb_l']=bb.iloc[:,2]
    else: df['bb_u']=df['bb_m']=df['bb_l']=df['close']

    l=df.iloc[-1]
    cl=safe_float(l['close']); e20=safe_float(l['ema20']); e50=safe_float(l['ema50'])
    rsi=safe_float(l['rsi']); macd=safe_float(l['macd']); sig=safe_float(l['sig'])
    hist=safe_float(l['hist']); bb_l=safe_float(l['bb_l']); bb_m=safe_float(l['bb_m'])

    ts=0
    if cl>e20: ts+=12
    if cl>e50: ts+=8
    gap=(cl-e20)/e20*100 if e20 else 0
    if -1<=gap<=3: ts+=5

    ms=0
    if 40<=rsi<=60: ms+=15
    elif 30<=rsi<40 or 60<rsi<=65: ms+=8
    if macd>sig: ms+=7
    if hist>0 and len(df)>1 and safe_float(df['hist'].iloc[-2])>=0 and hist>safe_float(df['hist'].iloc[-2]): ms+=3

    vr,_,is_surge,_ = volume_analysis(df)
    vs=min(int(vr*8),20)

    bs=0
    if cl<=bb_l*1.01: bs=15
    elif cl<=bb_m: bs=7

    pats=detect_patterns(df); ps=0
    for p in pats:
        if any(k in p for k in ['Engulfing','Morning Star','Hammer','Marubozu']): ps=15; break
        elif 'Doji' in p or 'Inv.' in p: ps=max(ps,5)

    score=min(ts+ms+vs+bs+ps,100)
    detail={'Trend':ts,'Momentum':ms,'Volume':vs,'BB Zone':bs,'Pattern':ps}
    return score, detail

def get_signal(df, score, mode="aggressive"):
    l=df.iloc[-1]
    cl=safe_float(l['close']); e20=safe_float(l.get('ema20', l['close']))
    e50=safe_float(l.get('ema50', l['close'])); rsi=safe_float(l.get('rsi', 50))
    macd=safe_float(l.get('macd', 0)); sig=safe_float(l.get('sig', 0))
    atr=safe_float(l.get('atr', cl*0.02))

    sl=cl-(1.5*atr); tp=cl+(2.5*atr)
    rr=round((tp-cl)/(cl-sl),1) if (cl-sl)>0 else 0

    if score>=70 and cl>e20 and rsi<65 and macd>sig: return "⚡ STRONG BUY","#00ff99",sl,tp,rr
    elif score>=55 and cl>e20 and rsi<70:            return "✅ BUY","#44dd88",sl,tp,rr
    elif rsi>75 or (cl<e50 and cl<e20 and score<35): return "❌ SELL/AVOID","#ff4466",sl,tp,rr
    elif score<40:                                   return "⚠️ WEAK/SKIP","#ff8844",sl,tp,rr
    else:                                            return "🔄 HOLD/WATCH","#ffcc00",sl,tp,rr

@st.cache_data(ttl=3600, show_spinner=False)
def analyze_full_cached(ticker, period="6mo"):
    return _analyze_full_core(ticker, period)

def analyze_full(ticker, period="1y"):
    return _analyze_full_core(ticker, period)

def _analyze_full_core(ticker, period="6mo"):
    df=yf.download(ticker, period=period, progress=False); df=clean_df(df)
    if df.empty or len(df)<52: return None
    df['ema20']=ta.ema(df['close'],length=20); df['ema50']=ta.ema(df['close'],length=50)
    df['rsi']=ta.rsi(df['close'],length=14); df['atr']=ta.atr(df['high'],df['low'],df['close'],length=14)
    macd_df=ta.macd(df['close'],fast=12,slow=26,signal=9)
    if macd_df is not None and not macd_df.empty:
        df['macd']=macd_df.iloc[:,0]; df['sig']=macd_df.iloc[:,1]; df['hist']=macd_df.iloc[:,2]
    else: df['macd']=df['sig']=df['hist']=0
    bb=ta.bbands(df['close'],length=20,std=2)
    if bb is not None and not bb.empty:
        df['bb_u']=bb.iloc[:,0]; df['bb_m']=bb.iloc[:,1]; df['bb_l']=bb.iloc[:,2]
    else: df['bb_u']=df['bb_m']=df['bb_l']=df['close']
    df['vol_ma20']=df['volume'].rolling(20).mean()
    return df

def calc_sr(df):
    if len(df)<20: return [],[]
    hh=df['high'].rolling(5,center=True).max()
    ll=df['low'].rolling(5,center=True).min()
    res=sorted(df[df['high']==hh]['high'].dropna().unique(),reverse=True)[:3]
    sup=sorted(df[df['low']==ll]['low'].dropna().unique())[:3]
    return list(res), list(sup)

def _scan_one(args):
    (ticker, min_score, signal_filter, require_above_ema,
     min_vol_ratio, require_surge, require_macd_bull,
     min_rsi, max_rsi) = args
    ticker_name = ticker.replace(".JK","")
    try:
        d = analyze_full_cached(ticker, period="6mo")
        if d is None or d.empty: return None, ticker_name
        last = d.iloc[-1]
        rsi_q  = safe_float(last.get('rsi', 50))
        cl_q   = safe_float(last.get('close', 0))
        ema_q  = safe_float(last.get('ema20', cl_q))
        macd_v = safe_float(last.get('macd', 0))
        sig_v2 = safe_float(last.get('sig', 0))
        if not (min_rsi <= rsi_q <= max_rsi): return None, ticker_name
        gap_pct = (cl_q - ema_q) / ema_q * 100 if ema_q > 0 else 0
        if require_above_ema and cl_q < ema_q: return None, ticker_name
        elif not require_above_ema and gap_pct < -1.5: return None, ticker_name
        sc_val, sc_det = score_ticker(d)
        if sc_val < min_score: return None, ticker_name
        sig, _, sl_v, tp_v, rr_v = get_signal(d, sc_val)
        if "SELL" in sig or "WEAK" in sig: return None, ticker_name
        if signal_filter == "Strong BUY Only" and "STRONG" not in sig: return None, ticker_name
        if signal_filter == "Semua BUY" and "BUY" not in sig: return None, ticker_name
        vr, vlbl, vsurge_light, vsurge_strong = volume_analysis(d)
        if require_surge and not vsurge_light: return None, ticker_name
        if vr < min_vol_ratio: return None, ticker_name
        if require_macd_bull and macd_v <= sig_v2: return None, ticker_name
        pats = detect_patterns(d)
        result = {
            "Ticker":   ticker_name,
            "Score":    sc_val,
            "Signal":   sig,
            "Price":    round(cl_q, 0),
            "RSI":      round(rsi_q, 1),
            "Vol":      vlbl,
            "MACD":     "✅" if macd_v > sig_v2 else "❌",
            "EMA20":    "✅" if cl_q >= ema_q else f"⚠️{gap_pct:.1f}%",
            "SL":       round(sl_v, 0),
            "TP":       round(tp_v, 0),
            "R:R":      f"1:{rr_v}",
            "Pattern":  pats[0] if pats else "—",
        }
        return result, ticker_name
    except: return None, ticker_name

def run_parallel_scan(tickers, scan_params, max_workers=10, progress_placeholder=None, status_placeholder=None):
    args_list = [(t, *scan_params) for t in tickers]
    results = []; completed = 0; total = len(tickers)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_scan_one, args): args[0] for args in args_list}
        for future in concurrent.futures.as_completed(futures):
            completed += 1
            try:
                result, _ = future.result()
                if result: results.append(result)
            except: pass
            if progress_placeholder: progress_placeholder.progress(completed/total)
            if status_placeholder:
                status_placeholder.markdown(
                    f"⚡ Scanning: **{completed}/{total}** | Kandidat: **{len(results)}** | {completed/total*100:.0f}%")
    return results

def interpret_analysis(ticker, score, detail, signal, df, sl, tp, rr, pats, vr, vsurge_light, vsurge_strong, ihsg_change=0.0):
    l = df.iloc[-1]
    cl   = safe_float(l['close']); rsi  = safe_float(l.get('rsi',   50))
    e20  = safe_float(l.get('ema20', cl)); e50  = safe_float(l.get('ema50', cl))
    macd = safe_float(l.get('macd', 0));  sig  = safe_float(l.get('sig',  0))
    atr  = safe_float(l.get('atr', cl*0.02)); name = ticker.replace(".JK","")

    pros=[]; cons=[]; cautions=[]
    gap_pct=(cl-e20)/e20*100 if e20 else 0

    if cl>e20 and cl>e50:
        pros.append(f"Harga di atas EMA20 ({fmt_price(e20)}) dan EMA50 ({fmt_price(e50)}) — tren naik kuat.")
    elif cl>e20:
        cautions.append(f"Di atas EMA20 (+{gap_pct:.1f}%) tapi masih di bawah EMA50 — tren menengah belum recovery.")
    elif -1.5<=gap_pct<0:
        cautions.append(f"Harga sedikit di bawah EMA20 ({gap_pct:.1f}%) — dalam toleransi breakout.")
    else:
        cons.append(f"Harga di bawah EMA20 & EMA50 — tren masih negatif.")

    if -0.5<=gap_pct<=3:
        pros.append(f"Posisi {gap_pct:+.1f}% dari EMA20 — zona entry ideal sebelum breakout.")
    elif gap_pct>6:
        cautions.append(f"Harga {gap_pct:.1f}% di atas EMA20 — risiko koreksi meningkat.")

    if 55<=rsi<=72:
        pros.append(f"RSI {rsi:.0f} di zona momentum prime (55–72) — sweet spot breakout.")
    elif 40<=rsi<55:
        pros.append(f"RSI {rsi:.0f} di zona akumulasi — saham istirahat, siap naik lagi.")
    elif rsi<35:
        pros.append(f"RSI {rsi:.0f} oversold ekstrem — peluang rebound teknikal tinggi.")
    elif 72<rsi<=78:
        cautions.append(f"RSI {rsi:.0f} mulai panas. Kurangi sizing, perketat SL.")
    elif rsi>78:
        cons.append(f"RSI {rsi:.0f} overbought berlebihan — hindari entry baru.")

    if macd>sig:
        hist_val = safe_float(l.get('hist', 0))
        prev_hist = safe_float(df['hist'].iloc[-2] if 'hist' in df.columns and len(df)>1 else 0)
        if hist_val>prev_hist:
            pros.append("MACD golden cross dan histogram membesar — momentum beli akseleratif.")
        else:
            pros.append("MACD di atas signal line — tekanan beli masih dominan.")
    else:
        cons.append("MACD masih di bawah signal. Tunggu golden cross untuk konfirmasi entry.")

    if vsurge_strong:
        pros.append(f"Volume {vr:.1f}x rata-rata 20 hari 🔥🔥 — konfirmasi institusional.")
    elif vsurge_light:
        pros.append(f"Volume {vr:.1f}x rata-rata 🔥 — minat beli mulai masuk.")
    elif vr>=1.0:
        cautions.append(f"Volume di rata-rata ({vr:.1f}x) — belum dikonfirmasi volume besar.")
    else:
        cautions.append(f"Volume sepi ({vr:.1f}x) — rentan reversal tiba-tiba.")

    if 'bb_l' in df.columns:
        bb_l=safe_float(l['bb_l']); bb_m=safe_float(l['bb_m']); bb_u=safe_float(l['bb_u'])
        if cl<=bb_l*1.01:
            pros.append(f"Harga menyentuh lower BB ({fmt_price(bb_l)}) — sering berbalik ke midband ({fmt_price(bb_m)}).")
        elif cl<=bb_m:
            pros.append(f"Antara lower BB dan midband — zona akumulasi bagus untuk entry.")
        elif cl>=bb_u*0.97:
            cons.append(f"Mendekati upper BB ({fmt_price(bb_u)}) — set SL ketat.")

    pat_str=pats[0] if pats else "—"
    if any(k in pat_str for k in ['Engulfing','Morning Star','Hammer','Marubozu']):
        pros.append("Pola candlestick bullish terdeteksi — konfirmasi visual pembalikan/lanjutan naik.")
    elif any(k in pat_str for k in ['Bearish','Evening Star']):
        cons.append("Pola bearish terdeteksi — waspada tekanan jual meningkat.")
    elif 'Doji' in pat_str:
        cautions.append("Pola Doji — pasar ragu-ragu. Tunggu candle konfirmasi.")

    if ihsg_change>0.5:
        pros.append(f"IHSG momentum positif ({ihsg_change:+.1f}%) — tailwind market.")
    elif ihsg_change<-0.5:
        cautions.append(f"IHSG melemah ({ihsg_change:+.1f}%) — setup bagus bisa ikut tertekan.")

    if rr>=2.0:    pros.append(f"Risk:Reward 1:{rr} — secara matematis menguntungkan.")
    elif rr>=1.5:  cautions.append(f"R:R 1:{rr} — di batas minimum, masih acceptable.")
    else:          cautions.append(f"R:R hanya 1:{rr} — terlalu kecil, cari entry lebih baik.")

    score_cons=len(cons)
    if "STRONG BUY" in signal or ("BUY" in signal and score_cons==0 and len(pros)>=4):
        verdict_title=f"✅ LAYAK DIBELI — Setup {name} Tergolong Kuat"
        verdict_color="#00ff99"; confidence="TINGGI"
        verdict_open=f"Skor {score}/100 — <b>{name}</b> di Rp {fmt_price(cl)} menunjukkan setup beli kuat."
    elif "BUY" in signal and score_cons<=1:
        verdict_title=f"🟡 BOLEH DIPERTIMBANGKAN — {name} Cukup Layak"
        verdict_color="#ffcc00"; confidence="SEDANG"
        verdict_open=f"Skor {score}/100 — <b>{name}</b> di Rp {fmt_price(cl)} punya setup layak dengan beberapa catatan."
    elif "SELL" in signal or "WEAK" in signal or score_cons>=3:
        verdict_title=f"❌ TIDAK DISARANKAN — {name} Belum Siap"
        verdict_color="#ff4466"; confidence="RENDAH"
        verdict_open=f"Skor {score}/100 — <b>{name}</b> di Rp {fmt_price(cl)} belum memiliki setup aman."
    else:
        verdict_title=f"⏳ TUNGGU KONFIRMASI — {name} Transisi"
        verdict_color="#aaaaff"; confidence="MENUNGGU"
        verdict_open=f"Skor {score}/100 — {name} sedang transisi, campuran sinyal positif dan negatif."

    if "BUY" in signal and "WEAK" not in signal:
        closing=(f"<b>Kesimpulan:</b> Entry area Rp {fmt_price(cl)}–{fmt_price(cl*1.005)}, "
                 f"SL Rp {fmt_price(sl)} (−{((cl-sl)/cl*100):.1f}%), "
                 f"TP Rp {fmt_price(tp)} (+{((tp-cl)/cl*100):.1f}%). Hold 1–3 hari trading.")
    else:
        closing=(f"<b>Alternatif:</b> Masukkan {name} ke watchlist. "
                 f"Tunggu RSI di 40–65 dan MACD golden cross sebelum entry.")

    pros_html="".join([f"<li style='margin-bottom:5px;color:#b0ffcc'>✅ {p}</li>" for p in pros])
    cons_html="".join([f"<li style='margin-bottom:5px;color:#ffaaaa'>❌ {c}</li>" for c in cons])
    caut_html="".join([f"<li style='margin-bottom:5px;color:#ffeebb'>⚠️ {w}</li>" for w in cautions])
    support_section=""
    if pros_html: support_section+=f"<p style='color:#668;font-size:12px;margin:8px 0 4px'>FAKTOR PENDUKUNG:</p><ul style='margin:0;padding-left:20px'>{pros_html}</ul>"
    if cons_html: support_section+=f"<p style='color:#668;font-size:12px;margin:10px 0 4px'>FAKTOR PENGHAMBAT:</p><ul style='margin:0;padding-left:20px'>{cons_html}</ul>"
    if caut_html: support_section+=f"<p style='color:#668;font-size:12px;margin:10px 0 4px'>CATATAN KEHATI-HATIAN:</p><ul style='margin:0;padding-left:20px'>{caut_html}</ul>"

    html=f"""
    <div style='background:linear-gradient(135deg,#080e1a,#0c1525);border:2px solid {verdict_color}44;
                border-left:4px solid {verdict_color};border-radius:12px;padding:20px;margin:16px 0;'>
        <div style='font-size:17px;font-weight:bold;color:{verdict_color};margin-bottom:10px'>
            {verdict_title}
            &nbsp;<span style='font-size:11px;background:{verdict_color}22;color:{verdict_color};
                          padding:2px 10px;border-radius:10px;border:1px solid {verdict_color}44'>
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
            ⚠️ Analisis teknikal saja — bukan saran investasi resmi.
        </p>
    </div>
    """
    return html, confidence, verdict_color

# ── TRACKER STORAGE ───────────────────────────────────────────────────────────

TRACKER_FILE = Path("idx_trade_log.json")
TZ_JKT = pytz.timezone("Asia/Jakarta")

def load_trade_log() -> list:
    if TRACKER_FILE.exists():
        with open(TRACKER_FILE,"r") as f: return json.load(f)
    return []

def save_trade_log(logs: list):
    with open(TRACKER_FILE,"w") as f: json.dump(logs, f, indent=2, default=str)

def save_scan_results_to_log(df_results: pd.DataFrame, scan_date_str: str):
    """Simpan top 10 hasil scan ke tracker, maksimal 10 per hari."""
    logs = load_trade_log()
    existing_keys = {(e["date"], e["ticker"]) for e in logs}
    new_entries = 0
    for _, row in df_results.head(10).iterrows():
        key = (scan_date_str, row["Ticker"])
        if key in existing_keys: continue
        logs.append({
            "id":       f"{scan_date_str}_{row['Ticker']}",
            "date":     scan_date_str,
            "ticker":   row["Ticker"],
            "signal":   row["Signal"],
            "score":    int(row["Score"]),
            "entry":    float(row["Price"]),
            "sl":       float(row["SL"]),
            "tp":       float(row["TP"]),
            "rr":       str(row["R:R"]),
            "pattern":  row.get("Pattern","—"),
            "note":     "",
        })
        new_entries += 1
    save_trade_log(logs)
    return new_entries

# ── TRADE STATUS ENGINE ───────────────────────────────────────────────────────

@st.cache_data(ttl=900, show_spinner=False)
def check_trade_status(ticker: str, entry: float, sl: float, tp: float, scan_date_str: str) -> dict:
    """
    Fetch OHLC dari tanggal scan sampai hari ini.
    Cek candle per candle apakah SL/TP kena.
    Return dict dengan status, harga saat ini, % change, rekomendasi, alasan.
    """
    ticker_jk = ticker + ".JK"
    try:
        scan_dt  = date.fromisoformat(scan_date_str)
        today    = datetime.now(TZ_JKT).date()
        start_dt = (scan_dt - timedelta(days=1)).isoformat()

        hist = clean_df(yf.download(ticker_jk, start=start_dt, progress=False))
        if hist.empty:
            return _no_data_result(entry, sl, tp)

        hist_from = hist[hist.index.date >= scan_dt]
        if hist_from.empty:
            return _no_data_result(entry, sl, tp)

        # Cek candle per candle
        hit_tp = hit_sl = False
        hit_price = hit_date = None
        for dt_idx, candle in hist_from.iterrows():
            hi = safe_float(candle['high']); lo = safe_float(candle['low'])
            if hi >= tp and not hit_tp and not hit_sl:
                hit_tp = True; hit_price = tp; hit_date = str(dt_idx.date()); break
            if lo <= sl and not hit_tp and not hit_sl:
                hit_sl = True; hit_price = sl; hit_date = str(dt_idx.date()); break

        # Harga penutupan terakhir
        last_row   = hist_from.iloc[-1]
        current    = safe_float(last_row['close'])
        curr_hi    = safe_float(last_row['high'])
        curr_lo    = safe_float(last_row['low'])
        last_date  = str(hist_from.index[-1].date())
        pct_change = (current - entry) / entry * 100 if entry > 0 else 0
        pct_to_tp  = (current - entry) / (tp - entry) * 100 if (tp - entry) > 0 else 0
        pct_to_sl  = (entry - current) / (entry - sl) * 100 if (entry - sl) > 0 else 0

        if hit_tp:
            pct_tp = (tp - entry) / entry * 100
            return {
                "status":    "TP HIT ✅",
                "current":   tp,
                "pct":       pct_tp,
                "last_date": hit_date,
                "color":     "#00ff99",
                "emoji":     "✅",
                "rec_action":"PROFIT TEREALISASI",
                "rec_color": "#00ff99",
                "reason":    (f"Target profit tercapai pada {hit_date}. "
                              f"High candle menyentuh TP {fmt_price(tp)} — gain {pct_tp:.1f}%."),
                "pct_to_tp": 100, "pct_to_sl": 0,
                "curr_hi": curr_hi, "curr_lo": curr_lo,
            }
        if hit_sl:
            pct_sl = (sl - entry) / entry * 100
            return {
                "status":    "SL HIT ❌",
                "current":   sl,
                "pct":       pct_sl,
                "last_date": hit_date,
                "color":     "#ff4466",
                "emoji":     "❌",
                "rec_action":"STOP LOSS AKTIF",
                "rec_color": "#ff4466",
                "reason":    (f"Stop loss terkena pada {hit_date}. "
                              f"Low candle menyentuh SL {fmt_price(sl)} — loss {abs(pct_sl):.1f}%."),
                "pct_to_tp": 0, "pct_to_sl": 100,
                "curr_hi": curr_hi, "curr_lo": curr_lo,
            }

        # Posisi masih open — beri rekomendasi berdasarkan kondisi
        rec_action, rec_color, reason = _generate_recommendation(
            entry, sl, tp, current, pct_change, pct_to_tp, pct_to_sl,
            curr_hi, curr_lo, scan_date_str, today
        )
        status_label = _status_label(pct_change, pct_to_tp, pct_to_sl)
        status_color = ("#00ff99" if pct_change>1 else
                        ("#44dd88" if pct_change>0 else
                         ("#ff8844" if pct_to_sl>50 else "#ffcc00")))

        return {
            "status":    status_label,
            "current":   current,
            "pct":       pct_change,
            "last_date": last_date,
            "color":     status_color,
            "emoji":     "📈" if pct_change>=0 else "📉",
            "rec_action": rec_action,
            "rec_color":  rec_color,
            "reason":    reason,
            "pct_to_tp": pct_to_tp,
            "pct_to_sl": pct_to_sl,
            "curr_hi": curr_hi, "curr_lo": curr_lo,
        }
    except Exception as e:
        return _no_data_result(entry, sl, tp, str(e))

def _no_data_result(entry, sl, tp, msg="Data tidak tersedia"):
    return {
        "status":"NO DATA","current":entry,"pct":0,"last_date":"—",
        "color":"#445566","emoji":"❓","rec_action":"CARI DATA MANUAL",
        "rec_color":"#445566","reason":msg,"pct_to_tp":0,"pct_to_sl":0,
        "curr_hi":entry,"curr_lo":entry,
    }

def _status_label(pct, pct_to_tp, pct_to_sl):
    if pct >= 0:
        if pct_to_tp >= 80: return f"HAMPIR TP ({pct:+.1f}%) 🎯"
        if pct_to_tp >= 50: return f"PROFIT BAGUS ({pct:+.1f}%) 💰"
        return f"UNTUNG {pct:+.1f}% ✊"
    else:
        if pct_to_sl >= 80: return f"HAMPIR SL ({pct:.1f}%) ⚠️"
        if pct_to_sl >= 50: return f"MELEMAH ({pct:.1f}%) 😟"
        return f"TURUN {pct:.1f}% 👀"

def _generate_recommendation(entry, sl, tp, current, pct, pct_to_tp, pct_to_sl,
                              curr_hi, curr_lo, scan_date_str, today):
    days_held = (today - date.fromisoformat(scan_date_str)).days
    days_note = f" (sudah {days_held} hari)" if days_held > 0 else " (hari pertama)"

    if pct >= 0:
        if pct_to_tp >= 80:
            return ("AMBIL TP SEKARANG", "#00ff99",
                    f"Harga sudah {pct_to_tp:.0f}% dari jarak entry→TP{days_note}. "
                    f"Pertimbangkan ambil profit penuh atau minimal partial 50% dan naikkan SL ke entry (breakeven). "
                    f"Jangan biarkan profit besar berubah jadi loss.")
        elif pct_to_tp >= 50:
            return ("PARTIAL TP + NAIKKAN SL", "#44dd88",
                    f"Profit {pct:.1f}%, sudah {pct_to_tp:.0f}% menuju target{days_note}. "
                    f"Disarankan: ambil profit 30–50%, geser SL ke harga entry (breakeven) untuk lock profit. "
                    f"Biarkan sisanya berjalan menuju TP {fmt_price(tp)}.")
        elif days_held >= 3 and pct > 0:
            return ("EVALUASI EXIT", "#ffcc00",
                    f"Sudah {days_held} hari, posisi profit {pct:.1f}% tapi masih jauh dari TP. "
                    f"Jika tidak ada momentum baru, pertimbangkan exit di harga saat ini dan alihkan ke setup lebih segar.")
        else:
            return ("HOLD — SESUAI RENCANA", "#ffcc00",
                    f"Posisi menguntungkan {pct:.1f}%{days_note}. Hold dengan SL di {fmt_price(sl)}. "
                    f"Target TP {fmt_price(tp)} ({((tp-current)/current*100):.1f}% lagi). "
                    f"Jangan pindahkan SL ke bawah entry.")
    else:
        if pct_to_sl >= 80:
            return ("CUT LOSS SEKARANG", "#ff4466",
                    f"Harga sudah {pct_to_sl:.0f}% mendekati SL{days_note}. "
                    f"Disarankan CUT LOSS sekarang di {fmt_price(current)} meskipun belum menyentuh SL {fmt_price(sl)}. "
                    f"Mencegah kerugian lebih besar lebih penting dari berharap reversal.")
        elif pct_to_sl >= 50:
            return ("WASPADA — SIAP CUT", "#ff8844",
                    f"Turun {abs(pct):.1f}%, sudah {pct_to_sl:.0f}% menuju SL{days_note}. "
                    f"Monitor ketat candle berikutnya. Jika candle bearish konfirmasi atau volume turun besar, "
                    f"eksekusi cut loss di {fmt_price(current)} tanpa tunggu SL {fmt_price(sl)} kena.")
        elif days_held >= 3 and pct < -1:
            return ("EVALUASI ULANG", "#ff8844",
                    f"Sudah {days_held} hari, posisi masih minus {abs(pct):.1f}%. "
                    f"Pertimbangkan cut loss jika tidak ada sinyal recovery (cek MACD, RSI, dan volume). "
                    f"Modal yang dilepas bisa diputar ke setup lebih bagus.")
        else:
            return ("HOLD — DALAM TOLERANSI", "#ffcc00",
                    f"Turun {abs(pct):.1f}%{days_note}, masih jauh dari SL {fmt_price(sl)} "
                    f"({(100-pct_to_sl):.0f}% margin tersisa). "
                    f"Hold sesuai rencana. SL adalah batas terakhir — jangan dipindah lebih rendah.")

# ── HEADER ────────────────────────────────────────────────────────────────────

st.markdown("""
<h1 style='text-align:center;color:#00bbff;letter-spacing:3px;font-family:monospace;'>
⚡ IDX TERMINAL v5 — SMART SCANNER
</h1>
<p style='text-align:center;color:#445566;font-family:monospace;'>
Multi-Factor Daily Trade Analyzer · IDX30 / LQ45 / IDX80 / Growth30 · Top 10 Rekomendasi Harian · Trade Tracker
</p>
""", unsafe_allow_html=True)
st.divider()

# ── MARKET PULSE ──────────────────────────────────────────────────────────────
col_ihsg, col_sector = st.columns([1,1])
ihsg_df = pd.DataFrame(); ihsg_change = 0.0

with col_ihsg:
    st.subheader("📈 IHSG Market Pulse")
    raw = yf.download("^JKSE", period="1y", progress=False); ihsg_df = clean_df(raw)
    if not ihsg_df.empty:
        ihsg_change = ((ihsg_df['close'].iloc[-1]-ihsg_df['close'].iloc[-2])/ihsg_df['close'].iloc[-2])*100
        ihsg_df['ma20'] = ihsg_df['close'].rolling(20).mean()
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=ihsg_df.index, y=ihsg_df['close'], fill='tozeroy',
                                 line_color='#00bbff', fillcolor='rgba(0,187,255,0.07)', name='IHSG'))
        fig.add_trace(go.Scatter(x=ihsg_df.index, y=ihsg_df['ma20'],
                                 line=dict(color='orange',width=1.5,dash='dot'), name='MA20'))
        fig.update_layout(height=230, template='plotly_dark', margin=dict(l=0,r=0,t=0,b=0),
                          showlegend=False, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
        ca,cb,cc,cd = st.columns(4)
        ca.metric("Last",       fmt_price(ihsg_df['close'].iloc[-1]))
        cb.metric("Change",     fmt_pct(ihsg_change))
        cc.metric("52W High",   fmt_price(ihsg_df['high'].max()))
        cd.metric("52W Low",    fmt_price(ihsg_df['low'].min()))

with col_sector:
    st.subheader("🗺️ Sectoral Heatmap (5D)")
    sec_data = []
    for s,t in SECTOR_PROXY.items():
        try:
            d = clean_df(yf.download(f"{t}.JK", period="10d", progress=False))
            if not d.empty and len(d)>=5:
                perf = ((d['close'].iloc[-1]-d['close'].iloc[-5])/d['close'].iloc[-5])*100
                sec_data.append({"Sektor":s,"Perf":round(safe_float(perf),1),"Parent":"IDX","Size":10})
        except: continue
    if sec_data:
        df_s = pd.DataFrame(sec_data)
        fig = px.treemap(df_s, path=['Parent','Sektor'], values='Size', color='Perf',
                         color_continuous_scale='RdYlGn', range_color=[-3,3])
        fig.update_layout(height=230, margin=dict(l=0,r=0,t=0,b=0), template='plotly_dark')
        st.plotly_chart(fig, use_container_width=True)
        best=max(sec_data,key=lambda x:x['Perf']); worst=min(sec_data,key=lambda x:x['Perf'])
        bias = "🟢 BULLISH" if ihsg_change>0.3 else ("🔴 BEARISH" if ihsg_change<-0.3 else "🟡 SIDEWAYS")
        st.caption(f"Bias: **{bias}** | 🏆 {best['Sektor']} ({best['Perf']:+.1f}%) | ⚠️ {worst['Sektor']} ({worst['Perf']:+.1f}%)")

st.divider()

# ── DEEP ANALYSIS ─────────────────────────────────────────────────────────────
st.subheader("🔬 Deep Analysis — Single Ticker")
inp1,inp2,inp3 = st.columns([1,2,1])
with inp1: manual = st.text_input("🔍 Kode (contoh: BBRI)","").upper()
with inp2: sec_sel = st.selectbox("📂 Pilih Sektor:",["—"]+list(MANUAL_SECTORS.keys()))
with inp3: tf = st.selectbox("📅 Timeframe:",["6mo","1y","2y"],index=1)

target = None
if manual:
    target = manual if manual.endswith(".JK") else f"{manual}.JK"
elif sec_sel != "—":
    pick = st.selectbox("Pilih Saham:", add_jk(MANUAL_SECTORS[sec_sel]))
    target = pick

if target:
    with st.spinner(f"Menganalisis {target}..."):
        df = analyze_full(target, period=tf)
    if df is not None:
        score,detail = score_ticker(df)
        signal,sig_color,sl,tp,rr = get_signal(df, score)
        l = df.iloc[-1]
        pats = detect_patterns(df)
        vr,vlbl,vsurge_light,vsurge_strong = volume_analysis(df)
        res,sup = calc_sr(df)
        cl=safe_float(l['close']); rsi=safe_float(l['rsi'])
        e20=safe_float(l['ema20']); e50=safe_float(l['ema50'])
        atr=safe_float(l['atr']); macd=safe_float(l['macd']); sig_v=safe_float(l['sig'])

        sc  = "score-high" if score>=65 else ("score-mid" if score>=45 else "score-low")
        tag = ("tag-sbuy" if "STRONG" in signal else
               ("tag-buy" if "BUY" in signal else
                ("tag-sell" if "SELL" in signal or "WEAK" in signal else "tag-hold")))

        st.markdown(f"### {target.replace('.JK','')}")
        c1,c2,c3,c4,c5 = st.columns(5)
        with c1:
            st.markdown(f"<div class='metric-card'><div style='color:#556;font-size:11px'>CONFLUENCE SCORE</div><div class='{sc}'>{score}/100</div></div>",unsafe_allow_html=True)
        with c2:
            st.markdown(f"<div class='metric-card'><div style='color:#556;font-size:11px'>SIGNAL</div><div style='margin-top:8px'><span class='{tag}'>{signal}</span></div></div>",unsafe_allow_html=True)
        with c3: st.metric("RSI (14)", f"{rsi:.0f}", delta="Oversold" if rsi<35 else ("Overbought" if rsi>72 else "Normal"))
        with c4: st.metric("Volume", vlbl)
        with c5: st.metric("ATR", fmt_price(atr))

        d1,d2,d3,d4,d5 = st.columns(5)
        d1.error(  f"❌ SL: {fmt_price(sl)}")
        d2.success(f"✅ TP: {fmt_price(tp)}")
        d3.info(   f"⚖️ R:R = 1:{rr}")
        gap=(cl-e20)/e20*100 if e20 else 0
        d4.metric("vs EMA20", f"{gap:+.1f}%")
        d5.metric("MACD","Bullish ↑" if macd>sig_v else "Bearish ↓")

        left,mid,right = st.columns(3)
        with left:
            st.markdown("**📊 Score Breakdown**")
            sdf = pd.DataFrame(list(detail.items()), columns=["Factor","Score"])
            sdf["Max"] = [25,25,20,15,15]
            fig_s = go.Figure(go.Bar(x=sdf["Score"], y=sdf["Factor"], orientation='h',
                marker_color=['#00ff99' if s/m>=0.7 else ('#ffcc00' if s/m>=0.4 else '#ff4466')
                              for s,m in zip(sdf["Score"],sdf["Max"])],
                text=sdf["Score"], textposition='auto'))
            fig_s.update_layout(height=200,template='plotly_dark',margin=dict(l=0,r=0,t=0,b=0),xaxis=dict(range=[0,25]))
            st.plotly_chart(fig_s, use_container_width=True)
        with mid:
            st.markdown("**🕯️ Patterns**")
            for p in pats: st.write(p)
            st.markdown("**📐 S/R Levels**")
            if res: st.markdown(f"🔴 R: {' | '.join([fmt_price(r) for r in res[:2]])}")
            if sup: st.markdown(f"🟢 S: {' | '.join([fmt_price(s) for s in sup[:2]])}")
        with right:
            st.markdown("**💡 Trade Setup**")
            lot10 = 10_000_000/cl/100 if cl>0 else 0
            st.markdown(f"""
            - 💰 **Entry:** {fmt_price(cl)} – {fmt_price(cl*1.005)}
            - ❌ **Max Loss/lot:** Rp {fmt_price((cl-sl)*100)}
            - ✅ **Target/lot:** Rp {fmt_price((tp-cl)*100)}
            - 📦 **Est. lot (10jt):** {lot10:.0f} lot
            - ⏱️ **Hold:** 1–3 hari
            """)

        interp_html,_,_ = interpret_analysis(target, score, detail, signal, df, sl, tp, rr,
                                              pats, vr, vsurge_light, vsurge_strong, ihsg_change)
        st.markdown(interp_html, unsafe_allow_html=True)

        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.55,0.25,0.20],
                            vertical_spacing=0.04, subplot_titles=("Price + Indicators","MACD","RSI + Volume"))
        fig.add_trace(go.Candlestick(x=df.index,open=df['open'],high=df['high'],low=df['low'],close=df['close'],
                                     increasing_line_color='#00ff99',decreasing_line_color='#ff4466',name='Price'),row=1,col=1)
        fig.add_trace(go.Scatter(x=df.index,y=df['ema20'],line=dict(color='orange',width=1.8),name='EMA20'),row=1,col=1)
        fig.add_trace(go.Scatter(x=df.index,y=df['ema50'],line=dict(color='#00aaff',width=1.2,dash='dot'),name='EMA50'),row=1,col=1)
        fig.add_trace(go.Scatter(x=df.index,y=df['bb_u'],line=dict(color='rgba(180,180,255,0.35)',width=1),name='BB',showlegend=False),row=1,col=1)
        fig.add_trace(go.Scatter(x=df.index,y=df['bb_l'],fill='tonexty',fillcolor='rgba(80,80,255,0.04)',
                                  line=dict(color='rgba(180,180,255,0.35)',width=1),showlegend=False),row=1,col=1)
        fig.add_hline(y=sl,line_dash="dash",line_color="#ff4466",annotation_text=f"SL {fmt_price(sl)}",row=1,col=1)
        fig.add_hline(y=tp,line_dash="dash",line_color="#00ff99",annotation_text=f"TP {fmt_price(tp)}",row=1,col=1)
        hc = ['#00ff99' if v>=0 else '#ff4466' for v in df['hist'].fillna(0)]
        fig.add_trace(go.Bar(x=df.index,y=df['hist'],marker_color=hc,name='Hist',showlegend=False),row=2,col=1)
        fig.add_trace(go.Scatter(x=df.index,y=df['macd'],line=dict(color='#00bbff',width=1.5),name='MACD'),row=2,col=1)
        fig.add_trace(go.Scatter(x=df.index,y=df['sig'],line=dict(color='orange',width=1.5),name='Signal'),row=2,col=1)
        fig.add_trace(go.Scatter(x=df.index,y=df['rsi'],line=dict(color='#bb77ff',width=1.5),name='RSI'),row=3,col=1)
        fig.add_hline(y=72,line_dash="dot",line_color="red",annotation_text="OB(72)",row=3,col=1)
        fig.add_hline(y=30,line_dash="dot",line_color="green",annotation_text="OS(30)",row=3,col=1)
        fig.add_hrect(y0=55,y1=72,fillcolor="rgba(0,255,150,0.05)",line_width=0,row=3,col=1)
        vc = ['#00ff99' if c>=o else '#ff4466' for c,o in zip(df['close'],df['open'])]
        fig.add_trace(go.Bar(x=df.index,y=df['volume']/df['volume'].max()*30,marker_color=vc,
                              opacity=0.35,showlegend=False),row=3,col=1)
        fig.update_layout(height=680,template='plotly_dark',xaxis_rangeslider_visible=False,
                          legend=dict(orientation='h',y=1.02),margin=dict(l=0,r=0,t=30,b=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning(f"Data tidak cukup untuk {target}.")

st.divider()

# ── SMART SCANNER ─────────────────────────────────────────────────────────────
st.subheader("🎯 Smart Scanner — Top 10 Rekomendasi Harian")

sc1,sc2,sc3,sc4 = st.columns([2,1,1,1])
with sc1: idx_choice = st.selectbox("📊 Universe:", list(INDEX_UNIVERSE.keys()))
with sc2: also_sector = st.multiselect("➕ Tambah Sektor:", list(MANUAL_SECTORS.keys()))
with sc3: min_score = st.slider("Min Score:", 0, 100, 55)
with sc4:
    now_jkt    = datetime.now(TZ_JKT).date()
    scan_date  = st.date_input("📅 Tanggal Scan:", value=now_jkt, max_value=now_jkt)

selected_universe = INDEX_UNIVERSE[idx_choice]
extra_from_sector = []
for sec in also_sector: extra_from_sector.extend(MANUAL_SECTORS[sec])
combined_universe = list(dict.fromkeys(selected_universe + extra_from_sector))

st.markdown(f"**Universe aktif: {len(combined_universe)} saham** · Hasil disimpan sebagai tanggal **{scan_date}** · Top 10 terbaik")

with st.expander("⚙️ Filter Tambahan", expanded=False):
    fc1,fc2,fc3 = st.columns(3)
    with fc1:
        min_vol_ratio   = st.slider("Min Volume Ratio:", 0.5, 3.0, 1.0, 0.1)
        require_surge   = st.checkbox("Wajib Volume Surge (🔥 ≥1.5x)", value=False)
    with fc2:
        min_rsi = st.slider("RSI Min:", 10, 50, 30)
        max_rsi = st.slider("RSI Max:", 50, 90, 70)
    with fc3:
        require_macd_bull  = st.checkbox("Wajib MACD Bullish", value=False)
        require_above_ema  = st.checkbox("Wajib Price > EMA20", value=True)
        signal_filter      = st.selectbox("Filter Signal:", ["Semua BUY","Strong BUY Only","Semua (incl HOLD)"])

if st.button("🚀 MULAI SCAN SEKARANG", use_container_width=True, type="primary"):
    tickers_to_scan = add_jk(combined_universe)
    prog   = st.progress(0); status = st.empty()
    t_start = time.time()

    scan_params = (min_score, signal_filter, require_above_ema,
                   min_vol_ratio, require_surge, require_macd_bull, min_rsi, max_rsi)

    results = run_parallel_scan(tickers_to_scan, scan_params, max_workers=12,
                                progress_placeholder=prog, status_placeholder=status)
    elapsed = time.time() - t_start
    prog.empty(); status.empty()
    st.caption(f"⏱️ Selesai dalam **{elapsed:.0f} detik** | {len(tickers_to_scan)} ticker discan")

    if results:
        df_res = pd.DataFrame(results).sort_values("Score", ascending=False).head(10)

        def color_score(val):
            if val>=70: return 'background-color:#004422;color:#00ff99'
            elif val>=55: return 'background-color:#332200;color:#ffcc00'
            else: return 'background-color:#2a0010;color:#ff8888'

        display_cols = ["Ticker","Score","Signal","Price","RSI","Vol","MACD","EMA20","SL","TP","R:R","Pattern"]
        # Format angka untuk display
        df_display = df_res[display_cols].copy()
        df_display["Price"] = df_display["Price"].apply(lambda x: fmt_price(x))
        df_display["SL"]    = df_display["SL"].apply(lambda x: fmt_price(x))
        df_display["TP"]    = df_display["TP"].apply(lambda x: fmt_price(x))
        df_display["RSI"]   = df_display["RSI"].apply(lambda x: f"{x:.0f}")

        styled = df_display.style.map(color_score, subset=['Score'])
        st.dataframe(styled, use_container_width=True, hide_index=True)
        st.success(f"✅ **{len(df_res)} kandidat terbaik** dari {len(tickers_to_scan)} saham")

        # Auto-save ke tracker
        n_saved = save_scan_results_to_log(df_res, str(scan_date))
        if n_saved>0:
            st.info(f"💾 **{n_saved} rekomendasi** disimpan ke tracker untuk tanggal {scan_date}.")
        else:
            st.caption(f"ℹ️ Ticker hari {scan_date} sudah tercatat di tracker sebelumnya.")

        # Top 3 detail
        st.markdown("### 🏆 Top 3 Setup Terbaik")
        for i,(_, row) in enumerate(df_res.head(3).iterrows()):
            medal = ["🥇","🥈","🥉"][i]
            sc2 = "score-high" if row['Score']>=65 else "score-mid"
            tg  = "tag-sbuy"  if "STRONG" in row['Signal'] else "tag-buy"
            try:
                df_top = analyze_full(f"{row['Ticker']}.JK", period="6mo")
                if df_top is not None:
                    sc_v2,det_v2  = score_ticker(df_top)
                    sig_v2,_,sl_v2,tp_v2,rr_v2 = get_signal(df_top, sc_v2)
                    pats_v2  = detect_patterns(df_top)
                    vr_v2,_,vsl_v2,vss_v2 = volume_analysis(df_top)
                    full_html,_,_ = interpret_analysis(f"{row['Ticker']}.JK", sc_v2, det_v2, sig_v2,
                                                       df_top, sl_v2, tp_v2, rr_v2, pats_v2, vr_v2, vsl_v2, vss_v2, ihsg_change)
                else:
                    full_html = "<p style='color:#556'>Interpretasi tidak tersedia.</p>"
            except:
                full_html = "<p style='color:#556'>Interpretasi tidak tersedia.</p>"

            with st.expander(f"{medal} #{i+1} {row['Ticker']} — Score {row['Score']}/100 | {row['Signal']} | Rp {fmt_price(row['Price'])}", expanded=(i==0)):
                col_a, col_b = st.columns([1, 2])
                with col_a:
                    st.markdown(f"""
                    <div class='metric-card'>
                        <div style='font-size:22px;font-weight:900;color:#00bbff'>{row['Ticker']}</div>
                        <div class='{sc2}'>{row['Score']}/100</div>
                        <div style='margin:8px 0'><span class='{tg}'>{row['Signal']}</span></div>
                        <hr style='border-color:#1e3050'>
                        <div style='font-size:12px;color:#778;text-align:left;line-height:2'>
                        💰 Harga: <b>Rp {fmt_price(row['Price'])}</b><br>
                        📊 RSI: <b>{row['RSI']}</b><br>
                        📦 Volume: <b>{row['Vol']}</b><br>
                        🕯️ Pattern: <b>{row['Pattern']}</b><br>
                        <hr style='border-color:#1e3050;margin:4px 0'>
                        ❌ SL: <span style='color:#ff6666'>{fmt_price(row['SL'])}</span><br>
                        ✅ TP: <span style='color:#66ff99'>{fmt_price(row['TP'])}</span><br>
                        ⚖️ R:R: <span style='color:#aaaaff'>{row['R:R']}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                with col_b:
                    st.markdown(full_html, unsafe_allow_html=True)

        st.markdown("### 📊 Distribusi Score Top 10")
        fig_dist = go.Figure()
        fig_dist.add_trace(go.Bar(
            x=df_res['Ticker'], y=df_res['Score'],
            marker_color=['#00ff99' if s>=70 else ('#ffcc00' if s>=55 else '#ff4466') for s in df_res['Score']],
            text=df_res['Score'], textposition='outside'
        ))
        fig_dist.add_hline(y=70,line_dash="dot",line_color="#00ff99",annotation_text="Strong Buy Zone")
        fig_dist.add_hline(y=55,line_dash="dot",line_color="#ffcc00",annotation_text="Buy Zone")
        fig_dist.update_layout(height=280, template='plotly_dark', margin=dict(l=0,r=0,t=10,b=0),
                               yaxis=dict(range=[0,105]), showlegend=False)
        st.plotly_chart(fig_dist, use_container_width=True)
    else:
        st.warning("Tidak ada saham yang memenuhi kriteria. Coba turunkan min score.")

st.divider()

# ── TRADE TRACKER ─────────────────────────────────────────────────────────────
st.subheader("📊 Trade Tracker — Pantau Rekomendasi Harian")

logs = load_trade_log()

# Toolbar atas: pilih tanggal + reset
tb1, tb2, tb3 = st.columns([2, 1, 1])
with tb1:
    all_dates = sorted({r['date'] for r in logs}, reverse=True)
    if all_dates:
        sel_date = st.selectbox("📅 Pilih Tanggal Scan:", all_dates,
                                format_func=lambda d: f"{d} ({sum(1 for r in logs if r['date']==d)} saham)")
    else:
        sel_date = None
        st.info("📭 Belum ada data. Jalankan scanner dulu.")

with tb2:
    if st.button("🔄 Refresh Harga", help="Ambil ulang harga terkini dari yfinance", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

with tb3:
    if st.button("🗑️ Hapus Semua Log", type="secondary", use_container_width=True):
        save_trade_log([])
        st.success("Log dikosongkan.")
        st.rerun()

if not logs or not sel_date:
    st.stop()

# Ambil trades untuk tanggal yang dipilih
day_trades = [r for r in logs if r['date'] == sel_date]
if not day_trades:
    st.warning(f"Tidak ada data untuk tanggal {sel_date}.")
    st.stop()

st.markdown(f"### 📅 Rekomendasi {sel_date} — {len(day_trades)} Saham")

# Fetch semua status sekaligus
with st.spinner("Mengambil harga terkini dari pasar..."):
    status_results = {}
    for trade in day_trades:
        status_results[trade['ticker']] = check_trade_status(
            trade['ticker'],
            float(trade['entry']),
            float(trade['sl']),
            float(trade['tp']),
            trade['date']
        )

# Summary bar
total_tp   = sum(1 for s in status_results.values() if "TP HIT" in s['status'])
total_sl   = sum(1 for s in status_results.values() if "SL HIT" in s['status'])
total_open = sum(1 for s in status_results.values() if "HIT" not in s['status'])
avg_pct    = np.mean([s['pct'] for s in status_results.values()]) if status_results else 0

sm1,sm2,sm3,sm4,sm5 = st.columns(5)
sm1.metric("Total Rekomendasi", len(day_trades))
sm2.metric("✅ TP Hit",   total_tp)
sm3.metric("❌ SL Hit",   total_sl)
sm4.metric("⏳ Open",      total_open)
wr = round(total_tp/(total_tp+total_sl)*100,0) if (total_tp+total_sl)>0 else 0
sm5.metric("Win Rate", f"{wr:.0f}%", delta=f"avg {avg_pct:+.1f}%")

st.markdown("---")

# Cards per saham
for trade in day_trades:
    ticker  = trade['ticker']
    entry   = float(trade['entry'])
    sl      = float(trade['sl'])
    tp      = float(trade['tp'])
    score   = int(trade['score'])
    signal  = trade['signal']
    pattern = trade.get('pattern', '—')
    s       = status_results.get(ticker, _no_data_result(entry, sl, tp))

    current   = s['current']
    pct       = s['pct']
    status_lbl= s['status']
    status_clr= s['color']
    rec_act   = s['rec_action']
    rec_clr   = s['rec_color']
    reason    = s['reason']
    last_date = s.get('last_date','—')
    pct_to_tp = s.get('pct_to_tp', 0)
    pct_to_sl = s.get('pct_to_sl', 0)

    # Progress bar visual
    is_hit    = "HIT" in status_lbl
    pct_gain  = (current-entry)/entry*100 if not is_hit else pct
    tp_pct_abs= (tp-entry)/entry*100 if entry>0 else 0
    sl_pct_abs= (entry-sl)/entry*100 if entry>0 else 0

    # Warna kartu berdasarkan status
    card_border = status_clr
    pct_color   = "#00ff99" if pct>=0 else "#ff4466"

    st.markdown(f"""
    <div style='background:#0a1020;border:1px solid {card_border}44;border-left:4px solid {card_border};
                border-radius:12px;padding:18px;margin:10px 0;'>
      <div style='display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px;'>

        <!-- KIRI: Info Saham -->
        <div style='min-width:130px'>
          <div style='font-size:22px;font-weight:900;color:#00bbff'>{ticker}</div>
          <div style='font-size:11px;color:#556;margin-top:2px'>Score: {score}/100 &nbsp;|&nbsp; {signal.split()[0]}</div>
          <div style='font-size:11px;color:#445;margin-top:2px'>🕯️ {pattern}</div>
        </div>

        <!-- TENGAH: Harga -->
        <div style='min-width:200px'>
          <div style='font-size:12px;color:#556;margin-bottom:4px'>HARGA</div>
          <div style='display:flex;gap:16px;flex-wrap:wrap'>
            <div><div style='font-size:10px;color:#445'>Entry</div>
                 <div style='font-size:14px;font-weight:700;color:#aac'>Rp {fmt_price(entry)}</div></div>
            <div><div style='font-size:10px;color:#445'>Sekarang ({last_date})</div>
                 <div style='font-size:16px;font-weight:900;color:{pct_color}'>Rp {fmt_price(current)}</div></div>
            <div><div style='font-size:10px;color:#445'>% Change</div>
                 <div style='font-size:16px;font-weight:900;color:{pct_color}'>{pct:+.1f}%</div></div>
          </div>
          <div style='display:flex;gap:12px;margin-top:8px'>
            <div><div style='font-size:10px;color:#ff6666'>SL {fmt_price(sl)}</div></div>
            <div><div style='font-size:10px;color:#66ff99'>TP {fmt_price(tp)}</div></div>
            <div><div style='font-size:10px;color:#aac'>R:R {trade.get("rr","—")}</div></div>
          </div>
        </div>

        <!-- KANAN: Status & Rekomendasi -->
        <div style='min-width:260px;flex:1'>
          <div style='font-size:11px;color:{status_clr};font-weight:700;margin-bottom:4px'>{status_lbl}</div>
          <div style='background:{rec_clr}22;border:1px solid {rec_clr}44;border-radius:8px;padding:8px 12px;'>
            <div style='font-size:13px;font-weight:900;color:{rec_clr};margin-bottom:4px'>{rec_act}</div>
            <div style='font-size:12px;color:#bbc;line-height:1.6'>{reason}</div>
          </div>
        </div>

      </div>

      <!-- Progress bar TP/SL -->
      <div style='margin-top:12px;'>
        <div style='display:flex;justify-content:space-between;font-size:10px;color:#445;margin-bottom:3px'>
          <span>SL {fmt_price(sl)} (−{sl_pct_abs:.1f}%)</span>
          <span>Entry {fmt_price(entry)}</span>
          <span>TP {fmt_price(tp)} (+{tp_pct_abs:.1f}%)</span>
        </div>
        <div style='background:#1a2030;border-radius:4px;height:8px;position:relative;overflow:hidden'>
          {'<div style="position:absolute;left:0;top:0;height:100%;width:'+str(max(0,min(100,50+pct/tp_pct_abs*50 if tp_pct_abs>0 else 50)))+'%;background:'+pct_color+';border-radius:4px;transition:width 0.5s;"></div>'}
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ── RINGKASAN P&L HARIAN ──────────────────────────────────────────────────────
st.markdown("### 📈 Ringkasan Performa Semua Tanggal")

if len(all_dates) > 0:
    summary_rows = []
    for d in all_dates:
        d_trades = [r for r in logs if r['date']==d]
        # Cek status dengan data yang sudah di-cache
        n_tp=n_sl=n_open=0; pct_sum=0.0; n_calc=0
        for t in d_trades:
            s = check_trade_status(t['ticker'], float(t['entry']), float(t['sl']), float(t['tp']), t['date'])
            if "TP HIT" in s['status']:   n_tp+=1
            elif "SL HIT" in s['status']: n_sl+=1
            else:                         n_open+=1
            pct_sum+=s['pct']; n_calc+=1
        avg_p = pct_sum/n_calc if n_calc>0 else 0
        wr_d  = round(n_tp/(n_tp+n_sl)*100,0) if (n_tp+n_sl)>0 else None
        summary_rows.append({
            "Tanggal": d,
            "Saham": len(d_trades),
            "✅ TP": n_tp,
            "❌ SL": n_sl,
            "⏳ Open": n_open,
            "Win Rate": f"{wr_d:.0f}%" if wr_d is not None else "—",
            "Avg P&L": f"{avg_p:+.1f}%",
        })
    df_summary = pd.DataFrame(summary_rows)

    def color_wr(val):
        if val == "—": return ""
        try:
            v = float(val.replace("%",""))
            if v>=60: return "color:#00ff99;font-weight:bold"
            elif v>=45: return "color:#ffcc00"
            return "color:#ff4466"
        except: return ""

    def color_pnl(val):
        try:
            v = float(val.replace("%","").replace("+",""))
            return "color:#00ff99" if v>0 else "color:#ff4466"
        except: return ""

    styled_sum = df_summary.style.map(color_wr, subset=["Win Rate"]).map(color_pnl, subset=["Avg P&L"])
    st.dataframe(styled_sum, use_container_width=True, hide_index=True)

st.divider()

# ── TAMBAH + HAPUS MANUAL ──────────────────────────────────────────────────────
col_add, col_del = st.columns(2)

with col_add:
    with st.expander("➕ Tambah Trade Manual", expanded=False):
        tm1,tm2 = st.columns(2)
        with tm1:
            m_ticker = st.text_input("Kode:", key="m_ticker").upper()
            m_signal = st.selectbox("Signal:", ["⚡ STRONG BUY","✅ BUY","🔄 HOLD/WATCH"], key="m_signal")
            m_score  = st.number_input("Score:", 0, 100, 60, key="m_score")
            m_pattern= st.text_input("Pattern:", key="m_pattern")
        with tm2:
            m_entry  = st.number_input("Entry (Rp):", min_value=0.0, step=10.0, key="m_entry")
            m_sl     = st.number_input("Stop Loss (Rp):", min_value=0.0, step=10.0, key="m_sl")
            m_tp     = st.number_input("Take Profit (Rp):", min_value=0.0, step=10.0, key="m_tp")
            m_date   = st.date_input("Tanggal:", value=datetime.today(), key="m_date")

        if st.button("➕ Tambah", key="add_manual", type="primary"):
            if m_ticker and m_entry>0:
                logs = load_trade_log()
                trade_id = f"{m_date}_{m_ticker}_manual"
                if any(l["id"]==trade_id for l in logs):
                    st.warning(f"Trade {m_ticker} tanggal {m_date} sudah ada.")
                else:
                    rr_m = round((m_tp-m_entry)/(m_entry-m_sl),1) if (m_entry-m_sl)>0 else 0
                    logs.append({
                        "id":      trade_id,
                        "date":    str(m_date),
                        "ticker":  m_ticker,
                        "signal":  m_signal,
                        "score":   int(m_score),
                        "entry":   float(m_entry),
                        "sl":      float(m_sl),
                        "tp":      float(m_tp),
                        "rr":      f"1:{rr_m}",
                        "pattern": m_pattern or "—",
                        "note":    "",
                    })
                    save_trade_log(logs)
                    st.success(f"✅ {m_ticker} ditambahkan."); st.rerun()
            else:
                st.error("Isi Kode Saham dan Harga Entry dulu.")

with col_del:
    with st.expander("🗑️ Hapus Trade Tertentu", expanded=False):
        if logs:
            all_ids = [f"{l['date']} — {l['ticker']} | Entry {fmt_price(l['entry'])}" for l in logs]
            del_idx = st.selectbox("Pilih trade:", range(len(all_ids)),
                                   format_func=lambda i: all_ids[i], key="del_sel")
            if st.button("🗑️ Hapus", key="del_btn", type="secondary"):
                del_id = logs[del_idx]["id"]
                logs   = [l for l in logs if l["id"] != del_id]
                save_trade_log(logs)
                st.success("Dihapus."); st.rerun()
        else:
            st.info("Tidak ada data untuk dihapus.")

st.divider()

# ── DOWNLOAD ──────────────────────────────────────────────────────────────────
dl1,dl2 = st.columns(2)
logs_now = load_trade_log()
with dl1:
    st.download_button("⬇️ Download CSV",
        pd.DataFrame(logs_now).to_csv(index=False).encode("utf-8"),
        f"idx_log_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv",
        use_container_width=True)
with dl2:
    st.download_button("⬇️ Download JSON",
        json.dumps(logs_now, indent=2, default=str).encode("utf-8"),
        f"idx_log_{datetime.now().strftime('%Y%m%d')}.json", "application/json",
        use_container_width=True)
