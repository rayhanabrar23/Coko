import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime
# ── BARU v4 ──────────────────────────────────────────────
import concurrent.futures
import time
# ─────────────────────────────────────────────────────────
# WIN/LOSS TRACKER — STORAGE (tambahan baru)
import json
from pathlib import Path
# ─────────────────────────────────────────────────────────

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

IDX_ALL_ACTIVE = list(dict.fromkeys([
    *IDX80, *IDX_GROWTH30, *IDX_SMC, *IDX_HIDIV20,
    "AGRO","BABP","BACA","BCIC","BDMN","BGTG","BJBR","BJTM","BKSW","BNBA",
    "BNII","BNLI","BPBB","BSWD","BTPN","BVIC","DNAR","INPC","MAYA","MCOR",
    "MEGA","NOBU","PNBS","SDRA","AGRS","AMAR","BBSI","BBYB","BCAP","BFIN",
    "CFIN","DEFI","HDFA","HOME","IMJS","KREN","LPGI","MFIN","MTFN","PADI",
    "PBID","TRIM","VRNA","WOMF",
    "ADMR","BOSS","BSSR","BTEK","BULL","BUMI","DEWA","ELSA","ESSA","FIRE",
    "GTSI","HRUM","INDY","KKGI","MBAP","MYOH","PKPK","PTRO","RUIS","SMMT",
    "SMRU","TOBA","ARII","BRAU","CITA","DSSA","FIRE","GTBO","HATA","INDY",
    "ITMG","KKGI","MBAP","MCOL","PTBA","RUIS","TOBA",
    "ACST","ADHI","APLN","ASRI","BEST","BIKA","BIPP","BKDP","BKSL","COWL",
    "CSAP","DGIK","DILD","DMAS","DUTI","ELTY","EMDE","EPMT","FMII","GAMA",
    "GMTD","GPRA","GWSA","JRPT","KIJA","LAND","LCGP","LPCK","LPKR","MDLN",
    "MKPI","MTLA","NIRO","OMRE","PANI","PJAA","PUDP","PWON","RDTX","RODA",
    "SCBD","SGRO","SMDM","SMRA","SSIA","TARA","WIKA","WSKT","TOTL","NRCA",
    "AISA","ALTO","CAMP","CEKA","CLEO","CNKO","COCO","CSMI","DAVO","DLTA",
    "DMND","FOOD","GOOD","HOKI","ICBP","IKAN","INDF","KEJU","KINO","LPPF",
    "LSIP","MAPI","MAPB","MBTO","MERK","MIDI","MLBI","MNKI","MRAT","MYOR",
    "NFCX","PCAR","PZZA","RANC","RICY","ROTI","SCCO","SIDO","SKBM","SKLT",
    "SMAR","SRTG","SSSS","STTP","TBLA","TCID","TGKA","TSPC","ULTJ","UNVR",
    "WIIM","WOOD","AALI","BWPT","DSNG","GZCO","JAWA","LSIP","PALM","SGRO",
    "SIMP","TAPG","UNSP","SSMS",
    "DVLA","INAF","KAEF","KLBF","MIKA","PRDA","PYFA","SAME","SILO","SILO",
    "HEAL","SOHO","SIDO","IRRA","OMED","PEHA","PRIM","RSGK","TSPC","MDRN",
    "BTEL","CENT","EXCL","FREN","GOLD","HALO","ISAT","META","MNCN","MTEL",
    "MYII","PGAS","SUPR","TBIG","TLKM","TOWR","TELE","TRIO","VKTR","WIFI",
    "WTON","JSMR","CMNP","INDY","META","NELY","PTIS","RAJA",
    "AGII","AKPI","ALDO","ALKA","ALMI","AMFG","APII","ARNA","BRNA","BTON",
    "CTBN","DPNS","EKAD","GDST","IGAR","IGLAS","IMPC","INAI","INCI","INKP",
    "INRU","INTP","ISSP","JTPE","JPRS","KDSI","KIAS","KPIG","LION","LMSH",
    "MARK","MDKA","MLIA","NIKL","NCKL","PICO","SIAP","SINI","SMCB","SMGR",
    "SPMA","SRSN","TBMS","TKIM","TPIA","TRST","UNIC","VOKS","WSBP","AMRT",
    "ARTO","BELI","BUKA","CASH","CHIP","DCII","DIVA","EMTK","GOTO","IPTV",
    "KIOS","MTDL","NFCX","POSA","SFAN","ATIC","AXIO","KREN","LUCK","MCAS",
    "MPPA","MSIN","MSKY","NETV","OASA","OMED","RELI","TELE","TGRA","VKTR",
    "APOL","ASSA","BIRD","BLTZ","BPTR","BULL","CASS","CMPP","GIAA","GOOD",
    "IATA","INDX","IPCC","JTPE","LEAD","LNDF","MBSS","MIRA","NELY","PTIS",
    "RAJA","SAFE","SMDR","SOCI","TMAS","TNCA","TPMA","TRUK","WEHA","WINS",
    "AALI","ANJT","BWPT","DSNG","GZCO","JAWA","LSIP","MAGP","MGRO","PALM",
    "SGRO","SIMP","SMAR","SSMS","TBLA","UNSP","TGRA","CPRO","IIKP","MBSS",
]))

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
    "IDX30 (Blue Chip, ~30 saham)":           IDX30,
    "LQ45 (Liquid 45, ~45 saham)":            LQ45,
    "IDX80 (Broad Market, ~80 saham)":        IDX80,
    "IDX High Dividend 20":                   IDX_HIDIV20,
    "IDX Growth30":                            IDX_GROWTH30,
    "IDX SMC Liquid (Small-Mid Cap)":         IDX_SMC,
    "ALL IDX Combined (~180 unik)":           list(dict.fromkeys(IDX80 + IDX_GROWTH30 + IDX_SMC + IDX_HIDIV20)),
    "🆕 ALL BEI Aktif (~400 saham, parallel)": IDX_ALL_ACTIVE,
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
# ANALYSIS ENGINE
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

