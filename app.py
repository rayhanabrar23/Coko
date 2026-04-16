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
            "id":       f"{scan_date_str}_{row['Ticker']}
