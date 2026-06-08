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

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="IDX Terminal v7",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
body, .stApp { background-color: #07090f; color: #d0d8e8; }
.block-container { padding-top: 1.2rem; padding-bottom: 1rem; }

/* Cards */
.metric-card {
    background: #0e1420; border: 1px solid #1e3050;
    border-radius: 10px; padding: 14px; text-align: center;
}
.reco-card {
    background: #0a1020; border-radius: 12px;
    border-left: 4px solid #00bbff;
    padding: 14px 18px; margin: 8px 0;
}
.warn-card {
    background: #120a0a; border-radius: 12px;
    border-left: 4px solid #ff4466;
    padding: 14px 18px; margin: 8px 0;
}

/* Score colors */
.score-high { color: #00ff99; font-size: 28px; font-weight: 900; }
.score-mid  { color: #ffcc00; font-size: 28px; font-weight: 900; }
.score-low  { color: #ff4466; font-size: 28px; font-weight: 900; }

/* Regime badges */
.regime-trend    { background:#003322; color:#00ff99; padding:4px 12px; border-radius:20px; font-weight:700; font-size:13px; }
.regime-range    { background:#332200; color:#ffcc00; padding:4px 12px; border-radius:20px; font-weight:700; font-size:13px; }
.regime-transit  { background:#1a1a33; color:#8888ff; padding:4px 12px; border-radius:20px; font-weight:700; font-size:13px; }

/* Signal tags */
.tag-sbuy { background:#004422; color:#00ff99; padding:3px 10px; border-radius:20px; font-weight:700; font-size:13px; }
.tag-buy  { background:#002e18; color:#44dd88; padding:3px 10px; border-radius:20px; font-weight:700; font-size:13px; }
.tag-hold { background:#332200; color:#ffcc00; padding:3px 10px; border-radius:20px; font-weight:700; font-size:13px; }
.tag-sell { background:#330011; color:#ff4466; padding:3px 10px; border-radius:20px; font-weight:700; font-size:13px; }

/* Universe badges */
.uni-badge {
    display:inline-block; background:#0a1428; border:1px solid #2244aa;
    color:#4488ff; padding:2px 8px; border-radius:10px; font-size:11px; margin:2px;
}

/* Tracker row */
.trade-row {
    background:#0a1020; border-radius:8px; border:1px solid #1e3050;
    padding:10px 14px; margin:4px 0; font-size:13px;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# UNIVERSE DATA
# ─────────────────────────────────────────────
IDX30 = ["AADI","ADRO","AMMN","ANTM","AMRT","ASII","BBCA","BBNI","BBRI","BBTN",
         "BMRI","BRIS","BUKA","CPIN","EXCL","GOTO","ICBP","INCO","INDF","ISAT",
         "ITMG","KLBF","MDKA","MEDC","MIKA","PGEO","PTBA","TLKM","TOWR","UNTR"]

LQ45 = list(dict.fromkeys(IDX30 + [
    "ACES","AKRA","ARTO","BELI","BNGA","BSDE","CTRA","EMTK","GGRM","HMSP",
    "INTP","JSMR","MAPI","MYOR","PGAS","PNBN","PWON","SMGR","TBIG","TINS",
    "TKIM","UNVR","HEAL","BYAN","CMRY","DCII","DSSA","NCKL","INKP","SILO"]))[:45]

IDX80_EXTRA = ["AVIA","BDMN","BUMI","DEWA","ENRG","GEMS","JPFA","MTEL","NISP",
               "SMRA","SSIA","TAPG","TCPI","SIDO","BRPT","FILM","CUAN","VKTR",
               "SOHO","MDIY","BSIM","BIPI","MAPI","PNBN","INKP","MYOR","CBDK","GGRM"]
IDX80 = list(dict.fromkeys(LQ45 + IDX80_EXTRA))[:80]

IDX_HIDIV20 = ["ADRO","ANTM","ASII","BBCA","BBNI","BBRI","BMRI","CPIN","GGRM","HMSP",
               "INDF","ITMG","KLBF","MEDC","PGAS","PTBA","SMGR","TLKM","UNTR","UNVR"]

IDX_GROWTH30 = ["ARTO","BELI","BRIS","BUKA","CMRY","DCII","DSSA","EMTK","GOTO","HEAL",
                "MIKA","MDKA","MTEL","NCKL","PGEO","SILO","TBIG","TOWR","VKTR","AMMN",
                "AADI","CUAN","BRMS","MBMA","TCPI","BREN","PANI","ARCO","CBDK","PGUN"]

IDX_SMC = ["ACES","AKRA","BDMN","BNGA","BSDE","CTRA","INTP","JPFA","JSMR","MAPI",
           "MYOR","NISP","PNBN","PWON","SMGR","SMRA","SSIA","TAPG","TINS","SIDO",
           "PYFA","SOHO","FILM","AVIA","BBHI","GEMS","BSIM","MDIY","MEGA","BBTN"]

UNIVERSES = {
    "IDX30 — Blue Chip (30)":         IDX30,
    "LQ45 — Liquid 45":               LQ45,
    "IDX80 — Broad Market":           IDX80,
    "IDX High Dividend 20":           IDX_HIDIV20,
    "IDX Growth 30":                  IDX_GROWTH30,
    "IDX SMC — Small/Mid Cap":        IDX_SMC,
    "ALL Combined (~180 unik)":       list(dict.fromkeys(IDX80 + IDX_GROWTH30 + IDX_SMC)),
}

SECTORS = {
    "Finance":    ["BBCA","BBRI","BMRI","BBNI","BRIS","ARTO","BNGA","PNBN","MEGA","BDMN","NISP","BBTN"],
    "Energy":     ["ADRO","ITMG","PTBA","MEDC","AKRA","PGAS","GEMS","AADI","BYAN","DSSA","TCPI","INDY"],
    "Healthcare": ["MIKA","HEAL","SILO","KLBF","SIDO","PYFA","SOHO"],
    "Basic Mat":  ["ANTM","TINS","MDKA","SMGR","INTP","TPIA","INCO","NCKL","AMMN","BRMS"],
    "Consumer":   ["ACES","MAPI","AMRT","ICBP","INDF","GGRM","HMSP","UNVR","MYOR","CPIN","CMRY","AVIA"],
    "Infra/Telco":["TLKM","ISAT","EXCL","TOWR","TBIG","JSMR","MTEL","PGAS","PGEO"],
    "Property":   ["BSDE","PWON","CTRA","SMRA","SSIA","CBDK","PANI","MKPI"],
    "Tech/Digital":["GOTO","BUKA","EMTK","DCII","BELI","BBHI","ARTO","VKTR"],
}

SECTOR_PROXY = {"Finance":"BBCA","Energy":"ADRO","Healthcare":"KLBF","Basic Mat":"ANTM",
                "Consumer":"ICBP","Infra/Telco":"TLKM","Property":"BSDE","Tech/Digital":"GOTO"}

TZ_JKT   = pytz.timezone("Asia/Jakarta")
TRACKER  = Path("idx_trade_log.json")

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def jk(t): return t if t.endswith(".JK") else f"{t}.JK"
def add_jk(lst): return [jk(t) for t in lst]

def clean_df(df):
    if df.empty: return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    return df

def sf(val, default=0.0):
    try:
        v = float(val)
        return default if (np.isnan(v) or np.isinf(v)) else v
    except: return default

# ─────────────────────────────────────────────
# CORE: FETCH + INDICATORS
# ─────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_df(ticker, period="6mo"):
    df = clean_df(yf.download(ticker, period=period, progress=False))
    if df.empty or len(df) < 52: return None
    df = df.copy()

    # Trend
    df['ema20']  = ta.ema(df['close'], length=20)
    df['ema50']  = ta.ema(df['close'], length=50)
    df['ema200'] = ta.ema(df['close'], length=200)

    # Momentum
    df['rsi']   = ta.rsi(df['close'], length=14)
    stoch = ta.stoch(df['high'], df['low'], df['close'], k=14, d=3)
    if stoch is not None and not stoch.empty:
        df['stoch_k'] = stoch.iloc[:, 0]
        df['stoch_d'] = stoch.iloc[:, 1]
    else:
        df['stoch_k'] = df['stoch_d'] = 50

    macd_df = ta.macd(df['close'], fast=12, slow=26, signal=9)
    if macd_df is not None and not macd_df.empty:
        df['macd'] = macd_df.iloc[:, 0]
        df['sig']  = macd_df.iloc[:, 1]
        df['hist'] = macd_df.iloc[:, 2]
    else:
        df['macd'] = df['sig'] = df['hist'] = 0

    # Volatility
    df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
    bb = ta.bbands(df['close'], length=20, std=2)
    if bb is not None and not bb.empty:
        df['bb_u'] = bb.iloc[:, 0]; df['bb_m'] = bb.iloc[:, 1]; df['bb_l'] = bb.iloc[:, 2]
        df['bb_width'] = (df['bb_u'] - df['bb_l']) / df['bb_m']
    else:
        df['bb_u'] = df['bb_m'] = df['bb_l'] = df['close']
        df['bb_width'] = 0

    # Regime — ADX
    adx_df = ta.adx(df['high'], df['low'], df['close'], length=14)
    if adx_df is not None and not adx_df.empty:
        df['adx'] = adx_df.iloc[:, 0]
        df['dmp'] = adx_df.iloc[:, 1]   # +DI
        df['dmn'] = adx_df.iloc[:, 2]   # -DI
    else:
        df['adx'] = df['dmp'] = df['dmn'] = 20

    # Volume
    df['vol_ma20'] = df['volume'].rolling(20).mean()
    df['vol_ratio'] = df['volume'] / df['vol_ma20'].replace(0, np.nan)

    return df

# ─────────────────────────────────────────────
# REGIME DETECTION
# ─────────────────────────────────────────────
def detect_regime(df):
    """Returns: 'trending' | 'ranging' | 'transition', adx_val"""
    adx = sf(df['adx'].iloc[-1])
    dmp = sf(df['dmp'].iloc[-1])
    dmn = sf(df['dmn'].iloc[-1])
    if adx > 25:
        direction = "bullish" if dmp > dmn else "bearish"
        return "trending", adx, direction
    elif adx < 20:
        return "ranging", adx, "neutral"
    else:
        return "transition", adx, "neutral"

# ─────────────────────────────────────────────
# VOLUME DIRECTION (FIX UTAMA)
# ─────────────────────────────────────────────
def volume_score(df):
    """
    Volume harus dikaitkan dengan arah candle.
    Surge bullish vs surge bearish = berbeda signifikan.
    """
    last = df.iloc[-1]
    vr   = sf(last['vol_ratio'], 1.0)
    cl   = sf(last['close'])
    op   = sf(last['open'])
    is_green = cl >= op

    if vr >= 2.0:
        label = f"{vr:.1f}x 🔥🔥"
        if is_green:   return 25, label, "surge_bull"
        else:          return -20, label, "surge_bear"   # distribusi — bahaya
    elif vr >= 1.5:
        label = f"{vr:.1f}x 🔥"
        if is_green:   return 18, label, "bull"
        else:          return -10, label, "bear"
    elif vr >= 1.0:
        label = f"{vr:.1f}x"
        if is_green:   return 8, label, "mild_bull"
        else:          return 0, label, "mild_bear"
    else:
        label = f"{vr:.1f}x"
        return 2, label, "weak"

# ─────────────────────────────────────────────
# RSI DIVERGENCE (sederhana)
# ─────────────────────────────────────────────
def detect_rsi_divergence(df, lookback=14):
    if len(df) < lookback + 2: return "none"
    prices = df['close'].values[-lookback:]
    rsis   = df['rsi'].values[-lookback:]
    # Cari swing low dalam window
    price_lows = [(i, prices[i]) for i in range(1, len(prices)-1)
                  if prices[i] < prices[i-1] and prices[i] < prices[i+1]]
    if len(price_lows) < 2: return "none"
    p1, p2 = price_lows[-2], price_lows[-1]
    r1, r2 = rsis[p1[0]], rsis[p2[0]]
    if p2[1] < p1[1] and r2 > r1 + 3:   return "bullish"   # harga LL, RSI HL
    if p2[1] > p1[1] and r2 < r1 - 3:   return "bearish"
    return "none"

# ─────────────────────────────────────────────
# CANDLESTICK PATTERNS
# ─────────────────────────────────────────────
def detect_patterns(df):
    if len(df) < 3: return ["—"]
    patterns = []
    o,h,l,c = df['open'].values, df['high'].values, df['low'].values, df['close'].values
    i = -1
    body = abs(c[i]-o[i]); rng = h[i]-l[i]
    uw = h[i]-max(c[i],o[i]); lw = min(c[i],o[i])-l[i]
    if rng > 0:
        if lw >= 2*body and uw <= 0.3*body:          patterns.append("🔨 Hammer")
        if uw >= 2*body and lw <= 0.3*body:           patterns.append("⬆️ Shooting Star")
        if body/rng < 0.1:                            patterns.append("✳️ Doji")
        if body/rng > 0.85:
            patterns.append("💪 Bull Marubozu" if c[i]>o[i] else "👇 Bear Marubozu")
    pb = abs(c[-2]-o[-2])
    if c[-2]<o[-2] and c[i]>o[i] and body>pb:        patterns.append("🟢 Bull Engulfing")
    if c[-2]>o[-2] and c[i]<o[i] and body>pb:        patterns.append("🔴 Bear Engulfing")
    if len(df)>=3:
        if c[-3]<o[-3] and abs(c[-2]-o[-2])<0.003*c[-2] and c[i]>o[i]: patterns.append("🌅 Morning Star")
        if c[-3]>o[-3] and abs(c[-2]-o[-2])<0.003*c[-2] and c[i]<o[i]: patterns.append("🌇 Evening Star")
    return patterns or ["—"]

# ─────────────────────────────────────────────
# WEIGHTED SCORING — REGIME AWARE
# ─────────────────────────────────────────────
def score_ticker(df):
    """
    Bobot dinamis berdasarkan market regime.
    Trending : Trend 40% | Volume 25% | Momentum 25% | Pattern 10%
    Ranging  : Trend 15% | Volume 20% | Momentum 45% | Pattern 20%
    Transition: 25/30/30/15
    """
    if df is None or df.empty or len(df) < 52:
        return 0, {}, "ranging", 0

    last   = df.iloc[-1]
    cl     = sf(last['close'])
    op     = sf(last['open'])
    e20    = sf(last['ema20'])
    e50    = sf(last['ema50'])
    e200   = sf(last['ema200'])
    rsi    = sf(last['rsi'])
    macd   = sf(last['macd'])
    sig    = sf(last['sig'])
    hist   = sf(last['hist'])
    hist_p = sf(df['hist'].iloc[-2]) if len(df) > 2 else 0
    stk    = sf(last['stoch_k'])
    std_d  = sf(last['stoch_d'])
    bb_l   = sf(last['bb_l'])
    bb_m   = sf(last['bb_m'])
    bb_u   = sf(last['bb_u'])
    bb_w   = sf(last['bb_width'])
    adx_v  = sf(last['adx'])
    dmp    = sf(last['dmp'])
    dmn    = sf(last['dmn'])

    regime, adx_val, direction = detect_regime(df)

    # ── TREND SCORE (raw 0–100) ──────────────────
    t = 0
    # EMA alignment
    if cl > e20:             t += 20
    if cl > e50:             t += 15
    if e20 > e50:            t += 15   # golden cross zone
    if e50 > e200 and e200 > 0: t += 10  # full bull alignment
    # ADX strength bonus
    if adx_v > 30 and dmp > dmn: t += 20
    elif adx_v > 25 and dmp > dmn: t += 10
    # EMA slope (2 candle)
    if len(df) > 3:
        ema20_slope = sf(df['ema20'].iloc[-1]) - sf(df['ema20'].iloc[-3])
        if ema20_slope > 0: t += 10
        elif ema20_slope < 0: t -= 10
    t = max(0, min(t, 100))

    # ── MOMENTUM SCORE (raw 0–100) ───────────────
    m = 0
    # RSI — context aware
    if regime == "trending":
        if 50 <= rsi <= 70:  m += 30
        elif 40 <= rsi < 50: m += 15
        elif rsi > 70:       m += 5    # overbought di trending masih ok
    else:
        if 30 <= rsi <= 45:  m += 35   # oversold di ranging = entry terbaik
        elif 45 < rsi <= 55: m += 15
        elif rsi > 70:       m -= 10   # overbought di ranging = bahaya
    # MACD
    if macd > sig:           m += 20
    if hist > 0 and hist > hist_p: m += 15   # histogram expanding
    # Stochastic (lebih relevan di ranging)
    if stk < 20 and stk > std_d:   m += 20   # stoch oversold cross
    elif stk < 40 and stk > std_d: m += 10
    # RSI Divergence
    div = detect_rsi_divergence(df)
    if div == "bullish":     m += 20
    elif div == "bearish":   m -= 15
    m = max(0, min(m, 100))

    # ── VOLUME SCORE (raw) ───────────────────────
    vs_raw, vol_label, vol_type = volume_score(df)
    v = max(0, min(vs_raw + 50, 100))   # normalize ke 0-100

    # ── PATTERN SCORE (raw 0–100) ────────────────
    pats = detect_patterns(df)
    p = 0
    for pat in pats:
        if any(k in pat for k in ['Bull Engulfing','Morning Star','Bull Marubozu','Hammer']): p = 80; break
        elif 'Doji' in pat: p = max(p, 40)
        elif any(k in pat for k in ['Bear Engulfing','Evening Star','Bear Marubozu']): p = max(p, 10)
    if p == 0: p = 30   # neutral

    # ── BB ZONE BONUS ────────────────────────────
    bb_bonus = 0
    if cl <= bb_l * 1.005:   bb_bonus = 15   # di bawah BB lower = potential reversal
    elif cl <= bb_m:          bb_bonus = 8
    if bb_w < 0.03:           bb_bonus += 10  # BB squeeze = breakout imminent

    # ── REGIME WEIGHTS ───────────────────────────
    if regime == "trending":
        weights = {"trend": 0.40, "momentum": 0.25, "volume": 0.25, "pattern": 0.10}
    elif regime == "ranging":
        weights = {"trend": 0.15, "momentum": 0.45, "volume": 0.20, "pattern": 0.20}
    else:  # transition
        weights = {"trend": 0.25, "momentum": 0.30, "volume": 0.30, "pattern": 0.15}

    raw = (t * weights["trend"] +
           m * weights["momentum"] +
           v * weights["volume"] +
           p * weights["pattern"])

    score = min(int(raw + bb_bonus), 100)

    detail = {
        "Regime": f"{regime.title()} (ADX {adx_val:.0f})",
        "Trend": f"{t}/100",
        "Momentum": f"{m}/100",
        "Volume": f"{v}/100 [{vol_label}]",
        "Pattern": f"{p}/100",
        "BB Bonus": bb_bonus,
        "Weights": weights,
        "RSI Div": div,
        "Vol Type": vol_type,
    }
    return score, detail, regime, adx_val

# ─────────────────────────────────────────────
# TECHNICAL LEVELS — ENTRY / SL / TP
# ─────────────────────────────────────────────
def get_levels(df, score, regime):
    if df is None or len(df) < 20: return None, None, None, None, "—", "#888"

    last  = df.iloc[-1]
    cl    = sf(last['close'])
    e20   = sf(last['ema20'])
    atr   = sf(last['atr'])
    bb_l  = sf(last['bb_l'])
    bb_m  = sf(last['bb_m'])

    # Pivot
    hv, lv, cv = sf(last['high']), sf(last['low']), cl
    pivot = (hv + lv + cv) / 3
    r1 = 2*pivot - lv;  r2 = pivot + (hv - lv)
    s1 = 2*pivot - hv;  s2 = pivot - (hv - lv)

    # Support/resistance dari rolling
    highs = df['high'].rolling(10, center=True).max().dropna()
    lows  = df['low'].rolling(10, center=True).min().dropna()
    res_levels = sorted(highs.unique(), reverse=True)
    sup_levels = sorted(lows.unique())

    # Entry
    if cl > e20:
        entry_base = max(e20, bb_m) if regime == "trending" else max(bb_l, s1)
        entry = min(cl, max(entry_base, cl * 0.985))
    else:
        sup_cands = [s for s in sup_levels[:3] if 0 < s < cl] + [s1, s2, bb_l]
        valid_sup = [s for s in sup_cands if 0 < s < cl]
        entry = max(valid_sup) if valid_sup else cl * 0.98

    entry = max(entry, cl * 0.97)
    entry = round(entry)

    # SL — di bawah support terkuat
    swing_low = df['low'].iloc[-5:].min()
    sl_cands = [swing_low * 0.99, s1 * 0.99, bb_l * 0.98]
    sl_cands = [s for s in sl_cands if 0 < s < entry]
    sl = max(sl_cands) if sl_cands else entry - max(atr * 1.5, entry * 0.02)
    sl = max(sl, entry * 0.94)
    sl = round(sl)

    # TP — ke resistance terdekat
    risk = max(entry - sl, entry * 0.005)
    res_cands = [r for r in res_levels[:3] if r > entry] + [r1, r2]
    valid_res = [r for r in res_cands if r > entry]
    tp = min(valid_res) if valid_res else entry + risk * 2.5
    if (tp - entry) < risk * 1.8:
        tp = entry + risk * 2.5
    tp = round(tp)
    rr = round((tp - entry) / (entry - sl), 2) if (entry - sl) > 0 else 0

    # Signal
    if score >= 70 and cl > e20:
        signal, color = "⚡ STRONG BUY", "#00ff99"
    elif score >= 55 and cl >= e20 * 0.99:
        signal, color = "✅ BUY", "#44dd88"
    elif score >= 42:
        signal, color = "🔄 WATCH", "#ffcc00"
    else:
        signal, color = "❌ AVOID", "#ff4466"

    return entry, sl, tp, rr, signal, color

# ─────────────────────────────────────────────
# SCANNER — single ticker worker
# ─────────────────────────────────────────────
def scan_one(args):
    (ticker, min_score, sig_filter, above_ema,
     min_vr, req_surge, req_macd, min_rsi, max_rsi) = args
    name = ticker.replace(".JK", "")
    try:
        df = fetch_df(ticker, "6mo")
        if df is None: return None, name, "Data kosong"

        last = df.iloc[-1]
        rsi_v = sf(last.get('rsi', 50))
        cl_v  = sf(last.get('close', 0))
        e20_v = sf(last.get('ema20', cl_v))
        macd_v = sf(last.get('macd', 0))
        sig_v  = sf(last.get('sig', 0))
        vr_v   = sf(last.get('vol_ratio', 1.0))

        if not (min_rsi <= rsi_v <= max_rsi):   return None, name, f"RSI {rsi_v:.0f}"
        if above_ema and cl_v < e20_v:           return None, name, "< EMA20"
        if req_macd and macd_v <= sig_v:         return None, name, "MACD bearish"
        if vr_v < min_vr:                        return None, name, f"Vol {vr_v:.1f}x"

        score, detail, regime, adx_v = score_ticker(df)
        if score < min_score:                    return None, name, f"Score {score}"

        entry, sl, tp, rr, signal, _ = get_levels(df, score, regime)
        if entry is None:                        return None, name, "Level error"

        if "AVOID" in signal:                    return None, name, "Signal AVOID"
        if sig_filter == "Strong BUY" and "STRONG" not in signal: return None, name, "Bukan Strong BUY"
        if sig_filter == "BUY saja" and "BUY" not in signal:      return None, name, "Bukan BUY"

        _, vol_lbl, vol_type = volume_score(df)
        if req_surge and "surge" not in vol_type: return None, name, "Bukan surge"

        div = detail.get("RSI Div", "none")
        pats = detect_patterns(df)

        return {
            "Ticker":  name,
            "Score":   score,
            "Regime":  regime.title(),
            "ADX":     round(adx_v, 1),
            "Signal":  signal,
            "Entry":   int(entry),
            "SL":      int(sl),
            "TP":      int(tp),
            "R:R":     f"1:{rr}",
            "RSI":     round(rsi_v, 1),
            "Vol":     vol_lbl,
            "VolType": vol_type,
            "MACD":    "✅" if macd_v > sig_v else "❌",
            "Div":     "🔼" if div=="bullish" else ("🔽" if div=="bearish" else "—"),
            "Pattern": pats[0] if pats else "—",
        }, name, None

    except Exception as e:
        return None, name, f"Err: {e}"

# ─────────────────────────────────────────────
# TRACKER I/O
# ─────────────────────────────────────────────
def load_log():
    if TRACKER.exists():
        with open(TRACKER) as f: return json.load(f)
    return []

def save_log(logs):
    with open(TRACKER, "w") as f: json.dump(logs, f, indent=2, default=str)

def save_scan_to_log(df_res, hold_days):
    today = datetime.now(TZ_JKT).strftime("%Y-%m-%d")
    logs = load_log()
    existing = {(e["date"], e["ticker"]) for e in logs}
    n = 0
    for _, row in df_res.iterrows():
        key = (today, row["Ticker"])
        if key in existing: continue
        logs.append({
            "id": f"{today}_{row['Ticker']}", "date": today, "ticker": row["Ticker"],
            "signal": row["Signal"], "score": int(row["Score"]),
            "entry": float(row["Entry"]), "sl": float(row["SL"]), "tp": float(row["TP"]),
            "rr": str(row["R:R"]), "hold_days": hold_days,
            "exit_price": None, "exit_date": None, "status": "OPEN", "note": ""
        })
        n += 1
    save_log(logs)
    return n

def eval_trade(trade):
    ticker = trade["ticker"]
    entry, sl, tp = float(trade["entry"]), float(trade["sl"]), float(trade["tp"])
    tgt = date.fromisoformat(trade["date"])
    hold = trade.get("hold_days", 3)
    today = datetime.now(TZ_JKT).date()
    days = (today - tgt).days
    try:
        hist = clean_df(yf.download(jk(ticker), start=tgt - timedelta(days=1),
                                    end=today + timedelta(days=1), progress=False))
        hist = hist[hist.index.date >= tgt]
        if hist.empty: return "OPEN", entry, days, "Data kosong", 0
        hi, lo, last_c = hist['high'].max(), hist['low'].min(), sf(hist['close'].iloc[-1])
        if hi >= tp:   return "WIN",  tp,     days, "TP ✅", round((tp-entry)/entry*100, 2)
        if lo <= sl:   return "LOSS", sl,     days, "SL ❌", round((sl-entry)/entry*100, 2)
        if days >= hold:
            pnl = round((last_c-entry)/entry*100, 2)
            return ("WIN" if pnl >= 0 else "LOSS"), last_c, days, f"Force close D{hold}", pnl
        dist_tp = round((tp-last_c)/tp*100, 1)
        dist_sl = round((last_c-sl)/last_c*100, 1)
        action = "🚀 TP dekat" if dist_tp<=1.5 else ("⚠️ SL dekat" if dist_sl<=1.5 else "🟡 Hold")
        return "OPEN", last_c, days, action, round((last_c-entry)/entry*100, 2)
    except:
        return "OPEN", entry, days, "Gagal fetch", 0

def auto_resolve():
    logs = load_log(); updated = False
    for t in logs:
        if t["status"] != "OPEN": continue
        status, ep, days, note, pnl = eval_trade(t)
        if status != "OPEN":
            t.update({"status": status, "exit_price": ep,
                      "exit_date": str(datetime.now(TZ_JKT).date()), "note": note})
            updated = True
    if updated: save_log(logs)

def tracker_stats(logs):
    closed = [l for l in logs if l["status"] in ("WIN","LOSS")]
    wins   = [l for l in closed if l["status"] == "WIN"]
    pnls   = []
    for l in closed:
        if l.get("exit_price") and l.get("entry"):
            pnls.append((float(l["exit_price"]) - float(l["entry"])) / float(l["entry"]) * 100)
    return {
        "total": len(logs), "closed": len(closed), "open": len(logs) - len(closed),
        "wins": len(wins), "losses": len(closed) - len(wins),
        "win_rate": round(len(wins)/len(closed)*100, 1) if closed else 0,
        "avg_pnl": round(sum(pnls)/len(pnls), 2) if pnls else 0,
        "total_pnl": round(sum(pnls), 2) if pnls else 0,
    }

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
st.markdown("""
<h1 style='text-align:center; color:#00bbff; margin-bottom:4px; letter-spacing:2px;'>IDX TERMINAL v7</h1>
<p style='text-align:center; color:#445566; margin-bottom:1rem;'>
Regime-Aware Scoring &nbsp;·&nbsp; Volume Direction &nbsp;·&nbsp; RSI Divergence &nbsp;·&nbsp; Pre-Market IEP Check
</p>
""", unsafe_allow_html=True)

auto_resolve()

# ─────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Market Overview",
    "Smart Scanner",
    "Deep Analysis",
    "Pre-Market Check",
    "Win/Loss Tracker",
])

# ══════════════════════════════════════════════
# TAB 1 — MARKET OVERVIEW
# ══════════════════════════════════════════════
with tab1:
    col_ihsg, col_sector = st.columns([1, 1])

    with col_ihsg:
        st.subheader("IHSG — Market Pulse")
        raw = clean_df(yf.download("^JKSE", period="1y", progress=False))
        ihsg_change = 0.0
        if not raw.empty:
            ihsg_change = (raw['close'].iloc[-1] - raw['close'].iloc[-2]) / raw['close'].iloc[-2] * 100
            raw['ma20'] = raw['close'].rolling(20).mean()
            raw['ma50'] = raw['close'].rolling(50).mean()

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=raw.index, y=raw['close'],
                                     fill='tozeroy', fillcolor='rgba(0,187,255,0.08)',
                                     line=dict(color='#00bbff', width=1.5), name="IHSG"))
            fig.add_trace(go.Scatter(x=raw.index, y=raw['ma20'],
                                     line=dict(color='orange', width=1, dash='dot'), name="MA20"))
            fig.add_trace(go.Scatter(x=raw.index, y=raw['ma50'],
                                     line=dict(color='#ff88aa', width=1, dash='dot'), name="MA50"))
            fig.update_layout(height=250, template='plotly_dark',
                              margin=dict(l=0,r=0,t=0,b=0), showlegend=False,
                              xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

            ca, cb, cc, cd = st.columns(4)
            ca.metric("Last",    f"{raw['close'].iloc[-1]:,.0f}")
            cb.metric("Change",  f"{ihsg_change:+.2f}%",
                      delta_color="normal" if ihsg_change >= 0 else "inverse")
            cc.metric("52W High", f"{raw['high'].max():,.0f}")
            cd.metric("52W Low",  f"{raw['low'].min():,.0f}")

            bias = "🟢 BULLISH" if ihsg_change > 0.3 else ("🔴 BEARISH" if ihsg_change < -0.3 else "🟡 SIDEWAYS")
            st.caption(f"Market Bias hari ini: **{bias}**")

    with col_sector:
        st.subheader("Sectoral Heatmap — 5D")
        sec_data = []
        for s, proxy in SECTOR_PROXY.items():
            try:
                d = clean_df(yf.download(jk(proxy), period="10d", progress=False))
                if not d.empty and len(d) >= 5:
                    perf = (d['close'].iloc[-1] - d['close'].iloc[-5]) / d['close'].iloc[-5] * 100
                    sec_data.append({"Sektor": s, "Perf": round(sf(perf), 2), "Parent": "IDX", "Size": 10})
            except: continue

        if sec_data:
            df_s = pd.DataFrame(sec_data)
            fig  = px.treemap(df_s, path=['Parent','Sektor'], values='Size',
                              color='Perf', color_continuous_scale='RdYlGn', range_color=[-3,3])
            fig.update_layout(height=250, margin=dict(l=0,r=0,t=0,b=0), template='plotly_dark')
            st.plotly_chart(fig, use_container_width=True)

            best  = max(sec_data, key=lambda x: x['Perf'])
            worst = min(sec_data, key=lambda x: x['Perf'])
            st.caption(f"🏆 Terkuat: **{best['Sektor']}** ({best['Perf']:+.2f}%) &nbsp;|&nbsp; ⚠️ Terlemah: **{worst['Sektor']}** ({worst['Perf']:+.2f}%)")

    st.divider()

    # Top movers hari ini
    st.subheader("Top Movers — LQ45 Hari Ini")
    mover_data = []
    prog_mv = st.progress(0)
    for i, t in enumerate(LQ45):
        try:
            d = clean_df(yf.download(jk(t), period="5d", progress=False))
            if not d.empty and len(d) >= 2:
                chg = (d['close'].iloc[-1] - d['close'].iloc[-2]) / d['close'].iloc[-2] * 100
                vol = sf(d['volume'].iloc[-1])
                mover_data.append({"Ticker": t, "Change%": round(sf(chg), 2), "Volume": int(vol),
                                   "Close": int(sf(d['close'].iloc[-1]))})
        except: pass
        prog_mv.progress((i+1) / len(LQ45))
    prog_mv.empty()

    if mover_data:
        df_mv = pd.DataFrame(mover_data).sort_values("Change%", ascending=False)
        top_gain = df_mv.head(5)
        top_loss = df_mv.tail(5)
        cg, cl_col = st.columns(2)
        with cg:
            st.markdown("**📈 Gainers**")
            st.dataframe(top_gain[["Ticker","Change%","Close","Volume"]],
                         use_container_width=True, hide_index=True)
        with cl_col:
            st.markdown("**📉 Losers**")
            st.dataframe(top_loss.sort_values("Change%")[["Ticker","Change%","Close","Volume"]],
                         use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════
# TAB 2 — SMART SCANNER
# ══════════════════════════════════════════════
with tab2:
    st.subheader("Smart Scanner — Rekomendasi Harian")

    sc1, sc2, sc3 = st.columns([2, 1, 1])
    with sc1:
        idx_choice = st.selectbox("Universe:", list(UNIVERSES.keys()))
    with sc2:
        top_n = st.number_input("Top N:", 5, 30, 10)
    with sc3:
        hold_period = st.radio("Hold:", [1, 3], index=1, horizontal=True)

    extra_sec = st.multiselect("Tambah sektor spesifik:", list(SECTORS.keys()))

    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        min_score   = st.slider("Min Score:", 0, 100, 55)
        sig_filter  = st.selectbox("Filter Signal:", ["Semua BUY", "Strong BUY", "BUY saja"])
    with col_f2:
        min_rsi  = st.slider("RSI Min:", 10, 60, 30)
        max_rsi  = st.slider("RSI Max:", 50, 90, 72)
    with col_f3:
        min_vr     = st.slider("Min Vol Ratio:", 0.5, 3.0, 1.0, 0.1)
        req_surge  = st.checkbox("Wajib Vol Surge")
    with col_f4:
        above_ema  = st.checkbox("Harga > EMA20", value=True)
        req_macd   = st.checkbox("Wajib MACD Bullish")

    universe = list(dict.fromkeys(
        UNIVERSES[idx_choice] +
        [t for s in extra_sec for t in SECTORS[s]]
    ))
    st.caption(f"Universe aktif: **{len(universe)} saham**")

    if st.button("🚀 MULAI SCAN", use_container_width=True, type="primary"):
        tickers = add_jk(universe)
        params  = (min_score, sig_filter, above_ema, min_vr, req_surge, req_macd, min_rsi, max_rsi)
        args    = [(t, *params) for t in tickers]

        prog  = st.progress(0)
        info  = st.empty()
        results = []; done = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
            futs = {ex.submit(scan_one, a): a[0] for a in args}
            for fut in concurrent.futures.as_completed(futs):
                done += 1
                prog.progress(done / len(tickers))
                info.markdown(f"⚡ {done}/{len(tickers)} | Kandidat: **{len(results)}**")
                res, name, reason = fut.result()
                if res: results.append(res)

        prog.empty(); info.empty()

        if not results:
            st.warning("Tidak ada saham yang lolos filter. Coba turunkan min score.")
        else:
            df_res = pd.DataFrame(results).sort_values("Score", ascending=False).head(top_n)
            n_saved = save_scan_to_log(df_res, hold_period)
            if n_saved:
                st.success(f"💾 {n_saved} rekomendasi disimpan ke tracker.")

            st.markdown(f"### Top {len(df_res)} Rekomendasi — {datetime.now(TZ_JKT).strftime('%d %b %Y %H:%M')} WIB")

            # Tabel ringkas
            show_cols = ["Ticker","Score","Regime","Signal","Entry","SL","TP","R:R","RSI","Vol","MACD","Div","Pattern"]
            st.dataframe(df_res[show_cols], use_container_width=True, hide_index=True)

            # Detail cards
            st.markdown("---")
            st.markdown("#### Detail & Reasoning")
            for _, row in df_res.iterrows():
                score_c = "#00ff99" if row['Score']>=70 else ("#ffcc00" if row['Score']>=55 else "#ff4466")
                regime_badge = (f"<span class='regime-trend'>{row['Regime']}</span>" if row['Regime']=="Trending"
                                else f"<span class='regime-range'>{row['Regime']}</span>" if row['Regime']=="Ranging"
                                else f"<span class='regime-transit'>{row['Regime']}</span>")
                sig_class = "tag-sbuy" if "STRONG" in row['Signal'] else ("tag-sell" if "AVOID" in row['Signal'] else "tag-buy")
                vol_warn = " ⚠️ <i>Volume distribusi — hati-hati!</i>" if row.get('VolType','') in ('surge_bear','bear') else ""
                div_note = " | 🔼 <b>RSI Bullish Divergence!</b>" if row['Div']=="🔼" else ""

                st.markdown(f"""
                <div class='reco-card'>
                    <div style='display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:8px'>
                        <div>
                            <span style='font-size:22px; font-weight:900; color:#00bbff'>{row['Ticker']}</span>
                            &nbsp; <span class='{sig_class}'>{row['Signal']}</span>
                            &nbsp; {regime_badge}
                            <div style='font-size:30px; font-weight:900; color:{score_c}; line-height:1.2'>{row['Score']}<span style='font-size:14px; color:#667'>/100</span></div>
                        </div>
                        <div style='font-size:13px; color:#aac; text-align:right'>
                            <b>Entry:</b> {row['Entry']:,} &nbsp; <b>SL:</b> {row['SL']:,} &nbsp; <b>TP:</b> {row['TP']:,} &nbsp; <b>R:R</b> {row['R:R']}<br>
                            <b>RSI:</b> {row['RSI']} &nbsp; <b>ADX:</b> {row['ADX']} &nbsp; <b>MACD:</b> {row['MACD']} &nbsp; <b>Vol:</b> {row['Vol']}<br>
                            <b>Pola:</b> {row['Pattern']} &nbsp; <b>Divergence:</b> {row['Div']}<br>
                            {vol_warn}{div_note}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # Score bar chart
            fig_bar = go.Figure()
            fig_bar.add_trace(go.Bar(
                x=df_res['Ticker'], y=df_res['Score'],
                marker_color=['#00ff99' if s>=70 else ('#ffcc00' if s>=55 else '#ff4466') for s in df_res['Score']],
                text=df_res['Score'], textposition='outside'
            ))
            fig_bar.add_hline(y=70, line_dash="dot", line_color="#00ff99", annotation_text="Strong Buy ≥70")
            fig_bar.add_hline(y=55, line_dash="dot", line_color="#ffcc00", annotation_text="Buy ≥55")
            fig_bar.update_layout(height=280, template='plotly_dark',
                                  title="Distribusi Score", margin=dict(l=0,r=0,t=30,b=0))
            st.plotly_chart(fig_bar, use_container_width=True)

# ══════════════════════════════════════════════
# TAB 3 — DEEP ANALYSIS
# ══════════════════════════════════════════════
with tab3:
    st.subheader("Deep Analysis — Single Ticker")

    da1, da2, da3 = st.columns([1, 2, 1])
    with da1:
        ticker_input = st.text_input("Kode Saham:", "BBRI").upper()
    with da2:
        sector_sel = st.selectbox("Atau pilih dari sektor:", ["—"] + list(SECTORS.keys()))
    with da3:
        tf = st.selectbox("Timeframe:", ["3mo","6mo","1y","2y"], index=2)

    target = None
    if ticker_input:
        target = jk(ticker_input)
    if sector_sel != "—":
        pick = st.selectbox("Saham:", add_jk(SECTORS[sector_sel]))
        target = pick

    if target and st.button("🔍 Analisis", type="primary"):
        with st.spinner(f"Menganalisis {target}..."):
            df = fetch_df(target, period=tf)

        if df is None:
            st.error("Data tidak cukup. Coba timeframe lebih panjang.")
        else:
            score, detail, regime, adx_v = score_ticker(df)
            entry, sl, tp, rr, signal, sig_col = get_levels(df, score, regime)
            last  = df.iloc[-1]
            cl    = sf(last['close']); rsi = sf(last['rsi'])
            e20   = sf(last['ema20']); e50 = sf(last['ema50'])
            adx   = sf(last['adx'])
            pats  = detect_patterns(df)
            _, vol_lbl, vol_type = volume_score(df)
            div   = detect_rsi_divergence(df)

            # Regime badge
            if regime == "trending":
                rbadge = f"<span class='regime-trend'>📈 TRENDING (ADX {adx:.0f})</span>"
            elif regime == "ranging":
                rbadge = f"<span class='regime-range'>↔️ RANGING (ADX {adx:.0f})</span>"
            else:
                rbadge = f"<span class='regime-transit'>🔄 TRANSITION (ADX {adx:.0f})</span>"

            # Metrics row
            m1, m2, m3, m4, m5, m6 = st.columns(6)
            m1.metric("Score",  f"{score}/100")
            m2.metric("Signal", signal)
            m3.metric("RSI",    f"{rsi:.1f}")
            m4.metric("ADX",    f"{adx:.1f}")
            m5.metric("Volume", vol_lbl)
            m6.metric("Close",  f"{cl:,.0f}")

            st.markdown(rbadge, unsafe_allow_html=True)
            if div == "bullish":
                st.success("🔼 RSI Bullish Divergence terdeteksi! Potential reversal kuat.")
            elif div == "bearish":
                st.warning("🔽 RSI Bearish Divergence — hati-hati potensi turun.")
            if vol_type in ("surge_bear", "bear"):
                st.error("⚠️ Volume surge tapi candle merah — distribusi institusi, hati-hati!")

            # Trade plan box
            if entry:
                st.markdown(f"""
                <div style='background:#0a1428; border-radius:10px; padding:16px; margin:12px 0;
                            border-left:4px solid {sig_col}'>
                    <div style='font-size:18px; font-weight:700; color:{sig_col}; margin-bottom:8px'>{signal}</div>
                    <table style='width:100%; font-size:14px; color:#ccd'>
                        <tr><td style='padding:4px 0; color:#889'>💡 Entry</td>
                            <td><b>Rp {entry:,}</b></td>
                            <td style='color:#889'>📐 Regime</td>
                            <td><b>{regime.title()} | ADX {adx:.0f}</b></td></tr>
                        <tr><td style='color:#889'>🛑 Stop Loss</td>
                            <td><b style='color:#ff4466'>Rp {sl:,}</b> ({(entry-sl)/entry*100:.1f}%)</td>
                            <td style='color:#889'>📊 RSI Div</td>
                            <td><b>{"🔼 Bullish" if div=="bullish" else ("🔽 Bearish" if div=="bearish" else "—")}</b></td></tr>
                        <tr><td style='color:#889'>🎯 Take Profit</td>
                            <td><b style='color:#00ff99'>Rp {tp:,}</b> (+{(tp-entry)/entry*100:.1f}%)</td>
                            <td style='color:#889'>⚖️ Risk/Reward</td>
                            <td><b>1:{rr}</b></td></tr>
                        <tr><td style='color:#889'>🕯 Pola</td>
                            <td colspan=3><b>{pats[0] if pats else "—"}</b></td></tr>
                    </table>
                </div>
                """, unsafe_allow_html=True)

            # Score breakdown
            with st.expander("📐 Score Breakdown"):
                st.json(detail)

            # Chart
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                                row_heights=[0.55, 0.25, 0.20],
                                subplot_titles=["Harga", "RSI + ADX", "Volume"])
            # Candles
            fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'],
                                          low=df['low'], close=df['close'],
                                          increasing_line_color='#00ff99',
                                          decreasing_line_color='#ff4466',
                                          name="OHLC"), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['ema20'],
                                     line=dict(color='orange', width=1.2), name="EMA20"), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['ema50'],
                                     line=dict(color='#8888ff', width=1.2), name="EMA50"), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['bb_u'],
                                     line=dict(color='#336699', width=0.8, dash='dot'), name="BB Upper"), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['bb_l'],
                                     line=dict(color='#336699', width=0.8, dash='dot'),
                                     fill='tonexty', fillcolor='rgba(51,102,153,0.05)', name="BB Lower"), row=1, col=1)
            if entry:
                fig.add_hline(y=sl,    line_dash="dash", line_color="#ff4466",
                              annotation_text=f"SL {sl:,}", row=1, col=1)
                fig.add_hline(y=tp,    line_dash="dash", line_color="#00ff99",
                              annotation_text=f"TP {tp:,}", row=1, col=1)
                fig.add_hline(y=entry, line_dash="dot",  line_color="#ffcc00",
                              annotation_text=f"Entry {entry:,}", row=1, col=1)
            # RSI
            fig.add_trace(go.Scatter(x=df.index, y=df['rsi'],
                                     line=dict(color='#bb77ff', width=1.5), name="RSI"), row=2, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['adx'],
                                     line=dict(color='#ffaa33', width=1.2, dash='dot'), name="ADX"), row=2, col=1)
            fig.add_hline(y=70, line_dash="dot", line_color="red",   row=2, col=1)
            fig.add_hline(y=30, line_dash="dot", line_color="green", row=2, col=1)
            fig.add_hline(y=25, line_dash="dot", line_color="#ffaa33", annotation_text="ADX 25", row=2, col=1)
            # Volume
            colors_vol = ['#00ff99' if c >= o else '#ff4466'
                          for c, o in zip(df['close'], df['open'])]
            fig.add_trace(go.Bar(x=df.index, y=df['volume'],
                                 marker_color=colors_vol, name="Volume"), row=3, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['vol_ma20'],
                                     line=dict(color='yellow', width=1), name="Vol MA20"), row=3, col=1)

            fig.update_layout(height=620, template='plotly_dark',
                              xaxis_rangeslider_visible=False,
                              margin=dict(l=0,r=0,t=30,b=0), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════
# TAB 4 — PRE-MARKET CHECK
# ══════════════════════════════════════════════
with tab4:
    st.subheader("Pre-Market Check — IEP Adjustment")
    st.caption("Masukkan IEP (Indicative Equilibrium Price) dari Ajaib sebelum market buka. "
               "Sistem akan recalculate entry, SL, TP, dan beri keputusan GO / SKIP / WAIT.")

    st.divider()

    # ── Load watchlist dari hasil scanner (open trades) ──
    logs_pm   = load_log()
    open_pm   = [l for l in logs_pm if l["status"] == "OPEN"]
    scan_date = datetime.now(TZ_JKT).strftime("%Y-%m-%d")
    today_pm  = [l for l in open_pm if l["date"] == scan_date]

    # Biarkan user juga input manual ticker tambahan
    st.markdown("#### Watchlist")
    col_wl1, col_wl2 = st.columns([3, 1])
    with col_wl1:
        manual_tickers = st.text_input(
            "Tambah ticker manual (pisahkan koma):",
            placeholder="BBRI, TLKM, GOTO"
        )
    with col_wl2:
        ihsg_open = st.number_input("IHSG Open estimasi:", value=0, step=10,
                                    help="Isi kalau sudah ada IEP IHSG futures / pre-opening")

    # Gabungkan dari tracker hari ini + manual input
    base_rows = []
    for t in today_pm:
        base_rows.append({
            "ticker":  t["ticker"],
            "entry":   float(t["entry"]),
            "sl":      float(t["sl"]),
            "tp":      float(t["tp"]),
            "score":   t.get("score", 0),
            "signal":  t.get("signal", "—"),
            "from":    "Scanner",
        })

    if manual_tickers:
        for raw_t in manual_tickers.split(","):
            t_clean = raw_t.strip().upper()
            if not t_clean: continue
            # Fetch data untuk hitung baseline level
            df_pm = fetch_df(jk(t_clean), "6mo")
            if df_pm is not None:
                sc_pm, _, reg_pm, _ = score_ticker(df_pm)
                e_pm, sl_pm, tp_pm, _, sig_pm, _ = get_levels(df_pm, sc_pm, reg_pm)
                if e_pm:
                    base_rows.append({
                        "ticker": t_clean,
                        "entry":  float(e_pm),
                        "sl":     float(sl_pm),
                        "tp":     float(tp_pm),
                        "score":  sc_pm,
                        "signal": sig_pm,
                        "from":   "Manual",
                    })
            else:
                base_rows.append({
                    "ticker": t_clean,
                    "entry":  0, "sl": 0, "tp": 0,
                    "score":  0, "signal": "—", "from": "Manual (no data)",
                })

    if not base_rows:
        st.info("Belum ada watchlist. Jalankan scanner dulu atau tambah ticker manual di atas.")
    else:
        st.divider()
        st.markdown("#### Input IEP per Saham")
        st.caption("Harga IEP terlihat di Ajaib pada fase Pre-Opening (08:45–09:00 WIB).")

        iep_inputs = {}
        prev_closes = {}

        # Fetch previous close untuk hitung gap
        for row in base_rows:
            try:
                d_prev = clean_df(yf.download(jk(row["ticker"]), period="5d", progress=False))
                prev_closes[row["ticker"]] = sf(d_prev['close'].iloc[-1]) if not d_prev.empty else row["entry"]
            except:
                prev_closes[row["ticker"]] = row["entry"]

        # Input grid
        cols_per_row = 3
        for i in range(0, len(base_rows), cols_per_row):
            chunk = base_rows[i:i+cols_per_row]
            cols  = st.columns(cols_per_row)
            for col, row in zip(cols, chunk):
                with col:
                    prev_c = prev_closes.get(row["ticker"], row["entry"])
                    iep_val = col.number_input(
                        f"{row['ticker']}  (close: {prev_c:,.0f})",
                        min_value=0,
                        value=int(prev_c),
                        step=1,
                        key=f"iep_{row['ticker']}"
                    )
                    iep_inputs[row["ticker"]] = iep_val

        st.divider()

        if st.button("Hitung Ulang dengan IEP", type="primary", use_container_width=True):

            st.markdown("#### Hasil Analisis Pre-Market")

            for row in base_rows:
                ticker  = row["ticker"]
                iep     = iep_inputs.get(ticker, 0)
                prev_c  = prev_closes.get(ticker, row["entry"])
                entry_o = row["entry"]   # entry dari analisis semalam
                sl_o    = row["sl"]
                tp_o    = row["tp"]

                if iep <= 0 or prev_c <= 0:
                    continue

                # ── Gap calculation ──────────────────────
                gap_pct  = (iep - prev_c) / prev_c * 100
                gap_type = ("gap_up"   if gap_pct >  1.0 else
                            "gap_down" if gap_pct < -1.0 else "flat")

                # ── Recalculate entry dari IEP ───────────
                # Entry baru = IEP itu sendiri (kita beli di harga buka)
                # tapi kalau gap up terlalu jauh, R:R bisa rusak
                new_entry = iep

                # SL: tetap proporsional dari entry baru
                original_sl_dist_pct = (entry_o - sl_o) / entry_o if entry_o > 0 else 0.02
                new_sl = round(new_entry * (1 - original_sl_dist_pct))

                # TP: tetap di level resistance lama KECUALI sudah terlewat
                if tp_o > new_entry:
                    new_tp = tp_o   # resistance masih valid
                else:
                    # TP terlewat karena gap up terlalu jauh, hitung ulang
                    new_tp = round(new_entry + (new_entry - new_sl) * 2.0)

                new_risk   = new_entry - new_sl
                new_reward = new_tp - new_entry
                new_rr     = round(new_reward / new_risk, 2) if new_risk > 0 else 0

                # ── Decision logic ───────────────────────
                if gap_type == "gap_up":
                    if gap_pct > 5:
                        decision = "SKIP"
                        reason   = f"Gap up {gap_pct:+.1f}% terlalu jauh. Setup rusak, R:R tidak layak."
                        dec_color = "#ff4466"
                    elif new_rr >= 1.5:
                        decision = "GO"
                        reason   = f"Gap up {gap_pct:+.1f}% wajar. R:R masih {new_rr} — layak entry di harga buka."
                        dec_color = "#00ff99"
                    else:
                        decision = "WAIT"
                        reason   = f"Gap up {gap_pct:+.1f}% memperburuk R:R jadi {new_rr}. Tunggu pullback ke {int(entry_o):,}."
                        dec_color = "#ffcc00"

                elif gap_type == "gap_down":
                    if gap_pct < -5:
                        decision = "SKIP"
                        reason   = f"Gap down {gap_pct:+.1f}%. Potensi panic sell lanjutan. Tunggu hari lain."
                        dec_color = "#ff4466"
                    elif gap_pct < -2:
                        decision = "WAIT"
                        reason   = f"Gap down {gap_pct:+.1f}%. Tunggu stabilisasi 15–30 menit pertama sebelum entry."
                        dec_color = "#ffcc00"
                    else:
                        decision = "GO"
                        reason   = f"Gap down minor {gap_pct:+.1f}%. Entry lebih murah dari plan. R:R membaik jadi {new_rr}."
                        dec_color = "#00ff99"

                else:  # flat open
                    if new_rr >= 1.5:
                        decision = "GO"
                        reason   = f"Open flat ({gap_pct:+.1f}%). Entry sesuai plan. R:R {new_rr}."
                        dec_color = "#00ff99"
                    else:
                        decision = "WAIT"
                        reason   = f"Open flat tapi R:R hanya {new_rr}. Entry lebih ideal di {int(entry_o):,}."
                        dec_color = "#ffcc00"

                # IHSG context
                ihsg_note = ""
                if ihsg_open > 0:
                    # fetch ihsg prev close
                    try:
                        ihsg_prev = clean_df(yf.download("^JKSE", period="5d", progress=False))
                        ihsg_prev_c = sf(ihsg_prev['close'].iloc[-1]) if not ihsg_prev.empty else 0
                        ihsg_gap = (ihsg_open - ihsg_prev_c) / ihsg_prev_c * 100 if ihsg_prev_c > 0 else 0
                        if ihsg_gap < -1.0:
                            ihsg_note = f"  IHSG diestimasi gap down {ihsg_gap:+.1f}% — pertimbangkan sizing lebih kecil."
                            if decision == "GO": decision = "WAIT"; dec_color = "#ffcc00"
                        elif ihsg_gap > 0.5:
                            ihsg_note = f"  IHSG gap up {ihsg_gap:+.1f}% — konfirmasi bullish market."
                    except: pass

                # ── Render card ──────────────────────────
                border_color = dec_color
                gap_label    = f"{gap_pct:+.1f}%"
                gap_color    = "#00ff99" if gap_pct >= 0 else "#ff4466"

                st.markdown(f"""
                <div style='background:#0a1020; border-radius:12px; border-left:5px solid {border_color};
                            padding:16px 20px; margin:10px 0;'>
                    <div style='display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:10px;'>
                        <div>
                            <span style='font-size:20px; font-weight:900; color:#00bbff;'>{ticker}</span>
                            &nbsp;&nbsp;
                            <span style='font-size:22px; font-weight:900; color:{dec_color};'>{decision}</span>
                        </div>
                        <div style='font-size:13px; color:#889;'>{row['from']} &nbsp;|&nbsp; Score: {row['score']}</div>
                    </div>
                    <div style='display:grid; grid-template-columns:repeat(4,1fr); gap:8px; font-size:13px; margin-bottom:10px;'>
                        <div style='background:#0d1628; border-radius:8px; padding:8px; text-align:center;'>
                            <div style='color:#667; font-size:11px; margin-bottom:2px;'>IEP</div>
                            <div style='font-weight:700; color:#fff;'>{iep:,}</div>
                        </div>
                        <div style='background:#0d1628; border-radius:8px; padding:8px; text-align:center;'>
                            <div style='color:#667; font-size:11px; margin-bottom:2px;'>Gap vs Close</div>
                            <div style='font-weight:700; color:{gap_color};'>{gap_label}</div>
                        </div>
                        <div style='background:#0d1628; border-radius:8px; padding:8px; text-align:center;'>
                            <div style='color:#667; font-size:11px; margin-bottom:2px;'>Entry (IEP)</div>
                            <div style='font-weight:700; color:#fff;'>{new_entry:,}</div>
                        </div>
                        <div style='background:#0d1628; border-radius:8px; padding:8px; text-align:center;'>
                            <div style='color:#667; font-size:11px; margin-bottom:2px;'>R:R Baru</div>
                            <div style='font-weight:700; color:{"#00ff99" if new_rr >= 2 else ("#ffcc00" if new_rr >= 1.5 else "#ff4466")};'>1:{new_rr}</div>
                        </div>
                    </div>
                    <div style='display:grid; grid-template-columns:repeat(3,1fr); gap:8px; font-size:13px; margin-bottom:10px;'>
                        <div style='background:#0d1628; border-radius:8px; padding:8px; text-align:center;'>
                            <div style='color:#667; font-size:11px; margin-bottom:2px;'>Entry Semalam</div>
                            <div style='font-weight:500; color:#aac;'>{int(entry_o):,}</div>
                        </div>
                        <div style='background:#0d1628; border-radius:8px; padding:8px; text-align:center;'>
                            <div style='color:#667; font-size:11px; margin-bottom:2px;'>Stop Loss</div>
                            <div style='font-weight:700; color:#ff4466;'>{new_sl:,}
                                <span style='font-size:11px;'>({(new_entry-new_sl)/new_entry*100:.1f}%)</span>
                            </div>
                        </div>
                        <div style='background:#0d1628; border-radius:8px; padding:8px; text-align:center;'>
                            <div style='color:#667; font-size:11px; margin-bottom:2px;'>Take Profit</div>
                            <div style='font-weight:700; color:#00ff99;'>{new_tp:,}
                                <span style='font-size:11px;'>(+{(new_tp-new_entry)/new_entry*100:.1f}%)</span>
                            </div>
                        </div>
                    </div>
                    <div style='font-size:13px; color:#ccd; background:#0d1628; border-radius:8px; padding:10px;'>
                        {reason}{ihsg_note}
                    </div>
                </div>
                """, unsafe_allow_html=True)

# ══════════════════════════════════════════════
# TAB 5 — WIN/LOSS TRACKER
# ══════════════════════════════════════════════
with tab5:
    st.subheader("Win/Loss Tracker")
    logs = load_log()

    if not logs:
        st.info("📭 Belum ada data. Jalankan scanner untuk menghasilkan rekomendasi.")
    else:
        stats = tracker_stats(logs)
        c1,c2,c3,c4,c5,c6 = st.columns(6)
        c1.metric("Win Rate",   f"{stats['win_rate']}%")
        c2.metric("✅ Menang",   stats['wins'])
        c3.metric("❌ Kalah",    stats['losses'])
        c4.metric("⏳ Open",     stats['open'])
        c5.metric("Avg P&L",    f"{stats['avg_pnl']:+.2f}%")
        c6.metric("Total P&L",  f"{stats['total_pnl']:+.2f}%")

        # Win rate chart
        if stats['closed'] > 0:
            fig_wr = go.Figure(go.Pie(
                values=[stats['wins'], stats['losses']],
                labels=["WIN","LOSS"],
                marker_colors=['#00ff99','#ff4466'],
                hole=0.6,
                textinfo='label+percent'
            ))
            fig_wr.update_layout(height=200, template='plotly_dark',
                                 margin=dict(l=0,r=0,t=0,b=0), showlegend=False)
            col_pie, col_empty = st.columns([1,2])
            with col_pie:
                st.plotly_chart(fig_wr, use_container_width=True)

        # Open trades
        open_trades = [l for l in logs if l["status"] == "OPEN"]
        if open_trades:
            st.markdown("#### Trade Aktif")
            for trade in open_trades:
                status, curr, days, action, pnl = eval_trade(trade)
                pnl_color = "#00ff99" if pnl >= 0 else "#ff4466"
                if status != "OPEN":
                    for t in logs:
                        if t["id"] == trade["id"]:
                            t.update({"status": status, "exit_price": curr,
                                      "exit_date": str(datetime.now(TZ_JKT).date())})
                    save_log(logs)
                    st.rerun()
                st.markdown(f"""
                <div class='trade-row'>
                    <b style='color:#00bbff'>{trade['ticker']}</b>
                    &nbsp;|&nbsp; Entry: <b>{float(trade['entry']):,.0f}</b>
                    &nbsp;|&nbsp; SL: <b style='color:#ff4466'>{float(trade['sl']):,.0f}</b>
                    &nbsp;|&nbsp; TP: <b style='color:#00ff99'>{float(trade['tp']):,.0f}</b>
                    &nbsp;|&nbsp; Now: <b>{curr:,.0f}</b>
                    &nbsp;|&nbsp; P&L: <b style='color:{pnl_color}'>{pnl:+.2f}%</b>
                    &nbsp;|&nbsp; {action}
                    &nbsp;|&nbsp; <span style='color:#889'>D{days}/{trade.get('hold_days',3)}</span>
                </div>
                """, unsafe_allow_html=True)

        # History table
        closed = [l for l in logs if l["status"] != "OPEN"]
        if closed:
            st.markdown("#### Riwayat Tertutup")
            df_hist = pd.DataFrame(closed)[
                ["date","ticker","signal","score","entry","sl","tp","exit_price","status","note","hold_days"]
            ].sort_values("date", ascending=False)
            st.dataframe(df_hist, use_container_width=True, hide_index=True)

        col_dl, col_reset = st.columns([3,1])
        with col_dl:
            st.download_button("⬇️ Download CSV",
                               pd.DataFrame(logs).to_csv(index=False).encode("utf-8"),
                               "idx_trade_log.csv", "text/csv")
        with col_reset:
            if st.button("🗑️ Reset Semua Data", type="secondary"):
                save_log([])
                st.rerun()