def volume_analysis(df):
    if 'volume' not in df.columns or len(df)<20: return 0,"N/A",False,False
    avg = df['volume'].rolling(20).mean().iloc[-1]
    last = df['volume'].iloc[-1]
    ratio = safe_float(last/avg) if avg>0 else 0
    is_surge = ratio >= 1.5
    label = f"{ratio:.1f}x"
    if is_surge: label += " 🔥"
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
    if hist>0 and len(df)>1 and safe_float(df['hist'].iloc[-2])>=0 and hist>safe_float(df['hist'].iloc[-2]):
        ms+=3

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
    cl=safe_float(l['close']); e20=safe_float(l['ema20'] if 'ema20' in df.columns else l['close'])
    e50=safe_float(l['ema50'] if 'ema50' in df.columns else l['close'])
    rsi=safe_float(l['rsi'] if 'rsi' in df.columns else 50)
    macd=safe_float(l['macd'] if 'macd' in df.columns else 0)
    sig=safe_float(l['sig'] if 'sig' in df.columns else 0)
    atr=safe_float(l['atr'] if 'atr' in df.columns else cl*0.02)

    sl=cl-(1.5*atr); tp=cl+(2.5*atr)
    rr=round((tp-cl)/(cl-sl),2) if (cl-sl)>0 else 0

    if score>=70 and cl>e20 and rsi<65 and macd>sig:   return "⚡ STRONG BUY","#00ff99",sl,tp,rr
    elif score>=55 and cl>e20 and rsi<70:               return "✅ BUY","#44dd88",sl,tp,rr
    elif rsi>75 or (cl<e50 and cl<e20 and score<35):   return "❌ SELL/AVOID","#ff4466",sl,tp,rr
    elif score<40:                                      return "⚠️ WEAK/SKIP","#ff8844",sl,tp,rr
    else:                                               return "🔄 HOLD/WATCH","#ffcc00",sl,tp,rr

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
    else:
        df['macd']=df['sig']=df['hist']=0
    bb=ta.bbands(df['close'],length=20,std=2)
    if bb is not None and not bb.empty:
        df['bb_u']=bb.iloc[:,0]; df['bb_m']=bb.iloc[:,1]; df['bb_l']=bb.iloc[:,2]
    else:
        df['bb_u']=df['bb_m']=df['bb_l']=df['close']
    df['vol_ma20']=df['volume'].rolling(20).mean()
    return df

def quick_volume_check(ticker, min_avg_lot=500):
    try:
        d = yf.download(ticker, period="10d", progress=False)
        d = clean_df(d)
        if d.empty or 'volume' not in d.columns: return False
        avg_vol = d['volume'].mean()
        return safe_float(avg_vol) >= (min_avg_lot * 100)
    except:
        return False

def _scan_one(args):
    (ticker, min_score, signal_filter, require_above_ema,
     min_vol_ratio, require_surge, require_macd_bull,
     min_rsi, max_rsi, min_avg_lot, use_vol_prefilter) = args

    ticker_name = ticker.replace(".JK","")

    try:
        if use_vol_prefilter:
            if not quick_volume_check(ticker, min_avg_lot):
                return None, ticker_name, "Vol Pre-filter", f"Avg vol < {min_avg_lot} lot/hari"

        d = analyze_full_cached(ticker, period="6mo")
        if d is None or d.empty:
            return None, ticker_name, "Data", "Data kosong atau < min candle"

        last = d.iloc[-1]
        rsi_q  = safe_float(last.get('rsi',  50))
        cl_q   = safe_float(last.get('close', 0))
        ema_q  = safe_float(last.get('ema20', cl_q))
        macd_v = safe_float(last.get('macd',  0))
        sig_v2 = safe_float(last.get('sig',   0))

        if not (min_rsi <= rsi_q <= max_rsi):
            return None, ticker_name, "RSI", f"RSI={rsi_q:.1f} di luar [{min_rsi}–{max_rsi}]"

        if require_above_ema:
            if cl_q < ema_q:
                return None, ticker_name, "EMA20", f"Harga {cl_q:,.0f} < EMA20 {ema_q:,.0f}"
        else:
            gap_pct = (cl_q - ema_q) / ema_q * 100 if ema_q > 0 else 0
            if gap_pct < -1.5:
                return None, ticker_name, "EMA Toleransi", f"Gap EMA={gap_pct:.1f}%"

        sc_val, sc_det = score_ticker(d)
        if sc_val < min_score:
            return None, ticker_name, "Score", f"Score={sc_val} < min {min_score}"

        sig, _, sl_v, tp_v, rr_v = get_signal(d, sc_val)
        if "SELL" in sig or "WEAK" in sig:
            return None, ticker_name, "Signal", f"Signal={sig}"
        if signal_filter == "Strong BUY Only" and "STRONG" not in sig:
            return None, ticker_name, "Signal Filter", f"Butuh STRONG BUY, dapat {sig}"
        if signal_filter == "Semua BUY" and "BUY" not in sig and "BREAKOUT" not in sig:
            return None, ticker_name, "Signal Filter", f"Bukan BUY: {sig}"

        vr, vlbl, vsurge_light, vsurge_strong = volume_analysis(d)
        if require_surge and not vsurge_light:
            return None, ticker_name, "Volume", f"Vol={vr:.2f}x, butuh surge ≥1.5x"
        if vr < min_vol_ratio:
            return None, ticker_name, "Volume Ratio", f"Vol={vr:.2f}x < min {min_vol_ratio}x"

        if require_macd_bull and macd_v <= sig_v2:
            return None, ticker_name, "MACD", f"MACD={macd_v:.4f} <= Signal={sig_v2:.4f}"

        pats = detect_patterns(d)
        result = {
            "Ticker":    ticker_name,
            "Score":     sc_val,
            "Signal":    sig,
            "Price":     int(cl_q),
            "RSI":       round(rsi_q, 1),
            "Vol":       vlbl,
            "MACD":      "✅" if macd_v > sig_v2 else "❌",
            "EMA20":     "✅" if cl_q >= ema_q else f"⚠️{((cl_q-ema_q)/ema_q*100):.1f}%",
            "SL":        int(sl_v),
            "TP":        int(tp_v),
            "R:R":       f"1:{rr_v}",
            "Pattern":   pats[0] if pats else "—",
            "Trend_s":   sc_det.get('Trend', 0),
            "Mom_s":     sc_det.get('Momentum', 0),
            "_cl":       cl_q,
            "_vr":       vr,
            "_vsurge_l": vsurge_light,
            "_vsurge_s": vsurge_strong,
        }
        return result, ticker_name, None, None

    except Exception as e:
        return None, ticker_name, "Exception", str(e)


