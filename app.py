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

# ==================================================
# CONFIG
# ==================================================
st.set_page_config(page_title="IDX Terminal v6 - Teknikal + Interpretasi", layout="wide", initial_sidebar_state="collapsed")

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
.progress-label { font-size:12px; color:#aaa; margin-bottom:4px; }
.progress-bar-container { background:#1e2a3a; border-radius:10px; height:8px; width:100%; margin:5px 0; }
.progress-bar-fill { background:#00ff99; border-radius:10px; height:8px; width:0%; }
.insight-box {
    background: #0a1428; border-left: 4px solid #00bbff; border-radius: 8px;
    padding: 10px 15px; margin: 10px 0; font-size: 13px; color: #c0d0e0;
}
</style>
""", unsafe_allow_html=True)

# ==================================================
# UNIVERSE DATABASE (sama seperti sebelumnya, dipotong agar tidak terlalu panjang)
# ==================================================
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

# ==================================================
# HELPERS
# ==================================================
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

def calc_sr(df):
    if len(df) < 20:
        return [], []
    hh = df['high'].rolling(5, center=True).max()
    ll = df['low'].rolling(5, center=True).min()
    res = sorted(df[df['high'] == hh]['high'].dropna().unique(), reverse=True)[:3]
    sup = sorted(df[df['low'] == ll]['low'].dropna().unique())[:3]
    return list(res), list(sup)

# ==================================================
# TEKNIKAL LEVELS & INTERPRETASI GRAFIK
# ==================================================
def get_swing_low_high(df, lookback=5):
    if len(df) < lookback:
        return df['low'].min(), df['high'].max()
    recent = df.iloc[-lookback:]
    swing_low = recent['low'].min()
    swing_high = recent['high'].max()
    return swing_low, swing_high

def get_pivot_points(df):
    last = df.iloc[-1]
    high = safe_float(last['high'])
    low = safe_float(last['low'])
    close = safe_float(last['close'])
    pivot = (high + low + close) / 3
    r1 = 2*pivot - low
    r2 = pivot + (high - low)
    s1 = 2*pivot - high
    s2 = pivot - (high - low)
    return pivot, r1, r2, s1, s2

def get_support_resistance(df, n=10):
    if len(df) < n:
        return [], []
    highs = df['high'].rolling(n, center=True).max().dropna()
    lows = df['low'].rolling(n, center=True).min().dropna()
    resistances = sorted(highs.unique(), reverse=True)[:3]
    supports = sorted(lows.unique())[:3]
    return resistances, supports

def detect_trend(df):
    if len(df) < 20:
        return "Data tidak cukup"
    last = df.iloc[-1]
    prev = df.iloc[-2]
    ema20_now = safe_float(last['ema20'])
    ema20_prev = safe_float(prev['ema20'])
    slope = ema20_now - ema20_prev
    price = safe_float(last['close'])
    if price > ema20_now and slope > 0:
        return "UPTREND (bullish)"
    elif price < ema20_now and slope < 0:
        return "DOWNTREND (bearish)"
    else:
        return "SIDEWAYS (konsolidasi)"

def detect_candlestick_pattern(df):
    if len(df) < 3:
        return "—"
    o = df['open'].values
    h = df['high'].values
    l = df['low'].values
    c = df['close'].values
    i = -1
    body = abs(c[i]-o[i])
    range_candle = h[i]-l[i]
    upper_shadow = h[i] - max(c[i], o[i])
    lower_shadow = min(c[i], o[i]) - l[i]
    patterns = []
    if range_candle > 0:
        if lower_shadow >= 2*body and upper_shadow <= 0.3*body:
            patterns.append("🔨 Hammer (bullish reversal)")
        if upper_shadow >= 2*body and lower_shadow <= 0.3*body:
            patterns.append("⬆️ Inverted Hammer (bullish)")
        if body/range_candle < 0.1:
            patterns.append("✳️ Doji (indecision / reversal)")
        if body/range_candle > 0.85:
            patterns.append("💪 Marubozu (strong momentum)")
    prev_body = abs(c[-2]-o[-2])
    if c[-2] < o[-2] and c[i] > o[i] and body > prev_body:
        patterns.append("🟢 Bullish Engulfing (reversal up)")
    if c[-2] > o[-2] and c[i] < o[i] and body > prev_body:
        patterns.append("🔴 Bearish Engulfing (reversal down)")
    if len(df)>=3:
        if c[-3] < o[-3] and abs(c[-2]-o[-2]) < 0.003*c[-2] and c[i] > o[i]:
            patterns.append("🌅 Morning Star (bullish reversal)")
        if c[-3] > o[-3] and abs(c[-2]-o[-2]) < 0.003*c[-2] and c[i] < o[i]:
            patterns.append("🌇 Evening Star (bearish reversal)")
    return patterns[0] if patterns else "Tidak ada pola signifikan"

def detect_rsi_divergence(df):
    if len(df) < 20:
        return None
    prices = df['close'].values
    rsi = df['rsi'].values
    last_price = prices[-1]
    last_rsi = rsi[-1]
    price_lows = []
    rsi_lows = []
    for i in range(-10, -1):
        if prices[i] < prices[i-1] and prices[i] < prices[i+1]:
            price_lows.append((i, prices[i]))
            rsi_lows.append((i, rsi[i]))
    if len(price_lows) >= 2:
        if price_lows[-1][1] < price_lows[-2][1] and rsi_lows[-1][1] > rsi_lows[-2][1]:
            return "Bullish Divergence (harga turun, RSI naik) → potensi reversal naik"
        price_highs = []
        rsi_highs = []
        for i in range(-10, -1):
            if prices[i] > prices[i-1] and prices[i] > prices[i+1]:
                price_highs.append((i, prices[i]))
                rsi_highs.append((i, rsi[i]))
        if len(price_highs) >= 2:
            if price_highs[-1][1] > price_highs[-2][1] and rsi_highs[-1][1] < rsi_highs[-2][1]:
                return "Bearish Divergence (harga naik, RSI turun) → potensi reversal turun"
    return None

def detect_volume_surge(df, threshold=1.5):
    if len(df) < 20:
        return None, False
    avg_vol = df['volume'].rolling(20).mean().iloc[-1]
    last_vol = df['volume'].iloc[-1]
    ratio = last_vol / avg_vol if avg_vol > 0 else 0
    if ratio >= threshold:
        return f"Volume surge {ratio:.1f}x → konfirmasi breakout atau reversal", True
    return f"Volume normal ({ratio:.1f}x)", False

def detect_breakout(df, resistances, supports):
    last_close = df['close'].iloc[-1]
    last_high = df['high'].iloc[-1]
    last_low = df['low'].iloc[-1]
    breakout_up = False
    breakout_down = False
    if resistances:
        nearest_res = min([r for r in resistances if r > last_close], default=None)
        if nearest_res and last_high > nearest_res:
            breakout_up = True
    if supports:
        nearest_sup = max([s for s in supports if s < last_close], default=None)
        if nearest_sup and last_low < nearest_sup:
            breakout_down = True
    return breakout_up, breakout_down

def get_technical_levels(df, score, mode="aggressive"):
    if df.empty or len(df) < 20:
        return None, None, None, None, None, None
    df = df.copy()
    df['ema20'] = ta.ema(df['close'], length=20)
    df['ema50'] = ta.ema(df['close'], length=50)
    df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
    bb = ta.bbands(df['close'], length=20, std=2)
    if bb is not None and not bb.empty:
        df['bb_l'] = bb.iloc[:,2]
    else:
        df['bb_l'] = df['close']

    last = df.iloc[-1]
    close = safe_float(last['close'])
    ema20 = safe_float(last['ema20'])
    atr = safe_float(last['atr'])
    bb_lower = safe_float(last['bb_l'])
    swing_low, swing_high = get_swing_low_high(df, 5)
    pivot, r1, r2, s1, s2 = get_pivot_points(df)
    resistances, supports = get_support_resistance(df, 10)

    if close > ema20:
        entry = max(ema20, bb_lower)
        entry = min(close, entry * 1.01)
    else:
        support_candidates = [s for s in supports if s < close] + [s1, s2, bb_lower]
        valid_supports = [s for s in support_candidates if s > 0 and s < close]
        if valid_supports:
            entry = max(valid_supports)
        else:
            entry = close * 0.98
    entry = max(entry, close * 0.97)
    entry = round(entry, 0)

    sl_candidates = [swing_low * 0.99, s1 * 0.99, s2 * 0.99, bb_lower * 0.98]
    sl_candidates = [s for s in sl_candidates if s > 0 and s < entry]
    if sl_candidates:
        sl = max(sl_candidates)
    else:
        sl = entry - max(atr * 1.2, entry * 0.015)
    sl = max(sl, entry * 0.95)
    sl = round(sl, 0)

    risk = entry - sl
    if risk <= 0:
        risk = entry * 0.01
    res_candidates = [r for r in resistances if r > entry] + [r1, r2, swing_high]
    valid_res = [r for r in res_candidates if r > entry]
    if valid_res:
        tp = min(valid_res)
    else:
        tp = entry + max(risk * 2, entry * 0.03)
    if (tp - entry) < (risk * 1.5):
        tp = entry + risk * 2
    tp = round(tp, 0)
    rr = round((tp - entry) / (entry - sl), 2) if (entry - sl) > 0 else 0

    if score >= 70 and close > ema20:
        signal = "⚡ STRONG BUY"
        sig_color = "#00ff99"
    elif score >= 55 and close > ema20:
        signal = "✅ BUY"
        sig_color = "#44dd88"
    elif score < 40 or close < ema20 * 0.98:
        signal = "❌ SELL/AVOID"
        sig_color = "#ff4466"
    else:
        signal = "🔄 HOLD/WATCH"
        sig_color = "#ffcc00"

    return entry, sl, tp, rr, signal, sig_color

# ==================================================
# FUNGSI DASAR (detect_patterns, volume_analysis, score_ticker)
# ==================================================
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

# ==================================================
# ANALISIS FULL
# ==================================================
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
            return None, ticker_name, "Data", "Data kosong"
        last = d.iloc[-1]
        rsi_q  = safe_float(last.get('rsi', 50))
        cl_q   = safe_float(last.get('close', 0))
        ema_q  = safe_float(last.get('ema20', cl_q))
        macd_v = safe_float(last.get('macd', 0))
        sig_v2 = safe_float(last.get('sig', 0))
        if not (min_rsi <= rsi_q <= max_rsi):
            return None, ticker_name, "RSI", f"RSI={rsi_q:.1f}"
        if require_above_ema and cl_q < ema_q:
            return None, ticker_name, "EMA20", f"Harga < EMA20"
        sc_val, sc_det = score_ticker(d)
        if sc_val < min_score:
            return None, ticker_name, "Score", f"Score={sc_val}"
        entry, sl, tp, rr, sig, _ = get_technical_levels(d, sc_val)
        if entry is None:
            return None, ticker_name, "Teknikal", "Gagal hitung level"
        if "SELL" in sig or "WEAK" in sig:
            return None, ticker_name, "Signal", sig
        if signal_filter == "Strong BUY Only" and "STRONG" not in sig:
            return None, ticker_name, "Signal Filter", "Butuh STRONG BUY"
        if signal_filter == "Semua BUY" and "BUY" not in sig:
            return None, ticker_name, "Signal Filter", "Bukan BUY"
        vr, vlbl, vsurge_light, vsurge_strong = volume_analysis(d)
        if require_surge and not vsurge_light:
            return None, ticker_name, "Volume", f"Vol={vr:.2f}x"
        if vr < min_vol_ratio:
            return None, ticker_name, "Volume Ratio", f"Vol={vr:.2f}x"
        if require_macd_bull and macd_v <= sig_v2:
            return None, ticker_name, "MACD", "MACD tidak bullish"
        pats = detect_patterns(d)
        result = {
            "Ticker": ticker_name, "Score": sc_val, "Signal": sig, "Price": int(entry),
            "RSI": round(rsi_q,1), "Vol": vlbl, "MACD": "✅" if macd_v > sig_v2 else "❌",
            "EMA20": "✅" if cl_q >= ema_q else f"⚠️{((cl_q-ema_q)/ema_q*100):.1f}%",
            "SL": int(sl), "TP": int(tp), "R:R": f"1:{rr}", "Pattern": pats[0] if pats else "—",
        }
        return result, ticker_name, None, None
    except Exception as e:
        return None, ticker_name, "Exception", str(e)

def run_parallel_scan(tickers, scan_params, max_workers=10, progress_placeholder=None, status_placeholder=None):
    args_list = [(t, *scan_params) for t in tickers]
    results = []; debug_log = []; errors = 0; completed = 0; total = len(tickers)
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
                status_placeholder.markdown(f"⚡ Parallel scan: {completed}/{total} | Kandidat: {len(results)}")
    return results, debug_log, errors

# ==================================================
# INTERPRETASI GRAFIK
# ==================================================
def generate_chart_insights(df, ticker, entry, sl, tp, score, signal):
    if df.empty:
        return "Data tidak cukup."
    last = df.iloc[-1]
    close = safe_float(last['close'])
    ema20 = safe_float(last['ema20'] if 'ema20' in df.columns else close)
    ema50 = safe_float(last['ema50'] if 'ema50' in df.columns else close)
    rsi = safe_float(last['rsi'] if 'rsi' in df.columns else 50)
    macd = safe_float(last['macd'] if 'macd' in df.columns else 0)
    sig = safe_float(last['sig'] if 'sig' in df.columns else 0)
    
    trend = detect_trend(df)
    candle_pattern = detect_candlestick_pattern(df)
    divergence = detect_rsi_divergence(df)
    vol_msg, vol_surge = detect_volume_surge(df)
    resistances, supports = get_support_resistance(df, 10)
    breakout_up, breakout_down = detect_breakout(df, resistances, supports)
    
    insights = []
    insights.append(f"📈 **Tren:** {trend}")
    if trend == "UPTREND (bullish)":
        insights.append("✅ Harga di atas EMA20 dan EMA20 naik → momentum bullish.")
    elif trend == "DOWNTREND (bearish)":
        insights.append("⚠️ Harga di bawah EMA20 dan EMA20 turun → hindari posisi long.")
    else:
        insights.append("🟡 Konsolidasi, tunggu breakout.")
    
    insights.append(f"🕯️ **Pola Candlestick Terakhir:** {candle_pattern}")
    if "Hammer" in candle_pattern or "Engulfing" in candle_pattern or "Morning Star" in candle_pattern:
        insights.append("🔨 Pola reversal bullish terdeteksi → potensi kenaikan.")
    elif "Bearish Engulfing" in candle_pattern or "Evening Star" in candle_pattern:
        insights.append("🔻 Pola reversal bearish → waspada koreksi.")
    elif "Doji" in candle_pattern:
        insights.append("✳️ Doji menandakan ketidakpastian. Tunggu konfirmasi candle berikutnya.")
    
    insights.append(f"📊 **RSI (14):** {rsi:.1f}")
    if rsi > 70:
        insights.append("⚠️ RSI overbought (>70) → potensi koreksi segera.")
    elif rsi < 30:
        insights.append("✅ RSI oversold (<30) → potensi rebound teknikal.")
    elif 40 <= rsi <= 60:
        insights.append("🟢 RSI netral, aman untuk entry.")
    
    if divergence:
        insights.append(f"🔄 **Divergence:** {divergence}")
    
    insights.append(f"📦 **Volume:** {vol_msg}")
    if vol_surge:
        insights.append("🔥 Lonjakan volume mengkonfirmasi pergerakan harga.")
    
    if breakout_up:
        insights.append("🚀 **Breakout resistansi!** Harga menembus level resistance. Potensi lanjutan naik.")
    elif breakout_down:
        insights.append("📉 **Breakdown support!** Harga jatuh di bawah support. Hindari beli.")
    
    if supports:
        s_str = ", ".join([f"{int(s):,}" for s in supports[-2:]])
        insights.append(f"🟢 **Support terdekat:** {s_str}")
    if resistances:
        r_str = ", ".join([f"{int(r):,}" for r in resistances[:2]])
        insights.append(f"🔴 **Resistance terdekat:** {r_str}")
    
    insights.append(f"💰 **Entry yang direkomendasikan:** {entry:,.0f}")
    insights.append(f"🛑 **Stop Loss:** {sl:,.0f} ({(entry-sl)/entry*100:.1f}% di bawah entry)")
    insights.append(f"🎯 **Take Profit:** {tp:,.0f} ({(tp-entry)/entry*100:.1f}% di atas entry)")
    risk_reward = (tp-entry)/(entry-sl) if (entry-sl)>0 else 0
    insights.append(f"⚖️ **Risk/Reward:** 1:{risk_reward:.2f} {'✅ Ideal' if risk_reward>=2 else '⚠️ Kurang ideal (min 1:2)'}")
    
    return insights

# ==================================================
# WIN/LOSS TRACKER
# ==================================================
TRACKER_FILE = Path("idx_trade_log.json")
TZ_JKT = pytz.timezone("Asia/Jakarta")

def load_trade_log() -> list:
    if TRACKER_FILE.exists():
        with open(TRACKER_FILE, "r") as f:
            return json.load(f)
    return []

def save_trade_log(logs: list):
    with open(TRACKER_FILE, "w") as f:
        json.dump(logs, f, indent=2, default=str)

def save_scan_results_to_log(df_results: pd.DataFrame, hold_days: int, scan_date: str = None):
    if scan_date is None:
        scan_date = datetime.now(TZ_JKT).strftime("%Y-%m-%d")
    logs = load_trade_log()
    existing_keys = {(e["date"], e["ticker"]) for e in logs}
    new_entries = 0
    for _, row in df_results.iterrows():
        key = (scan_date, row["Ticker"])
        if key in existing_keys:
            continue
        logs.append({
            "id": f"{scan_date}_{row['Ticker']}", "date": scan_date, "ticker": row["Ticker"],
            "signal": row["Signal"], "score": int(row["Score"]), "entry": float(row["Price"]),
            "sl": float(row["SL"]), "tp": float(row["TP"]), "rr": str(row["R:R"]),
            "pattern": row.get("Pattern", "—"), "hold_days": hold_days,
            "exit_price": None, "exit_date": None, "status": "OPEN", "auto_resolved": False, "note": "",
        })
        new_entries += 1
    save_trade_log(logs)
    return new_entries

def is_market_closed() -> tuple[bool, str]:
    now_jkt = datetime.now(TZ_JKT)
    closed = now_jkt.hour > 15 or (now_jkt.hour == 15 and now_jkt.minute >= 30)
    return closed, now_jkt.strftime("%H:%M WIB")

def get_price_progress(ticker_jk, entry, sl, tp, target_date):
    try:
        end = datetime.now(TZ_JKT).date()
        start = target_date - timedelta(days=1)
        hist = clean_df(yf.download(ticker_jk, start=start, end=end + timedelta(days=1), progress=False))
        if hist.empty:
            return None, None, None, None, None
        hist_from = hist[hist.index.date >= target_date]
        if hist_from.empty:
            return None, None, None, None, None
        return safe_float(hist_from['close'].iloc[-1]), hist_from['high'].max(), hist_from['low'].min(), safe_float(hist_from['close'].iloc[-1]), hist_from
    except:
        return None, None, None, None, None

def evaluate_trade_progress(ticker, entry, sl, tp, target_date, hold_days):
    ticker_jk = ticker + ".JK"
    curr_price, highest, lowest, last_close, hist = get_price_progress(ticker_jk, entry, sl, tp, target_date)
    if curr_price is None:
        return "OPEN", None, None, "Data tidak tersedia", 0, 0, 0, 0
    today = datetime.now(TZ_JKT).date()
    days_held = (today - target_date).days
    if highest >= tp:
        return "WIN", tp, target_date + timedelta(days=1), "TP tercapai", (tp-entry)/entry*100, days_held, 0, 0
    if lowest <= sl:
        return "LOSS", sl, target_date + timedelta(days=1), "SL tersentuh", (sl-entry)/entry*100, days_held, 0, 0
    if days_held >= hold_days:
        pnl = (last_close - entry)/entry*100
        return ("WIN" if pnl>=0 else "LOSS"), last_close, today, f"Force close {hold_days} hari", pnl, days_held, 0, 0
    dist_to_tp = (tp-curr_price)/tp*100 if tp>0 else 0
    dist_to_sl = (curr_price-sl)/curr_price*100 if curr_price>0 else 0
    if dist_to_tp <= 1.5: action = "🚀 Segera TP"
    elif dist_to_sl <= 1.5: action = "⚠️ Cut loss"
    elif dist_to_tp <= 3: action = "📈 Menuju TP"
    elif dist_to_sl <= 3: action = "📉 Mendekati SL"
    else: action = "🟡 Hold"
    return "OPEN", curr_price, None, action, 0, days_held, dist_to_tp, dist_to_sl

def auto_resolve_all_trades():
    logs = load_trade_log()
    updated = False
    notifs = []
    for trade in logs:
        if trade["status"] != "OPEN":
            continue
        target_date = date.fromisoformat(trade["date"])
        hold_days = trade.get("hold_days", 3)
        entry = float(trade["entry"]); sl = float(trade["sl"]); tp = float(trade["tp"])
        status, exit_price, exit_date, reason, pnl, days_held, _, _ = evaluate_trade_progress(
            trade["ticker"], entry, sl, tp, target_date, hold_days
        )
        if status != "OPEN":
            trade["status"] = status; trade["exit_price"] = exit_price; trade["exit_date"] = str(exit_date) if exit_date else None
            trade["auto_resolved"] = True; trade["note"] = reason; updated = True
            notifs.append({"ticker": trade["ticker"], "status": status, "pnl_pct": pnl, "days_held": days_held})
    if updated:
        save_trade_log(logs)
    return notifs

def compute_tracker_stats(logs: list) -> dict:
    closed = [l for l in logs if l["status"] in ("WIN","LOSS")]
    wins = [l for l in closed if l["status"]=="WIN"]
    losses = [l for l in closed if l["status"]=="LOSS"]
    pnl_list = []
    for l in closed:
        if l.get("exit_price") and l.get("entry"):
            pnl_list.append((float(l["exit_price"])-float(l["entry"]))/float(l["entry"])*100)
    win_rate = round(len(wins)/len(closed)*100,1) if closed else 0
    avg_pnl = round(sum(pnl_list)/len(pnl_list),2) if pnl_list else 0
    total_pnl = round(sum(pnl_list),2) if pnl_list else 0
    stats_1d = {"wins":0,"losses":0,"total":0}
    stats_3d = {"wins":0,"losses":0,"total":0}
    for l in closed:
        hd = l.get("hold_days",3)
        if hd==1:
            stats_1d["total"]+=1
            if l["status"]=="WIN": stats_1d["wins"]+=1
            else: stats_1d["losses"]+=1
        else:
            stats_3d["total"]+=1
            if l["status"]=="WIN": stats_3d["wins"]+=1
            else: stats_3d["losses"]+=1
    return {"total":len(logs),"closed":len(closed),"wins":len(wins),"losses":len(losses),"opens":len([l for l in logs if l["status"]=="OPEN"]),
            "win_rate":win_rate,"avg_pnl":avg_pnl,"total_pnl":total_pnl,"stats_1d":stats_1d,"stats_3d":stats_3d}

# ==================================================
# HEADER & MARKET PULSE
# ==================================================
st.markdown("""
<h1 style='text-align:center;color:#00bbff;'>⚡ IDX TERMINAL v6 — TEKNIKAL + INTERPRETASI GRAFIK</h1>
<p style='text-align:center;color:#445566;'>Analisis Candlestick, S/R, Divergence, Breakout, Volume Surge</p>
""", unsafe_allow_html=True)

notifications = auto_resolve_all_trades()
if notifications:
    st.markdown("---### 🔔 Update Otomatis Trade")
    for n in notifications[:3]:
        st.write(f"{n['ticker']} → {n['status']} ({n['pnl_pct']:+.2f}%)")
    st.markdown("---")

col_ihsg, col_sector = st.columns([1,1])
ihsg_df = pd.DataFrame(); ihsg_change=0.0
with col_ihsg:
    st.subheader("📈 IHSG Market Pulse")
    raw = yf.download("^JKSE",period="1y",progress=False); ihsg_df=clean_df(raw)
    if not ihsg_df.empty:
        ihsg_change=((ihsg_df['close'].iloc[-1]-ihsg_df['close'].iloc[-2])/ihsg_df['close'].iloc[-2])*100
        ihsg_df['ma20']=ihsg_df['close'].rolling(20).mean()
        fig=go.Figure()
        fig.add_trace(go.Scatter(x=ihsg_df.index,y=ihsg_df['close'],fill='tozeroy',line_color='#00bbff'))
        fig.add_trace(go.Scatter(x=ihsg_df.index,y=ihsg_df['ma20'],line=dict(color='orange',width=1.5,dash='dot')))
        fig.update_layout(height=230,template='plotly_dark',margin=dict(l=0,r=0,t=0,b=0),showlegend=False)
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
        fig=px.treemap(df_s,path=['Parent','Sektor'],values='Size',color='Perf',color_continuous_scale='RdYlGn',range_color=[-3,3])
        fig.update_layout(height=230,margin=dict(l=0,r=0,t=0,b=0),template='plotly_dark')
        st.plotly_chart(fig,use_container_width=True)
        best=max(sec_data,key=lambda x:x['Perf']); worst=min(sec_data,key=lambda x:x['Perf'])
        bias = "🟢 BULLISH" if ihsg_change>0.3 else ("🔴 BEARISH" if ihsg_change<-0.3 else "🟡 SIDEWAYS")
        st.caption(f"Market Bias: **{bias}** | 🏆 {best['Sektor']} ({best['Perf']:+.2f}%) | ⚠️ {worst['Sektor']} ({worst['Perf']:+.2f}%)")

st.divider()

# ==================================================
# DEEP ANALYSIS dengan Interpretasi Grafik
# ==================================================
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
        entry, sl, tp, rr, signal, _ = get_technical_levels(df, score)
        if entry is None:
            st.warning("Gagal hitung level teknikal.")
        else:
            l=df.iloc[-1]
            cl=safe_float(l['close']); rsi=safe_float(l['rsi'])
            e20=safe_float(l['ema20']); e50=safe_float(l['ema50'])
            pats=detect_patterns(df)
            vr, vlbl, vsurge_light, vsurge_strong = volume_analysis(df)
            res,sup = calc_sr(df)
            
            # Interpretasi grafik
            insights = generate_chart_insights(df, target, entry, sl, tp, score, signal)
            
            st.markdown(f"### {target}")
            c1,c2,c3,c4,c5 = st.columns(5)
            c1.metric("Score", f"{score}/100")
            c2.metric("Signal", signal)
            c3.metric("RSI", f"{rsi:.1f}")
            c4.metric("Volume", vlbl)
            c5.metric("Close", f"{cl:,.0f}")
            
            # Tampilkan insight dalam box
            st.markdown("#### 📋 Interpretasi Grafik Otomatis")
            insight_html = "<div class='insight-box'>" + "<br>".join(insights) + "</div>"
            st.markdown(insight_html, unsafe_allow_html=True)
            
            # Chart dengan anotasi S/R
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.55,0.25,0.20], vertical_spacing=0.04)
            fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'],
                                         increasing_line_color='#00ff99', decreasing_line_color='#ff4466'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['ema20'], line=dict(color='orange', width=1.8), name='EMA20'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['ema50'], line=dict(color='#00aaff', width=1.2, dash='dot'), name='EMA50'), row=1, col=1)
            # Support & resistance
            for s in sup[-2:]:
                fig.add_hline(y=s, line_dash="dash", line_color="green", opacity=0.5, row=1, col=1)
            for r in res[:2]:
                fig.add_hline(y=r, line_dash="dash", line_color="red", opacity=0.5, row=1, col=1)
            fig.add_hline(y=sl, line_dash="dash", line_color="#ff4466", annotation_text=f"SL {sl:,.0f}", row=1, col=1)
            fig.add_hline(y=tp, line_dash="dash", line_color="#00ff99", annotation_text=f"TP {tp:,.0f}", row=1, col=1)
            fig.add_hline(y=entry, line_dash="dot", line_color="#ffcc00", annotation_text=f"Entry {entry:,.0f}", row=1, col=1)
            # MACD
            hc = ['#00ff99' if v>=0 else '#ff4466' for v in df['hist'].fillna(0)]
            fig.add_trace(go.Bar(x=df.index, y=df['hist'], marker_color=hc, name='Hist'), row=2, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['macd'], line=dict(color='#00bbff'), name='MACD'), row=2, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['sig'], line=dict(color='orange'), name='Signal'), row=2, col=1)
            # RSI
            fig.add_trace(go.Scatter(x=df.index, y=df['rsi'], line=dict(color='#bb77ff'), name='RSI'), row=3, col=1)
            fig.add_hline(y=72, line_dash="dot", line_color="red", annotation_text="OB", row=3, col=1)
            fig.add_hline(y=30, line_dash="dot", line_color="green", annotation_text="OS", row=3, col=1)
            fig.add_hrect(y0=55, y1=72, fillcolor="rgba(0,255,150,0.05)", line_width=0, row=3, col=1)
            # Volume di subplot RSI
            vc = ['#00ff99' if c>=o else '#ff4466' for c,o in zip(df['close'], df['open'])]
            fig.add_trace(go.Bar(x=df.index, y=df['volume']/df['volume'].max()*30, marker_color=vc, opacity=0.35, showlegend=False), row=3, col=1)
            fig.update_layout(height=680, template='plotly_dark', xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning(f"Data tidak cukup untuk {target}.")

st.divider()

# ==================================================
# SMART SCANNER (ringkas)
# ==================================================
st.subheader("🎯 Smart Scanner — Pilih Universe & Hold Period")
sc1,sc2,sc3,sc4 = st.columns([2,1,1,1])
with sc1:
    idx_choice = st.selectbox("📊 Universe:", list(INDEX_UNIVERSE.keys()))
with sc2:
    also_sector = st.multiselect("➕ Sektor:", list(MANUAL_SECTORS.keys()))
with sc3:
    min_score = st.slider("Min Score:", 0, 100, 55)
with sc4:
    top_n = st.number_input("Top N:", 5, 50, 10)

hold_period = st.radio("⏱️ Hold Period (hari)", [1,3], index=1, horizontal=True)
is_all_bei = "ALL BEI" in idx_choice

selected_universe = INDEX_UNIVERSE[idx_choice]
extra_from_sector = []
for sec in also_sector:
    extra_from_sector.extend(MANUAL_SECTORS[sec])
combined_universe = list(dict.fromkeys(selected_universe + extra_from_sector))

col_info1, col_info2 = st.columns([3,1])
with col_info1:
    badge_html = " ".join([f"<span class='universe-badge'>{t}</span>" for t in combined_universe[:40]])
    st.markdown(f"**Universe: {len(combined_universe)} saham**<br>{badge_html}", unsafe_allow_html=True)
with col_info2:
    signal_filter = st.selectbox("Filter Signal:", ["Semua BUY", "Strong BUY Only", "Semua (incl HOLD)"])

with st.expander("⚙️ Filter Tambahan", expanded=False):
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        min_vol_ratio = st.slider("Min Volume Ratio:", 0.5, 3.0, 1.0, 0.1)
        require_surge = st.checkbox("Wajib Volume Surge", value=False)
    with fc2:
        min_rsi = st.slider("RSI Min:", 10, 50, 30)
        max_rsi = st.slider("RSI Max:", 50, 90, 70)
    with fc3:
        require_macd_bull = st.checkbox("Wajib MACD Bullish", value=False)
        require_above_ema = st.checkbox("Wajib Price > EMA20", value=True)
    if is_all_bei:
        max_workers = st.slider("Thread Paralel:", 3, 20, 10, key="mw")
        use_vol_prefilter = st.checkbox("Pre-filter volume", value=True)
        min_avg_lot = st.slider("Min avg lot:", 100, 2000, 500) if use_vol_prefilter else 500
    else:
        max_workers = 10
        use_vol_prefilter = False
        min_avg_lot = 500

show_debug = st.checkbox("Debug Mode", value=False)

if st.button("🚀 MULAI SCAN", use_container_width=True, type="primary"):
    tickers_to_scan = add_jk(combined_universe)
    prog = st.progress(0); status = st.empty()
    start_time = time.time()
    scan_params = (min_score, signal_filter, require_above_ema, min_vol_ratio, require_surge, require_macd_bull,
                   min_rsi, max_rsi, min_avg_lot, use_vol_prefilter)
    if is_all_bei:
        results, debug_log, errors = run_parallel_scan(tickers_to_scan, scan_params, max_workers=max_workers,
                                                       progress_placeholder=prog, status_placeholder=status)
    else:
        results = []; debug_log = []; errors = 0
        for i, t in enumerate(tickers_to_scan):
            prog.progress((i+1)/len(tickers_to_scan))
            status.markdown(f"Scanning {t}... ({i+1}/{len(tickers_to_scan)}) | Candidates: {len(results)}")
            ticker_name = t.replace(".JK","")
            try:
                d = analyze_full_cached(t, period="6mo")
                if d is None or d.empty:
                    if show_debug: debug_log.append({"Ticker":ticker_name,"Gugur":"Data"})
                    continue
                last = d.iloc[-1]
                rsi_q = safe_float(last.get('rsi',50)); cl_q = safe_float(last.get('close',0))
                ema_q = safe_float(last.get('ema20',cl_q)); macd_v = safe_float(last.get('macd',0)); sig_v2 = safe_float(last.get('sig',0))
                if not (min_rsi <= rsi_q <= max_rsi):
                    if show_debug: debug_log.append({"Ticker":ticker_name,"Gugur":"RSI"})
                    continue
                if require_above_ema and cl_q < ema_q:
                    if show_debug: debug_log.append({"Ticker":ticker_name,"Gugur":"EMA20"})
                    continue
                sc_val, _ = score_ticker(d)
                if sc_val < min_score:
                    if show_debug: debug_log.append({"Ticker":ticker_name,"Gugur":"Score"})
                    continue
                entry, sl, tp, rr, sig, _ = get_technical_levels(d, sc_val)
                if entry is None: continue
                if "SELL" in sig or "WEAK" in sig: continue
                if signal_filter=="Strong BUY Only" and "STRONG" not in sig: continue
                if signal_filter=="Semua BUY" and "BUY" not in sig: continue
                vr, vlbl, vsurge_light, _ = volume_analysis(d)
                if require_surge and not vsurge_light: continue
                if vr < min_vol_ratio: continue
                if require_macd_bull and macd_v <= sig_v2: continue
                pats = detect_patterns(d)
                results.append({"Ticker":ticker_name,"Score":sc_val,"Signal":sig,"Price":int(entry),
                                "RSI":round(rsi_q,1),"Vol":vlbl,"MACD":"✅" if macd_v>sig_v2 else "❌",
                                "EMA20":"✅" if cl_q>=ema_q else f"⚠️{((cl_q-ema_q)/ema_q*100):.1f}%",
                                "SL":int(sl),"TP":int(tp),"R:R":f"1:{rr}","Pattern":pats[0] if pats else "—"})
            except Exception as e:
                errors+=1
                if show_debug: debug_log.append({"Ticker":ticker_name,"Gugur":"Exception","Alasan":str(e)})
    elapsed = time.time() - start_time
    prog.empty(); status.empty()
    st.caption(f"⏱️ Scan selesai dalam {elapsed:.1f} detik | {len(tickers_to_scan)} ticker | {errors} error")
    if show_debug and debug_log:
        with st.expander("Debug Log", expanded=True):
            st.dataframe(pd.DataFrame(debug_log))
    if results:
        df_res = pd.DataFrame(results).sort_values("Score", ascending=False).head(top_n)
        st.dataframe(df_res, use_container_width=True)
        n_saved = save_scan_results_to_log(df_res, hold_days=hold_period)
        if n_saved > 0:
            st.info(f"💾 {n_saved} rekomendasi disimpan ke tracker.")
        st.success(f"✅ {len(df_res)} kandidat dari {len(tickers_to_scan)} discan")
    else:
        st.warning("Tidak ada saham memenuhi kriteria.")

st.divider()

# ==================================================
# WIN/LOSS TRACKER (ringkas)
# ==================================================
st.subheader("📊 Win/Loss Tracker")
logs = load_trade_log()
if not logs:
    st.info("Belum ada data. Jalankan scanner.")
else:
    stats = compute_tracker_stats(logs)
    m1,m2,m3,m4,m5,m6 = st.columns(6)
    m1.metric("Win Rate", f"{stats['win_rate']}%")
    m2.metric("Menang", stats['wins'])
    m3.metric("Kalah", stats['losses'])
    m4.metric("Open", stats['opens'])
    m5.metric("Avg P&L", f"{stats['avg_pnl']:+.2f}%")
    m6.metric("Total P&L", f"{stats['total_pnl']:+.2f}%")
    
    open_trades = [l for l in logs if l["status"] == "OPEN"]
    if open_trades:
        st.markdown("### 🔄 Rekomendasi Aktif")
        for trade in open_trades[:5]:
            target_date = date.fromisoformat(trade["date"])
            hold_days = trade.get("hold_days",3)
            entry, sl, tp = float(trade["entry"]), float(trade["sl"]), float(trade["tp"])
            status, curr_price, _, action, _, days_held, _, _ = evaluate_trade_progress(
                trade["ticker"], entry, sl, tp, target_date, hold_days
            )
            if status != "OPEN":
                trade["status"] = status
                trade["exit_price"] = curr_price
                trade["auto_resolved"] = True
                save_trade_log(logs)
                st.rerun()
            st.markdown(f"{trade['ticker']} | Entry {entry:,.0f} | SL {sl:,.0f} | TP {tp:,.0f} | Current {curr_price:,.0f} | {action}")
    
    st.download_button("⬇️ Download CSV", pd.DataFrame(logs).to_csv(index=False).encode("utf-8"), "idx_log.csv")