def run_parallel_scan(tickers, scan_params, max_workers=10, progress_placeholder=None, status_placeholder=None):
    args_list = [(t, *scan_params) for t in tickers]
    results = []
    debug_log = []
    errors = 0
    completed = 0
    total = len(tickers)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_scan_one, args): args[0] for args in args_list}
        for future in concurrent.futures.as_completed(futures):
            completed += 1
            ticker_raw = futures[future]
            try:
                result, ticker_name, gate, reason = future.result()
                if result:
                    results.append(result)
                elif gate:
                    debug_log.append({"Ticker": ticker_name, "Gugur di": gate, "Alasan": reason})
            except Exception as e:
                errors += 1
                debug_log.append({"Ticker": ticker_raw.replace(".JK",""), "Gugur di": "Exception", "Alasan": str(e)})

            if progress_placeholder:
                progress_placeholder.progress(completed / total)
            if status_placeholder:
                eta_done = completed / total * 100
                status_placeholder.markdown(
                    f"⚡ Parallel scan: **{completed}/{total}** ticker diproses "
                    f"| Kandidat: **{len(results)}** "
                    f"| Progress: **{eta_done:.0f}%**"
                )

    return results, debug_log, errors

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

    gap_pct = (cl - e20) / e20 * 100 if e20 else 0
    if cl > e20 and cl > e50:
        pros.append(f"Harga berada di atas EMA20 ({e20:,.0f}) dan EMA50 ({e50:,.0f}), tren naik jangka pendek dan menengah masih kuat.")
    elif cl > e20 and cl <= e50:
        cautions.append(f"Harga sudah di atas EMA20 ({gap_pct:+.1f}%), tapi masih di bawah EMA50 — tren menengah belum recovery penuh.")
    elif -1.5 <= gap_pct < 0:
        cautions.append(f"Harga sedikit di bawah EMA20 ({gap_pct:.1f}%) — masih dalam toleransi untuk setup breakout.")
    else:
        cons.append(f"Harga ({cl:,.0f}) masih di bawah EMA20 ({e20:,.0f}) dan EMA50 ({e50:,.0f}). Tren masih negatif.")

    if -0.5 <= gap_pct <= 3:
        pros.append(f"Posisi harga {gap_pct:+.1f}% dari EMA20 — zona entry ideal sebelum breakout terjadi.")
    elif 3 < gap_pct <= 6:
        cautions.append(f"Harga sudah {gap_pct:.1f}% di atas EMA20. Masih acceptable tapi sizing lebih kecil.")
    elif gap_pct > 6:
        cautions.append(f"Harga {gap_pct:.1f}% di atas EMA20 — risiko koreksi ke EMA20 meningkat.")

    if 55 <= rsi <= 72:
        pros.append(f"RSI {rsi:.1f} berada di zona momentum prime (55–72). Sweet spot untuk daily trade breakout.")
    elif 40 <= rsi < 55:
        pros.append(f"RSI {rsi:.1f} di zona akumulasi — saham sedang istirahat dan siap kembali naik.")
    elif rsi < 35:
        pros.append(f"RSI {rsi:.1f} oversold ekstrem — peluang rebound teknikal sangat tinggi.")
    elif 72 < rsi <= 78:
        cautions.append(f"RSI {rsi:.1f} mulai panas. Kurangi sizing dan perketat SL.")
    elif rsi > 78:
        cons.append(f"RSI {rsi:.1f} overbought berlebihan (>78). Hindari entry baru.")

    if macd > sig:
        hist_val = safe_float(l['hist'] if 'hist' in df.columns else 0)
        prev_hist = safe_float(df['hist'].iloc[-2] if 'hist' in df.columns and len(df)>1 else 0)
        if hist_val > prev_hist:
            pros.append(f"MACD golden cross dan histogram terus membesar — momentum beli semakin akseleratif.")
        else:
            pros.append(f"MACD di atas signal line (bullish) — tekanan beli masih dominan.")
    else:
        cons.append(f"MACD masih di bawah signal line. Tunggu golden cross untuk konfirmasi entry.")

    if vsurge_strong:
        pros.append(f"Volume {vr:.1f}x rata-rata 20 hari — surge kuat 🔥🔥. Konfirmasi institusional.")
    elif vsurge_light:
        pros.append(f"Volume {vr:.1f}x rata-rata — surge ringan 🔥. Minat beli mulai masuk.")
    elif vr >= 1.0:
        cautions.append(f"Volume di rata-rata ({vr:.1f}x). Pergerakan belum dikonfirmasi volume besar.")
    else:
        cautions.append(f"Volume sepi ({vr:.1f}x rata-rata). Rentan reversal tiba-tiba.")

    if 'bb_l' in df.columns and 'bb_m' in df.columns:
        bb_l = safe_float(l['bb_l']); bb_m = safe_float(l['bb_m']); bb_u = safe_float(l['bb_u'])
        if cl <= bb_l * 1.01:
            pros.append(f"Harga menyentuh lower BB ({bb_l:,.0f}) — zona oversold BB, sering berbalik ke midband ({bb_m:,.0f}).")
        elif cl <= bb_m:
            pros.append(f"Harga antara lower BB dan midband — zona akumulasi yang bagus untuk entry.")
        elif cl > bb_m and cl < bb_u * 0.97:
            bb_width = (bb_u - bb_l) / bb_m if bb_m > 0 else 0
            if bb_width > 0.04:
                pros.append(f"Harga di upper half BB dan bandwidth masih melebar — tanda momentum breakout yang sehat.")
            else:
                cautions.append(f"Harga di atas midband BB tapi bandwidth mulai menyempit — momentum bisa melambat.")
        elif cl >= bb_u * 0.97:
            cons.append(f"Harga mendekati upper BB ({bb_u:,.0f}). Set SL ketat.")

    pat_str = pats[0] if pats else "—"
    if any(k in pat_str for k in ['Engulfing','Morning Star','Hammer','Marubozu']):
        pros.append(f"Pola candlestick bullish terdeteksi — konfirmasi visual pembalikan atau lanjutan naik.")
    elif any(k in pat_str for k in ['Bearish','Evening Star']):
        cons.append(f"Pola bearish terdeteksi — waspada tekanan jual meningkat.")
    elif 'Doji' in pat_str:
        cautions.append(f"Pola Doji — pasar ragu-ragu. Tunggu candle konfirmasi sebelum masuk.")

    if ihsg_change > 0.5:
        pros.append(f"IHSG momentum positif ({ihsg_change:+.2f}%) — tailwind dari market secara keseluruhan.")
    elif ihsg_change < -0.5:
        cautions.append(f"IHSG sedang melemah ({ihsg_change:+.2f}%). Setup bagus bisa ikut tertekan.")

    if rr >= 2.0:
        pros.append(f"Risk:Reward 1:{rr} — secara matematis menguntungkan.")
    elif 1.5 <= rr < 2.0:
        cautions.append(f"R:R 1:{rr} — di batas minimum. Masih acceptable.")
    else:
        cautions.append(f"R:R hanya 1:{rr} — terlalu kecil. Cari entry yang lebih baik.")

    score_cons = len(cons)
    if "STRONG BUY" in signal or ("BUY" in signal and score_cons == 0 and len(pros) >= 4):
        verdict_title = f"✅ LAYAK DIBELI — Setup {name} Tergolong Kuat"
        verdict_color = "#00ff99"; confidence = "TINGGI"; conf_color = "#00ff99"
        verdict_open = f"Skor {score}/100 — saham <b>{name}</b> di Rp {cl:,.0f} menunjukkan setup beli yang kuat untuk daily trade."
    elif "BUY" in signal and score_cons <= 1:
        verdict_title = f"🟡 BOLEH DIPERTIMBANGKAN — Setup {name} Cukup Layak"
        verdict_color = "#ffcc00"; confidence = "SEDANG"; conf_color = "#ffcc00"
        verdict_open = f"Skor {score}/100 — <b>{name}</b> di Rp {cl:,.0f} punya setup yang layak dengan beberapa catatan."
    elif "SELL" in signal or "WEAK" in signal or score_cons >= 3:
        verdict_title = f"❌ TIDAK DISARANKAN — {name} Belum Siap"
        verdict_color = "#ff4466"; confidence = "RENDAH"; conf_color = "#ff4466"
        verdict_open = f"Skor {score}/100 — <b>{name}</b> di Rp {cl:,.0f} belum memiliki setup yang aman saat ini."
    else:
        verdict_title = f"⏳ TUNGGU KONFIRMASI — {name} Transisi"
        verdict_color = "#aaaaff"; confidence = "MENUNGGU"; conf_color = "#aaaaff"
        verdict_open = f"Skor {score}/100 — {name} sedang transisi. Campuran sinyal positif dan negatif."

    if "BUY" in signal and "WEAK" not in signal:
        closing = (f"<b>Kesimpulan:</b> Entry area Rp {cl:,.0f}–{cl*1.005:,.0f}, "
                   f"SL Rp {sl:,.0f} (−{((cl-sl)/cl*100):.1f}%), "
                   f"TP Rp {tp:,.0f} (+{((tp-cl)/cl*100):.1f}%). Hold 1–3 hari trading.")
    else:
        closing = (f"<b>Alternatif:</b> Masukkan {name} ke watchlist. Tunggu RSI di 40–65 dan MACD golden cross sebelum entry.")

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
            ⚠️ Analisis teknikal saja — bukan saran investasi.
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

    reasons  = []
    warnings = []

    if score >= 70:      reasons.append(f"skor tinggi ({score}/100)")
    if vsurge:           reasons.append("volume surge 🔥")
    if macd_ok:          reasons.append("MACD bullish")
    if ema_ok:           reasons.append("di atas EMA20")
    if 55 <= rsi <= 72:  reasons.append(f"RSI momentum prime ({rsi})")
    elif 40 <= rsi < 55: reasons.append(f"RSI akumulasi ({rsi})")
    elif rsi < 35:       reasons.append(f"RSI oversold ({rsi}) — potensi rebound")

    if not ema_ok:       warnings.append("harga di bawah EMA20")
    if not macd_ok:      warnings.append("MACD masih bearish")
    if rsi > 75:         warnings.append(f"RSI panas ({rsi})")
    if not vsurge:       warnings.append("volume belum surge")
    if ihsg_change < -0.5: warnings.append("IHSG melemah")

    if "STRONG" in signal and not warnings:
        verdict = f"🟢 <b>BUY SEKARANG</b> — {', '.join(reasons[:3])}. Setup premium."
    elif "BUY" in signal and len(warnings) <= 1:
        w_note = f" Perhatikan: {warnings[0]}." if warnings else ""
        verdict = f"🟡 <b>BUY sizing kecil</b> — {', '.join(reasons[:2])}.{w_note}"
    elif warnings:
        verdict = f"⏳ <b>Tunggu konfirmasi</b> — {', '.join(warnings[:2])}. Masuk setelah reversal konfirmasi."
    else:
        verdict = f"👀 <b>Watchlist</b> — Setup sedang terbentuk."

    return verdict


# ─────────────────────────────────────────────────────────
# WIN/LOSS TRACKER — FUNGSI STORAGE
# ─────────────────────────────────────────────────────────

TRACKER_FILE = Path("idx_trade_log.json")

def load_trade_log() -> list:
    if TRACKER_FILE.exists():
        with open(TRACKER_FILE, "r") as f:
            return json.load(f)
    return []

def save_trade_log(logs: list):
    with open(TRACKER_FILE, "w") as f:
        json.dump(logs, f, indent=2, default=str)

def save_scan_results_to_log(df_results: pd.DataFrame, scan_date: str = None):
    if scan_date is None:
        scan_date = datetime.now().strftime("%Y-%m-%d")
    logs = load_trade_log()
    existing_keys = {(e["date"], e["ticker"]) for e in logs}
    new_entries = 0
    for _, row in df_results.iterrows():
        key = (scan_date, row["Ticker"])
        if key in existing_keys:
            continue
        logs.append({
            "id":         f"{scan_date}_{row['Ticker']}",
            "date":       scan_date,
            "ticker":     row["Ticker"],
            "signal":     row["Signal"],
            "score":      int(row["Score"]),
            "entry":      float(row["Price"]),
            "sl":         float(row["SL"]),
            "tp":         float(row["TP"]),
            "rr":         str(row["R:R"]),
            "pattern":    row.get("Pattern", "—"),
            "exit_price": None,
            "exit_date":  None,
            "status":     "OPEN",
            "note":       "",
        })
        new_entries += 1
    save_trade_log(logs)
    return new_entries

def compute_tracker_stats(logs: list) -> dict:
    closed = [l for l in logs if l["status"] in ("WIN", "LOSS")]
    wins   = [l for l in closed if l["status"] == "WIN"]
    losses = [l for l in closed if l["status"] == "LOSS"]
    opens  = [l for l in logs   if l["status"] == "OPEN"]

    pnl_list = []
    for l in closed:
        if l.get("exit_price") and l.get("entry"):
            pnl_list.append((float(l["exit_price"]) - float(l["entry"])) / float(l["entry"]) * 100)

    win_rate  = round(len(wins) / len(closed) * 100, 1) if closed else 0
    avg_pnl   = round(sum(pnl_list) / len(pnl_list), 2) if pnl_list else 0
    total_pnl = round(sum(pnl_list), 2) if pnl_list else 0

    strong_closed = [l for l in closed if "STRONG" in l["signal"]]
    strong_wins   = [l for l in strong_closed if l["status"] == "WIN"]
    buy_closed    = [l for l in closed if "STRONG" not in l["signal"]]
    buy_wins      = [l for l in buy_closed if l["status"] == "WIN"]

    # Streak hitung
    streak = 0; streak_type = "—"
    if closed:
        last_status = closed[-1]["status"]
        streak_type = "🟢 WIN" if last_status == "WIN" else "🔴 LOSS"
        for l in reversed(closed):
            if l["status"] == last_status:
                streak += 1
            else:
                break

    return {
        "total": len(logs), "closed": len(closed),
        "wins": len(wins), "losses": len(losses), "opens": len(opens),
        "win_rate": win_rate, "avg_pnl": avg_pnl, "total_pnl": total_pnl,
        "strong_wr": round(len(strong_wins)/len(strong_closed)*100,1) if strong_closed else 0,
        "buy_wr":    round(len(buy_wins)/len(buy_closed)*100,1) if buy_closed else 0,
        "streak": streak, "streak_type": streak_type,
    }

# ─────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────
st.markdown("""
<h1 style='text-align:center;color:#00bbff;letter-spacing:3px;font-family:monospace;'>
⚡ IDX TERMINAL v4 — SMART SCANNER
</h1>
<p style='text-align:center;color:#445566;font-family:monospace;'>
Multi-Factor Daily Trade Analyzer · IDX30 / LQ45 / IDX80 / Growth30 / SMC · 400+ Universe · Parallel Scan
</p>
""", unsafe_allow_html=True)

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
        df=analyze_full(target, period=tf)
    if df is not None:
        score,detail=score_ticker(df)
        signal,sig_color,sl,tp,rr=get_signal(df, score)
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
    min_score = st.slider("Min Score:",0,100,55)
with sc4:
    top_n = st.number_input("Top N Hasil:",5,50,10)

is_all_bei = "ALL BEI" in idx_choice

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
        min_vol_ratio=st.slider("Min Volume Ratio:",0.5,3.0,1.0,0.1)
        require_surge=st.checkbox("Wajib Volume Surge (🔥 ≥1.5x)",value=False)
    with fc2:
        min_rsi=st.slider("RSI Min:",10,50,30)
        max_rsi=st.slider("RSI Max:",50,90,70)
    with fc3:
        require_macd_bull=st.checkbox("Wajib MACD Bullish Cross",value=False)
        require_above_ema=st.checkbox("Wajib Price > EMA20",value=True)

    if is_all_bei:
        st.divider()
        st.markdown("**⚡ Pengaturan Parallel Scan (ALL BEI)**")
        p1, p2, p3 = st.columns(3)
        with p1:
            max_workers = st.slider("Jumlah Thread Paralel:", 3, 20, 10,
                                    help="Semakin banyak = lebih cepat, tapi risiko rate-limit YFinance lebih tinggi. Recommended: 8–12.")
        with p2:
            use_vol_prefilter = st.checkbox("Pre-filter volume sebelum analisis penuh",
                                            value=True,
                                            help="Cek volume 10 hari dulu. Ticker sepi langsung dilewati → hemat waktu ~40%.")
            min_avg_lot = st.slider("Min avg volume (lot/hari):", 100, 2000, 500,
                                    help="1 lot = 100 lembar. Default 500 lot = volume minimal yang layak ditrade.") if use_vol_prefilter else 500
        with p3:
            st.info(f"""
            **Estimasi waktu scan:**
            - Tanpa pre-filter: ~8–15 menit
            - Dengan pre-filter: ~4–8 menit
            - Thread: {max_workers if is_all_bei else 10}
            """)
    else:
        max_workers = 10
        use_vol_prefilter = False
        min_avg_lot = 500

show_debug = st.checkbox("🐛 Debug Mode — tampilkan kenapa saham kegugur", value=False)

if is_all_bei:
    st.info(
        f"🆕 **Mode ALL BEI Aktif** — {len(combined_universe)} saham akan di-scan secara **paralel** "
        f"dengan {max_workers} thread. "
        f"{'Pre-filter volume aktif → ticker sepi dilewati otomatis.' if use_vol_prefilter else 'Pre-filter volume nonaktif.'} "
        f"Estimasi: **4–15 menit** tergantung koneksi."
    )

if st.button("🚀 MULAI SCAN SEKARANG",use_container_width=True,type="primary"):
    tickers_to_scan = add_jk(combined_universe)
    prog=st.progress(0); status=st.empty()
    start_time = time.time()

    scan_params = (
        min_score, signal_filter, require_above_ema,
        min_vol_ratio, require_surge, require_macd_bull,
        min_rsi, max_rsi, min_avg_lot, use_vol_prefilter
    )

    if is_all_bei:
        status.markdown(f"⚡ Memulai parallel scan **{len(tickers_to_scan)} saham** dengan {max_workers} thread...")
        results, debug_log, errors = run_parallel_scan(
            tickers_to_scan, scan_params,
            max_workers=max_workers,
            progress_placeholder=prog,
            status_placeholder=status
        )
    else:
        results=[]; debug_log=[]; errors=0
        for i,t in enumerate(tickers_to_scan):
            prog.progress((i+1)/len(tickers_to_scan))
            status.markdown(f"🔍 Scanning **{t}** ... ({i+1}/{len(tickers_to_scan)}) | Candidates: **{len(results)}**")
            ticker_name = t.replace(".JK","")
            try:
                d = analyze_full_cached(t, period="6mo")
                if d is None or d.empty:
                    if show_debug: debug_log.append({"Ticker":ticker_name,"Gugur di":"Data","Alasan":"Data kosong"})
                    continue
                last=d.iloc[-1]
                rsi_q=safe_float(last.get('rsi',50)); cl_q=safe_float(last.get('close',0))
                ema_q=safe_float(last.get('ema20',cl_q)); macd_v=safe_float(last.get('macd',0)); sig_v2=safe_float(last.get('sig',0))

                if not (min_rsi<=rsi_q<=max_rsi):
                    if show_debug: debug_log.append({"Ticker":ticker_name,"Gugur di":"RSI","Alasan":f"RSI={rsi_q:.1f}"})
                    continue
                if require_above_ema and cl_q<ema_q:
                    if show_debug: debug_log.append({"Ticker":ticker_name,"Gugur di":"EMA20","Alasan":f"Harga<EMA20"})
                    continue
                sc_val,sc_det=score_ticker(d)
                if sc_val<min_score:
                    if show_debug: debug_log.append({"Ticker":ticker_name,"Gugur di":"Score","Alasan":f"Score={sc_val}"})
                    continue
                sig,_,sl_v,tp_v,rr_v=get_signal(d,sc_val)
                if "SELL" in sig or "WEAK" in sig:
                    if show_debug: debug_log.append({"Ticker":ticker_name,"Gugur di":"Signal","Alasan":sig})
                    continue
                if signal_filter=="Strong BUY Only" and "STRONG" not in sig: continue
                if signal_filter=="Semua BUY" and "BUY" not in sig and "BREAKOUT" not in sig: continue
                vr,vlbl,vsurge_light,vsurge_strong=volume_analysis(d)
                if require_surge and not vsurge_light: continue
                if vr<min_vol_ratio: continue
                if require_macd_bull and macd_v<=sig_v2: continue
                pats=detect_patterns(d)
                results.append({
                    "Ticker":ticker_name,"Score":sc_val,"Signal":sig,"Price":int(cl_q),
                    "RSI":round(rsi_q,1),"Vol":vlbl,"MACD":"✅" if macd_v>sig_v2 else "❌",
                    "EMA20":"✅" if cl_q>=ema_q else f"⚠️{((cl_q-ema_q)/ema_q*100):.1f}%",
                    "SL":int(sl_v),"TP":int(tp_v),"R:R":f"1:{rr_v}","Pattern":pats[0] if pats else "—",
                    "Trend_s":sc_det.get('Trend',0),"Mom_s":sc_det.get('Momentum',0),
                    "_cl":cl_q,"_vr":vr,"_vsurge_l":vsurge_light,"_vsurge_s":vsurge_strong,
                })
            except Exception as e:
                errors+=1
                if show_debug: debug_log.append({"Ticker":ticker_name,"Gugur di":"Exception","Alasan":str(e)})

    elapsed = time.time() - start_time
    prog.empty(); status.empty()

    st.caption(f"⏱️ Scan selesai dalam **{elapsed:.1f} detik** ({elapsed/60:.1f} menit) | "
               f"{len(tickers_to_scan)} ticker diproses | {errors} error")

    if show_debug and debug_log:
        with st.expander(f"🐛 Debug Log — {len(debug_log)} saham kegugur", expanded=True):
            df_debug = pd.DataFrame(debug_log)
            gate_counts = df_debug['Gugur di'].value_counts().reset_index()
            gate_counts.columns = ['Gate', 'Jumlah']
            st.markdown("**Bottleneck per Gate:**")
            st.dataframe(gate_counts, use_container_width=True, hide_index=True)
            st.dataframe(df_debug, use_container_width=True, hide_index=True)

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

        # ── AUTO-SAVE ke Win/Loss Tracker ─────────────────
        n_saved = save_scan_results_to_log(df_res)
        if n_saved > 0:
            st.info(f"💾 **{n_saved} rekomendasi** baru otomatis disimpan ke Win/Loss Tracker.")
        else:
            st.caption("ℹ️ Semua ticker hari ini sudah tercatat di tracker.")

        st.markdown("### 📝 Interpretasi Tiap Saham")
        for _, row in df_res.iterrows():
            score_v = row['Score']
            sc_clr  = "#00ff99" if score_v>=70 else ("#ffcc00" if score_v>=55 else "#ff4466")
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
                    RSI: {row['RSI']}<br>Vol: {row['Vol']}<br>MACD: {row['MACD']}<br>
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
                df_top = analyze_full(f"{row['Ticker']}.JK", period="6mo")
                if df_top is not None:
                    sc_v2, det_v2 = score_ticker(df_top)
                    sig_v2, _, sl_v2, tp_v2, rr_v2 = get_signal(df_top, sc_v2)
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
            marker_color=['#00ff99' if s>=70 else ('#ffcc00' if s>=55 else '#ff4466') for s in df_res['Score']],
            text=df_res['Score'], textposition='outside'
        ))
        fig_dist.add_hline(y=70,line_dash="dot",line_color="#00ff99",annotation_text="Strong Buy Zone")
        fig_dist.add_hline(y=55,line_dash="dot",line_color="#ffcc00",annotation_text="Buy Zone")
        fig_dist.update_layout(height=300,template='plotly_dark',margin=dict(l=0,r=0,t=10,b=0),
                                yaxis=dict(range=[0,105]),showlegend=False)
        st.plotly_chart(fig_dist,use_container_width=True)

        st.divider()
        st.subheader("📋 Morning Review — Panduan Eksekusi")
        mktbias="🟢 BULLISH" if ihsg_change>0.3 else ("🔴 BEARISH" if ihsg_change<-0.3 else "🟡 SIDEWAYS")
        strong_picks=[r['Ticker'] for _,r in df_res.iterrows() if "STRONG" in r['Signal']]
        surge_picks=[r['Ticker'] for _,r in df_res.iterrows() if "🔥" in str(r.get('Vol',''))]

        st.markdown(f"""
        <div style='background:#0a1020;border:1px solid #1e3050;border-radius:12px;padding:20px;'>
        <b>🌐 IHSG:</b> {ihsg_df['close'].iloc[-1]:,.0f} <span style='color:{"#00ff99" if ihsg_change>0 else "#ff4466"}'>{ihsg_change:+.2f}%</span> — {mktbias}<br><br>
        <b>⚡ Strong Buy Candidates:</b> {', '.join(strong_picks) if strong_picks else '—'}<br>
        <b>🔥 Volume Surge Picks:</b> {', '.join(surge_picks) if surge_picks else '—'}<br><br>
        <b>📌 Panduan Eksekusi:</b>
        <ol style='color:#99aacc;margin-top:8px'>
        <li>Prioritaskan saham <b>Score ≥ 70 + Volume Surge 🔥</b> → Setup Premium.</li>
        <li>Jika IHSG {mktbias}, {"hanya masuk setup terkuat (Score ≥ 70)" if "BEARISH" in mktbias else "bisa lebih agresif tapi tetap pakai SL"}.</li>
        <li>Masuk dekat <b>Support / EMA20</b>, bukan setelah saham sudah lari jauh.</li>
        <li>R:R wajib ≥ 1:2 sebelum eksekusi. Skip jika R:R &lt; 1:1.5.</li>
        <li>MACD Bullish Cross ✅ + RSI 40–60 + Volume Surge = <b>trifecta signal terkuat</b>.</li>
        <li>Gunakan max 20–25% modal per saham. Jangan all-in satu emiten.</li>
        </ol>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.warning(f"Tidak ada saham yang memenuhi semua kriteria. Coba turunkan min score atau longgarkan filter.")
        st.info(f"Total discan: {len(tickers_to_scan)} | Errors: {errors}")

st.divider()

# ─────────────────────────────────────────────────────────
# WIN/LOSS TRACKER — SECTION BARU
# ─────────────────────────────────────────────────────────
st.subheader("📊 Win/Loss Tracker — Rekap Performa Rekomendasi Harian")

logs = load_trade_log()

if not logs:
    st.info("📭 Belum ada data trade. Jalankan scanner dulu — hasil akan otomatis tersimpan ke tracker.")
else:
    stats = compute_tracker_stats(logs)

    # ── METRICS ROW ────────────────────────────────────
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("🏆 Win Rate",       f"{stats['win_rate']}%")
    m2.metric("✅ Menang",          stats['wins'])
    m3.metric("❌ Kalah",           stats['losses'])
    m4.metric("⏳ Open",            stats['opens'])
    m5.metric("📈 Avg P&L/trade",  f"{stats['avg_pnl']:+.2f}%")
    m6.metric("💰 Total P&L",      f"{stats['total_pnl']:+.2f}%")

    # ── CHARTS ROW ─────────────────────────────────────
    ch1, ch2 = st.columns(2)

    with ch1:
        # Win rate per signal type
        bar_df = pd.DataFrame({
            "Signal":   ["⚡ Strong Buy", "✅ Buy"],
            "Win Rate": [stats["strong_wr"], stats["buy_wr"]]
        })
        fig_wr = go.Figure(go.Bar(
            x=bar_df["Win Rate"], y=bar_df["Signal"], orientation='h',
            marker_color=["#00ff99", "#44aaff"],
            text=[f"{v}%" for v in bar_df["Win Rate"]],
            textposition='auto'
        ))
        fig_wr.update_layout(
            height=180, template='plotly_dark',
            margin=dict(l=0, r=0, t=30, b=0),
            xaxis=dict(range=[0, 100]),
            title_text="Win Rate per Tipe Signal"
        )
        st.plotly_chart(fig_wr, use_container_width=True)

    with ch2:
        # Pie chart WIN vs LOSS vs OPEN
        closed_total = stats['wins'] + stats['losses']
        if closed_total > 0:
            fig_pie = go.Figure(go.Pie(
                labels=["WIN", "LOSS", "OPEN"],
                values=[stats['wins'], stats['losses'], stats['opens']],
                marker_colors=["#00ff99", "#ff4466", "#44aaff"],
                hole=0.45,
                textinfo='label+percent'
            ))
            fig_pie.update_layout(
                height=180, template='plotly_dark',
                margin=dict(l=0, r=0, t=30, b=0),
                showlegend=False,
                title_text="Distribusi Hasil Trade"
            )
            st.plotly_chart(fig_pie, use_container_width=True)

    # ── P&L TIMELINE ───────────────────────────────────
    closed_logs = [l for l in logs if l["status"] in ("WIN","LOSS") and l.get("exit_price") and l.get("entry")]
    if len(closed_logs) >= 2:
        pnl_rows = []
        cumulative = 0.0
        for l in sorted(closed_logs, key=lambda x: x.get("exit_date") or x["date"]):
            p = (float(l["exit_price"]) - float(l["entry"])) / float(l["entry"]) * 100
            cumulative += p
            pnl_rows.append({
                "Tanggal": l.get("exit_date") or l["date"],
                "Ticker": l["ticker"],
                "P&L (%)": round(p, 2),
                "Kumulatif (%)": round(cumulative, 2)
            })
        df_pnl = pd.DataFrame(pnl_rows)
        fig_pnl = go.Figure()
        fig_pnl.add_trace(go.Bar(
            x=df_pnl["Ticker"] + " " + df_pnl["Tanggal"],
            y=df_pnl["P&L (%)"],
            marker_color=["#00ff99" if v >= 0 else "#ff4466" for v in df_pnl["P&L (%)"]],
            name="P&L per Trade"
        ))
        fig_pnl.add_trace(go.Scatter(
            x=df_pnl["Ticker"] + " " + df_pnl["Tanggal"],
            y=df_pnl["Kumulatif (%)"],
            mode='lines+markers',
            line=dict(color='#ffcc00', width=2),
            name="Kumulatif P&L"
        ))
        fig_pnl.add_hline(y=0, line_dash="dot", line_color="#445566")
        fig_pnl.update_layout(
            height=260, template='plotly_dark',
            margin=dict(l=0, r=0, t=30, b=0),
            title_text="P&L per Trade + Kumulatif",
            legend=dict(orientation='h', y=1.1)
        )
        st.plotly_chart(fig_pnl, use_container_width=True)

    st.divider()

    # ── UPDATE STATUS TRADE ────────────────────────────
    st.markdown("#### ✏️ Update Hasil Trade")
    open_logs = [l for l in logs if l["status"] == "OPEN"]

    if open_logs:
        options_label = [
            f"{l['date']} — {l['ticker']} | Entry: {float(l['entry']):,.0f} | SL: {float(l['sl']):,.0f} | TP: {float(l['tp']):,.0f}"
            for l in open_logs
        ]
        sel_idx = st.selectbox(
            f"Pilih trade open ({len(open_logs)} aktif):",
            range(len(options_label)),
            format_func=lambda i: options_label[i],
            key="sel_trade_open"
        )
        sel_log = open_logs[sel_idx]

        uc1, uc2, uc3, uc4 = st.columns(4)
        with uc1:
            new_status = st.selectbox("Status akhir:", ["WIN", "LOSS", "MANUAL"], key="new_status_sel")
        with uc2:
            default_exit = float(sel_log["tp"]) if new_status == "WIN" else float(sel_log["sl"])
            exit_price = st.number_input(
                "Harga exit (Rp):",
                min_value=0.0,
                value=default_exit,
                step=10.0,
                key="exit_price_input"
            )
        with uc3:
            exit_date_input = st.date_input("Tanggal exit:", value=datetime.today(), key="exit_date_input")
        with uc4:
            note_input = st.text_input("Catatan (opsional):", key="note_input_field")

        # Hitung preview P&L
        if exit_price > 0 and sel_log.get("entry"):
            preview_pnl = (exit_price - float(sel_log["entry"])) / float(sel_log["entry"]) * 100
            pnl_color = "#00ff99" if preview_pnl >= 0 else "#ff4466"
            st.markdown(
                f"<span style='color:{pnl_color};font-size:14px'>Preview P&L: {preview_pnl:+.2f}% "
                f"({'Profit ✅' if preview_pnl >= 0 else 'Loss ❌'})</span>",
                unsafe_allow_html=True
            )

        if st.button("💾 Simpan Update Trade", key="save_trade_update", type="primary"):
            for l in logs:
                if l["id"] == sel_log["id"]:
                    l["status"]     = new_status
                    l["exit_price"] = float(exit_price)
                    l["exit_date"]  = str(exit_date_input)
                    l["note"]       = note_input
                    break
            save_trade_log(logs)
            st.success(f"✅ Trade **{sel_log['ticker']}** berhasil diupdate ke **{new_status}**.")
            st.rerun()
    else:
        st.success("🎉 Tidak ada trade open saat ini. Semua sudah diupdate!")

    # ── TAMBAH TRADE MANUAL ────────────────────────────
    with st.expander("➕ Tambah Trade Manual (dari Deep Analysis)", expanded=False):
        tm1, tm2, tm3 = st.columns(3)
        with tm1:
            m_ticker  = st.text_input("Kode Saham:", key="m_ticker").upper()
            m_signal  = st.selectbox("Signal:", ["⚡ STRONG BUY","✅ BUY","🔄 HOLD/WATCH"], key="m_signal")
            m_score   = st.number_input("Score:", 0, 100, 60, key="m_score")
        with tm2:
            m_entry   = st.number_input("Harga Entry (Rp):", min_value=0.0, step=10.0, key="m_entry")
            m_sl      = st.number_input("Stop Loss (Rp):",   min_value=0.0, step=10.0, key="m_sl")
            m_tp      = st.number_input("Take Profit (Rp):", min_value=0.0, step=10.0, key="m_tp")
        with tm3:
            m_date    = st.date_input("Tanggal Entry:", value=datetime.today(), key="m_date")
            m_pattern = st.text_input("Pattern (opsional):", key="m_pattern")
            m_note    = st.text_input("Catatan:", key="m_note")

        if st.button("➕ Tambah ke Tracker", key="add_manual_trade"):
            if m_ticker and m_entry > 0:
                logs = load_trade_log()
                trade_id = f"{m_date}_{m_ticker}_manual"
                existing = [l for l in logs if l["id"] == trade_id]
                if existing:
                    st.warning(f"Trade {m_ticker} tanggal {m_date} sudah ada di log.")
                else:
                    rr_manual = round((m_tp - m_entry) / (m_entry - m_sl), 2) if (m_entry - m_sl) > 0 else 0
                    logs.append({
                        "id":         trade_id,
                        "date":       str(m_date),
                        "ticker":     m_ticker,
                        "signal":     m_signal,
                        "score":      int(m_score),
                        "entry":      float(m_entry),
                        "sl":         float(m_sl),
                        "tp":         float(m_tp),
                        "rr":         f"1:{rr_manual}",
                        "pattern":    m_pattern or "—",
                        "exit_price": None,
                        "exit_date":  None,
                        "status":     "OPEN",
                        "note":       m_note,
                    })
                    save_trade_log(logs)
                    st.success(f"✅ Trade {m_ticker} berhasil ditambahkan ke tracker.")
                    st.rerun()
            else:
                st.error("Isi Kode Saham dan Harga Entry terlebih dahulu.")

    st.divider()

    # ── TABEL LOG LENGKAP ──────────────────────────────
    st.markdown("#### 📋 Log Semua Trade")
    f1, f2, f3 = st.columns(3)
    with f1:
        filter_status = st.selectbox("Filter Status:", ["Semua","OPEN","WIN","LOSS","MANUAL"], key="fs_log")
    with f2:
        filter_signal = st.selectbox("Filter Signal:", ["Semua","STRONG BUY","BUY"], key="fg_log")
    with f3:
        filter_date_str = st.text_input("Filter Tanggal (YYYY-MM-DD):", key="fd_log")

    df_log = pd.DataFrame(logs)

    if filter_status != "Semua":
        df_log = df_log[df_log["status"] == filter_status]
    if filter_signal != "Semua":
        df_log = df_log[df_log["signal"].str.contains(
            "STRONG" if filter_signal == "STRONG BUY" else "BUY", na=False
        )]
    if filter_date_str:
        df_log = df_log[df_log["date"] == filter_date_str]

    def calc_pnl_str(row):
        try:
            if row["exit_price"] and row["entry"]:
                p = (float(row["exit_price"]) - float(row["entry"])) / float(row["entry"]) * 100
                return f"{p:+.2f}%"
        except:
            pass
        return "—"

    df_log["P&L (%)"] = df_log.apply(calc_pnl_str, axis=1)
    df_log["Hit"] = df_log["status"].map({
        "WIN": "✅ TP Hit", "LOSS": "❌ SL Hit", "OPEN": "⏳ Open", "MANUAL": "📝 Manual"
    }).fillna("—")

    show_cols = ["date","ticker","signal","score","entry","sl","tp","exit_price","exit_date","P&L (%)","Hit","status","note"]
    existing_cols = [c for c in show_cols if c in df_log.columns]

    def style_status(val):
        if val == "WIN":  return "background-color:#004422;color:#00ff99"
        if val == "LOSS": return "background-color:#3a0010;color:#ff4466"
        if val == "OPEN": return "background-color:#001433;color:#44aaff"
        return ""

    styled_log = df_log[existing_cols].sort_values("date", ascending=False).style.map(
        style_status, subset=["status"]
    )
    st.dataframe(styled_log, use_container_width=True, hide_index=True)

    # ── HAPUS TRADE ─────────────────────────────────────
    with st.expander("🗑️ Hapus Trade dari Log", expanded=False):
        all_ids = [f"{l['date']} — {l['ticker']} ({l['status']})" for l in logs]
        del_idx = st.selectbox("Pilih trade yang ingin dihapus:", range(len(all_ids)),
                               format_func=lambda i: all_ids[i], key="del_trade_sel")
        if st.button("🗑️ Hapus Trade Ini", key="del_trade_btn", type="secondary"):
            del_id = logs[del_idx]["id"]
            logs = [l for l in logs if l["id"] != del_id]
            save_trade_log(logs)
            st.success("Trade berhasil dihapus.")
            st.rerun()

    # ── DOWNLOAD ────────────────────────────────────────
    dl1, dl2 = st.columns(2)
    with dl1:
        csv_data = pd.DataFrame(logs).to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download Log CSV",
            csv_data,
            f"idx_trade_log_{datetime.now().strftime('%Y%m%d')}.csv",
            "text/csv",
            use_container_width=True
        )
    with dl2:
        json_data = json.dumps(logs, indent=2, default=str).encode("utf-8")
        st.download_button(
            "⬇️ Download Log JSON",
            json_data,
            f"idx_trade_log_{datetime.now().strftime('%Y%m%d')}.json",
            "application/json",
            use_container_width=True
        )
