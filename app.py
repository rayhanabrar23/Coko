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
st.set_page_config(page_title="IDX Terminal v3", layout="wide", initial_sidebar_state="collapsed")

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

# IDX30 — 30 saham blue chip paling liquid (update Agustus 2025)
IDX30 = [
    "AADI","ADRO","AMMN","ANTM","AMRT","ASII","BBCA","BBNI","BBRI","BBTN",
    "BMRI","BRIS","BUKA","CPIN","EXCL","GOTO","ICBP","INCO","INDF","ISAT",
    "ITMG","KLBF","MDKA","MEDC","MIKA","PGEO","PTBA","TLKM","TOWR","UNTR"
]

# LQ45 — 45 saham liquid market cap besar (superset IDX30)
LQ45 = IDX30 + [
    "ACES","AKRA","ARTO","BELI","BNGA","BSDE","CTRA","EMTK","GGRM","HMSP",
    "INTP","JSMR","MAPI","MYOR","PGAS","PNBN","PWON","SMGR","TBIG","TINS",
    "TKIM","UNVR","HEAL","BYAN","CMRY","DCII","DSSA","NCKL","INKP","SILO"
]
LQ45 = list(dict.fromkeys(LQ45))[:45]

# IDX80 — 80 saham (superset LQ45, tambahan mid-cap liquid)
IDX80_EXTRA = [
    "AVIA","BDMN","BKSL","BUMI","CDIA","DEWA","ENRG","GEMS","GIAA","JPFA",
    "MEDC","MTEL","NISP","NCKL","PGEO","SMRA","SSIA","TAPG","TCPI","TBIG",
    "SIDO","PYFA","ARCO","BRPT","FILM","ARCI","BBHI","CUAN","VKTR","SOHO",
    "MDIY","BSIM","BIPI","JSMR","MAPI","PNBN","INKP","MYOR","CBDK","GGRM"
]
IDX80 = list(dict.fromkeys(LQ45 + IDX80_EXTRA))[:80]

# IDX High Dividend 20
IDX_HIDIV20 = [
    "ADRO","ANTM","ASII","BBCA","BBNI","BBRI","BMRI","CPIN","GGRM","HMSP",
    "INDF","ITMG","KLBF","MEDC","PGAS","PTBA","SMGR","TLKM","UNTR","UNVR"
]

# IDX Growth30 — saham pertumbuhan
IDX_GROWTH30 = [
    "ARTO","BELI","BRIS","BUKA","CMRY","DCII","DSSA","EMTK","GOTO","HEAL",
    "MIKA","MDKA","MTEL","NCKL","PGEO","SILO","TBIG","TOWR","VKTR","AMMN",
    "AADI","CUAN","BRMS","MBMA","TCPI","BREN","PANI","ARCO","CBDK","PGUN"
]

# IDX SMC (Small Mid Cap) Liquid — saham kecil menengah liquid
IDX_SMC = [
    "ACES","AKRA","BDMN","BNGA","BSDE","CTRA","GIAA","INTP","JPFA","JSMR",
    "MAPI","MYOR","NISP","PNBN","PWON","SMGR","SMRA","SSIA","TAPG","TINS",
    "SIDO","PYFA","SOHO","FILM","AVIA","BBHI","BUMI","GEMS","ARCI","DEWA",
    "ENRG","BIPI","BSIM","MDIY","CDIA","BBTN","MEGA","MLPT","NSSS","MSIN"
]

# Sektor manual (warisan v2, tetap tersedia)
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

# Index universe registry
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
    if 'volume' not in df.columns or len(df)<20: return 0,"N/A",False
    avg = df['volume'].rolling(20).mean().iloc[-1]
    last = df['volume'].iloc[-1]
    ratio = safe_float(last/avg) if avg>0 else 0
    return ratio, f"{ratio:.1f}x", ratio>=1.5

def score_ticker(df):
    """Multi-factor score 0-100"""
    if df.empty or len(df)<52: return 0,{}
    df = df.copy()
    df['ema20'] = ta.ema(df['close'],length=20)
    df['ema50'] = ta.ema(df['close'],length=50)
    df['rsi']   = ta.rsi(df['close'],length=14)
    df['atr']   = ta.atr(df['high'],df['low'],df['close'],length=14)
    macd_df     = ta.macd(df['close'],fast=12,slow=26,signal=9)
    if macd_df is not None and not macd_df.empty:
        df['macd']=macd_df.iloc[:,0]; df['sig']=macd_df.iloc[:,1]; df['hist']=macd_df.iloc[:,2]
    else:
        df['macd']=df['sig']=df['hist']=0
    bb = ta.bbands(df['close'],length=20,std=2)
    if bb is not None and not bb.empty:
        df['bb_u']=bb.iloc[:,0]; df['bb_m']=bb.iloc[:,1]; df['bb_l']=bb.iloc[:,2]
    else:
        df['bb_u']=df['bb_m']=df['bb_l']=df['close']

    l=df.iloc[-1]
    cl=safe_float(l['close']); e20=safe_float(l['ema20']); e50=safe_float(l['ema50'])
    rsi=safe_float(l['rsi']); macd=safe_float(l['macd']); sig=safe_float(l['sig'])
    hist=safe_float(l['hist']); bb_l=safe_float(l['bb_l']); bb_m=safe_float(l['bb_m'])

    # 1. TREND (0-25)
    ts=0
    if cl>e20: ts+=12
    if cl>e50: ts+=8
    gap=(cl-e20)/e20*100 if e20 else 0
    if -1<=gap<=3: ts+=5

    # 2. MOMENTUM (0-25)
    ms=0
    if 40<=rsi<=60: ms+=15
    elif 30<=rsi<40 or 60<rsi<=65: ms+=8
    if macd>sig: ms+=7
    if hist>0 and len(df)>1 and safe_float(df['hist'].iloc[-2])>=0 and hist>safe_float(df['hist'].iloc[-2]):
        ms+=3

    # 3. VOLUME (0-20)
    vr,_,_ = volume_analysis(df)
    vs=min(int(vr*8),20)

    # 4. BB ZONE (0-15)
    bs=0
    if cl<=bb_l*1.01: bs=15
    elif cl<=bb_m: bs=7

    # 5. PATTERN (0-15)
    pats=detect_patterns(df); ps=0
    for p in pats:
        if any(k in p for k in ['Engulfing','Morning Star','Hammer','Marubozu']): ps=15; break
        elif 'Doji' in p or 'Inv.' in p: ps=max(ps,5)

    score=min(ts+ms+vs+bs+ps,100)
    detail={'Trend':ts,'Momentum':ms,'Volume':vs,'BB Zone':bs,'Pattern':ps}
    return score, detail

def get_signal(df, score):
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

def analyze_full(ticker, period="1y"):
    df=yf.download(ticker,period=period,progress=False); df=clean_df(df)
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

def calc_sr(df):
    if len(df)<20: return [],[]
    hh=df['high'].rolling(5,center=True).max()
    ll=df['low'].rolling(5,center=True).min()
    res=sorted(df[df['high']==hh]['high'].dropna().unique(),reverse=True)[:3]
    sup=sorted(df[df['low']==ll]['low'].dropna().unique())[:3]
    return list(res), list(sup)

# ─────────────────────────────────────────────────────────
# INTERPRETASI KALIMAT ENGINE
# ─────────────────────────────────────────────────────────

def interpret_analysis(ticker, score, detail, signal, df, sl, tp, rr, pats, vr, vsurge, ihsg_change=0.0):
    """
    Generate human-readable narrative verdict.
    Returns: (verdict_html, verdict_plain, confidence_label, confidence_color)
    """
    l = df.iloc[-1]
    cl   = safe_float(l['close'])
    rsi  = safe_float(l['rsi']  if 'rsi'  in df.columns else 50)
    e20  = safe_float(l['ema20'] if 'ema20' in df.columns else cl)
    e50  = safe_float(l['ema50'] if 'ema50' in df.columns else cl)
    macd = safe_float(l['macd'] if 'macd' in df.columns else 0)
    sig  = safe_float(l['sig']  if 'sig'  in df.columns else 0)
    atr  = safe_float(l['atr']  if 'atr'  in df.columns else cl * 0.02)
    name = ticker.replace(".JK","")

    # ── Kumpulkan argumen PRO (buy) dan KONTRA (jangan buy) ──
    pros  = []
    cons  = []
    cautions = []

    # TREND
    gap_pct = (cl - e20) / e20 * 100 if e20 else 0
    if cl > e20 and cl > e50:
        pros.append(f"Harga berada di atas EMA20 ({e20:,.0f}) dan EMA50 ({e50:,.0f}), menunjukkan tren naik jangka pendek dan menengah masih kuat.")
    elif cl > e20 and cl <= e50:
        cautions.append(f"Harga sudah menembus EMA20 ke atas ({gap_pct:+.1f}%), tapi masih di bawah EMA50 — tren menengah belum sepenuhnya recovery.")
    else:
        cons.append(f"Harga ({cl:,.0f}) masih di bawah EMA20 ({e20:,.0f}) dan EMA50 ({e50:,.0f}). Tren masih negatif, masuk sekarang berisiko tinggi.")

    if -0.5 <= gap_pct <= 2.5:
        pros.append(f"Posisi harga hanya {gap_pct:+.1f}% dari EMA20 — ini adalah zona rebound ideal, tidak terlalu jauh dan tidak terlalu dekat.")
    elif gap_pct > 5:
        cautions.append(f"Harga sudah {gap_pct:.1f}% di atas EMA20, artinya saham sudah cukup jauh dari support — risiko koreksi lebih tinggi jika masuk sekarang.")

    # MOMENTUM — RSI
    if 40 <= rsi <= 60:
        pros.append(f"RSI di {rsi:.1f} berada di zona netral-ideal (40–60). Saham sudah 'istirahat' dari kenaikan sebelumnya dan siap kembali naik tanpa risiko overbought.")
    elif rsi < 35:
        pros.append(f"RSI {rsi:.1f} menunjukkan kondisi oversold — tekanan jual sudah sangat ekstrem dan peluang rebound teknikal sangat tinggi.")
    elif 60 < rsi <= 70:
        cautions.append(f"RSI {rsi:.1f} sudah memasuki zona agak panas. Masih boleh masuk tapi dengan lot lebih kecil — momentum sedang kuat tapi potensi koreksi mulai meningkat.")
    elif rsi > 70:
        cons.append(f"RSI {rsi:.1f} sudah overbought (>70). Secara statistik, saham rawan koreksi dalam 1–3 hari ke depan. Tidak disarankan masuk di level ini.")

    # MOMENTUM — MACD
    if macd > sig:
        hist_val = safe_float(l['hist'] if 'hist' in df.columns else 0)
        prev_hist = safe_float(df['hist'].iloc[-2] if 'hist' in df.columns and len(df)>1 else 0)
        if hist_val > prev_hist:
            pros.append(f"MACD sudah golden cross (bullish) dan histogram MACD terus membesar — momentum beli semakin kuat dan akselerasi naik masih berlanjut.")
        else:
            pros.append(f"MACD berada di atas signal line (bullish cross), mengkonfirmasi tekanan beli lebih dominan dari tekanan jual saat ini.")
    else:
        cons.append(f"MACD masih di bawah signal line (bearish cross) — momentum jual masih dominan. Tunggu konfirmasi golden cross sebelum masuk.")

    # VOLUME
    if vsurge:
        pros.append(f"Volume hari ini {vr:.1f}x di atas rata-rata 20 hari — ini adalah konfirmasi kuat bahwa ada 'uang besar' (institusional) yang masuk. Breakout dengan volume tinggi jauh lebih valid.")
    elif vr >= 1.2:
        pros.append(f"Volume {vr:.1f}x rata-rata, menunjukkan minat beli yang mulai meningkat walau belum surge penuh.")
    elif vr < 0.8:
        cautions.append(f"Volume sepi ({vr:.1f}x rata-rata) — pergerakan harga tanpa volume yang cukup rentan jadi false move. Tunggu volume konfirmasi.")

    # BOLLINGER BAND
    if 'bb_l' in df.columns and 'bb_m' in df.columns:
        bb_l = safe_float(l['bb_l']); bb_m = safe_float(l['bb_m']); bb_u = safe_float(l['bb_u'])
        if cl <= bb_l * 1.01:
            pros.append(f"Harga menyentuh lower Bollinger Band ({bb_l:,.0f}) — secara statistik ini zona oversold di mana harga historis sering berbalik naik menuju midband ({bb_m:,.0f}).")
        elif cl >= bb_u * 0.98:
            cons.append(f"Harga mendekati upper Bollinger Band ({bb_u:,.0f}). Ini zona resistance kuat — beli di sini berarti beli di puncak, risiko koreksi ke midband tinggi.")

    # PATTERN
    pat_str = pats[0] if pats else "—"
    bullish_pats = ['Engulfing','Morning Star','Hammer','Marubozu']
    bearish_pats = ['Bearish','Evening Star']
    if any(k in pat_str for k in bullish_pats):
        pros.append(f"Terdeteksi pola candlestick '{pat_str.replace('🟢','').replace('🔨','').replace('🌅','').replace('💪','').strip()}' — pola ini secara historis muncul di awal pembalikan bullish.")
    elif any(k in pat_str for k in bearish_pats):
        cons.append(f"Pola candlestick '{pat_str}' terdeteksi — ini sinyal peringatan bahwa tekanan jual bisa meningkat dalam waktu dekat.")
    elif 'Doji' in pat_str:
        cautions.append(f"Pola Doji terdeteksi — pasar sedang dalam kebimbangan antara beli dan jual. Tunggu satu candle konfirmasi arah sebelum masuk.")

    # MARKET CONTEXT
    if ihsg_change > 0.5:
        pros.append(f"IHSG sedang dalam momentum positif ({ihsg_change:+.2f}%) — kondisi market secara umum mendukung setup beli ini.")
    elif ihsg_change < -0.5:
        cautions.append(f"IHSG sedang melemah ({ihsg_change:+.2f}%). Bahkan saham yang secara teknikal bagus bisa ikut tertekan jika market secara keseluruhan turun.")

    # R:R check
    if rr >= 2.0:
        pros.append(f"Risk:Reward ratio 1:{rr} — untuk setiap Rp 1 yang dirisikoan, potensi keuntungan Rp {rr}. Ini setup yang secara matematis menguntungkan.")
    elif rr < 1.5:
        cautions.append(f"Risk:Reward hanya 1:{rr} — terlalu kecil untuk daily trade. Setup ideal minimal 1:2.")

    # ── Buat VERDICT berdasarkan bobot argumen ──
    score_pros  = len(pros)
    score_cons  = len(cons)
    score_caut  = len(cautions)

    if "STRONG BUY" in signal or ("BUY" in signal and score_cons == 0 and score_pros >= 4):
        verdict_title = f"✅ LAYAK DIBELI — Setup {name} Tergolong Kuat"
        verdict_color = "#00ff99"
        confidence    = "TINGGI"
        conf_color    = "#00ff99"
        verdict_open  = f"Berdasarkan analisis multi-faktor dengan skor {score}/100, saham <b>{name}</b> pada harga Rp {cl:,.0f} menunjukkan setup beli yang kuat untuk daily trade hari ini."
    elif "BUY" in signal and score_cons <= 1:
        verdict_title = f"🟡 BOLEH DIPERTIMBANGKAN — Setup {name} Cukup Layak"
        verdict_color = "#ffcc00"
        confidence    = "SEDANG"
        conf_color    = "#ffcc00"
        verdict_open  = f"Dengan skor {score}/100, saham <b>{name}</b> di harga Rp {cl:,.0f} memiliki setup yang cukup layak untuk daily trade, namun ada beberapa hal yang perlu diperhatikan."
    elif "SELL" in signal or "WEAK" in signal or score_cons >= 3:
        verdict_title = f"❌ TIDAK DISARANKAN — {name} Belum Siap Dibeli"
        verdict_color = "#ff4466"
        confidence    = "RENDAH"
        conf_color    = "#ff4466"
        verdict_open  = f"Skor {score}/100 dan data teknikal menunjukkan bahwa saham <b>{name}</b> di harga Rp {cl:,.0f} belum memiliki setup yang aman untuk daily trade saat ini."
    else:
        verdict_title = f"⏳ TUNGGU KONFIRMASI — {name} Dalam Fase Transisi"
        verdict_color = "#aaaaff"
        confidence    = "MENUNGGU"
        conf_color    = "#aaaaff"
        verdict_open  = f"Skor {score}/100 menunjukkan {name} sedang dalam fase transisi. Ada campuran sinyal positif dan negatif — lebih bijak untuk menunggu konfirmasi lebih jelas sebelum masuk."

    # ── Rakitan KESIMPULAN AKHIR ──
    if "BUY" in signal and "WEAK" not in signal:
        closing = (
            f"<b>Kesimpulan:</b> Masuk di area Rp {cl:,.0f}–{cl*1.005:,.0f}, "
            f"pasang Stop Loss di Rp {sl:,.0f} (−{((cl-sl)/cl*100):.1f}%), "
            f"target Take Profit di Rp {tp:,.0f} (+{((tp-cl)/cl*100):.1f}%). "
            f"Estimasi hold 1–3 hari trading."
        )
    else:
        closing = (
            f"<b>Alternatif:</b> Masukkan {name} ke watchlist dan tunggu RSI turun ke 40–55, "
            f"atau tunggu konfirmasi MACD golden cross sebelum memutuskan masuk."
        )

    # ── Bangun HTML ──
    pros_html  = "".join([f"<li style='margin-bottom:6px;color:#b0ffcc'>✅ {p}</li>" for p in pros])
    cons_html  = "".join([f"<li style='margin-bottom:6px;color:#ffaaaa'>❌ {c}</li>" for c in cons])
    caut_html  = "".join([f"<li style='margin-bottom:6px;color:#ffeebb'>⚠️ {w}</li>" for w in cautions])

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
            ⚠️ Analisis ini bersifat teknikal dan tidak memperhitungkan fundamental, news, atau kondisi makro.
            Selalu gunakan manajemen risiko yang ketat. Bukan saran investasi.
        </p>
    </div>
    """
    return html, confidence, conf_color


def interpret_scanner_row(row, ihsg_change=0.0):
    """Short 2-line verdict for scanner table rows."""
    name    = row['Ticker']
    score   = row['Score']
    signal  = row['Signal']
    rsi     = row['RSI']
    vsurge  = row['🔥'] == "🔥"
    macd_ok = row['MACD'] == "✅"
    ema_ok  = row['EMA20'] == "✅"
    pat     = row.get('Pattern','—')
    rr_str  = row.get('R:R','1:0')

    # Build one-liner reasons
    reasons = []
    if score >= 70:     reasons.append(f"skor tinggi ({score}/100)")
    if vsurge:          reasons.append("volume surge terkonfirmasi 🔥")
    if macd_ok:         reasons.append("MACD bullish")
    if ema_ok:          reasons.append("di atas EMA20")
    if 40<=rsi<=60:     reasons.append(f"RSI ideal ({rsi})")
    elif rsi < 35:      reasons.append(f"RSI oversold ({rsi}) — potensi rebound")

    warnings = []
    if not ema_ok:      warnings.append("harga di bawah EMA20")
    if not macd_ok:     warnings.append("MACD masih bearish")
    if rsi > 70:        warnings.append(f"RSI overbought ({rsi})")
    if not vsurge:      warnings.append("volume belum surge")
    if ihsg_change < -0.5: warnings.append("IHSG sedang melemah")

    if "STRONG" in signal and not warnings:
        verdict = f"🟢 <b>BUY SEKARANG</b> — {', '.join(reasons[:3])}. Setup premium, risiko rendah."
    elif "BUY" in signal and len(warnings) <= 1:
        w_note = f" Perhatikan: {warnings[0]}." if warnings else ""
        verdict = f"🟡 <b>BUY dengan sizing kecil</b> — {', '.join(reasons[:2])}.{w_note}"
    elif warnings:
        verdict = f"⏳ <b>Tunggu konfirmasi</b> — {', '.join(warnings[:2])}. Masuk setelah ada konfirmasi reversal."
    else:
        verdict = f"👀 <b>Watchlist</b> — Setup sedang terbentuk, belum ideal untuk entry sekarang."

    return verdict


# ─────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────
st.markdown("""
<h1 style='text-align:center;color:#00bbff;letter-spacing:3px;font-family:monospace;'>
⚡ IDX TERMINAL v4 — SMART SCANNER
</h1>
<p style='text-align:center;color:#445566;font-family:monospace;'>
Multi-Factor Daily Trade Analyzer · IDX30 / LQ45 / IDX80 / Growth30 / SMC · 180+ Universe
</p>
""", unsafe_allow_html=True)

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
        df=analyze_full(target,period=tf)
    if df is not None:
        score,detail=score_ticker(df)
        signal,sig_color,sl,tp,rr=get_signal(df,score)
        l=df.iloc[-1]
        pats=detect_patterns(df); vr,vlbl,vsurge=volume_analysis(df)
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
        with c3: st.metric("RSI (14)",f"{rsi:.1f}",delta="Oversold" if rsi<35 else ("Overbought" if rsi>70 else "Normal"))
        with c4: st.metric("Volume",vlbl,delta="🔥 SURGE" if vsurge else None)
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

        # ── INTERPRETASI KALIMAT ──
        interp_html, conf_lbl, conf_clr = interpret_analysis(
            target, score, detail, signal, df, sl, tp, rr,
            pats, vr, vsurge, ihsg_change
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
        fig.add_hline(y=70,line_dash="dot",line_color="red",row=3,col=1)
        fig.add_hline(y=30,line_dash="dot",line_color="green",row=3,col=1)
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
# SMART SCANNER — INDEX-BASED UNIVERSE
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

# Show universe info
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

# Pre-scan filter options
with st.expander("⚙️ Filter Tambahan (Advanced)", expanded=False):
    fc1,fc2,fc3=st.columns(3)
    with fc1:
        min_vol_ratio=st.slider("Min Volume Ratio:",0.5,3.0,1.0,0.1)
        require_surge=st.checkbox("Wajib Volume Surge (>1.5x)",value=False)
    with fc2:
        min_rsi=st.slider("RSI Min:",10,50,30)
        max_rsi=st.slider("RSI Max:",50,90,70)
    with fc3:
        require_macd_bull=st.checkbox("Wajib MACD Bullish Cross",value=False)
        require_above_ema=st.checkbox("Wajib Price > EMA20",value=True)

if st.button("🚀 MULAI SCAN SEKARANG",use_container_width=True,type="primary"):
    tickers_to_scan = add_jk(combined_universe)
    results=[]
    prog=st.progress(0); status=st.empty()
    errors=0

    for i,t in enumerate(tickers_to_scan):
        prog.progress((i+1)/len(tickers_to_scan))
        status.markdown(f"🔍 Scanning **{t}** ... ({i+1}/{len(tickers_to_scan)}) | Candidates so far: **{len(results)}**")
        try:
            d=clean_df(yf.download(t,period="60d",progress=False))
            if d.empty or len(d)<52: continue

            # Quick pre-filter (tanpa kalkulasi berat)
            d['ema20_q']=ta.ema(d['close'],length=20)
            d['rsi_q']=ta.rsi(d['close'],length=14)
            last=d.iloc[-1]
            rsi_q=safe_float(last['rsi_q'])
            if not (min_rsi<=rsi_q<=max_rsi): continue
            if require_above_ema and safe_float(last['close'])<safe_float(last['ema20_q']): continue

            # Full score
            sc_val,sc_det=score_ticker(d)
            if sc_val<min_score: continue

            sig,_,sl_v,tp_v,rr_v=get_signal(d,sc_val)
            if "SELL" in sig or "WEAK" in sig: continue
            if signal_filter=="Strong BUY Only" and "STRONG" not in sig: continue
            if signal_filter=="Semua BUY" and "BUY" not in sig: continue

            vr,vlbl,vsurge=volume_analysis(d)
            if require_surge and not vsurge: continue
            if vr<min_vol_ratio: continue

            macd_df2=ta.macd(d['close'],fast=12,slow=26,signal=9)
            if macd_df2 is not None and not macd_df2.empty:
                mc=safe_float(macd_df2.iloc[-1,0]); ms2=safe_float(macd_df2.iloc[-1,1])
            else: mc=ms2=0
            if require_macd_bull and mc<=ms2: continue

            pats=detect_patterns(d)
            cl=safe_float(last['close'])

            # Tambah ke hasil
            results.append({
                "Ticker":     t.replace(".JK",""),
                "Score":      sc_val,
                "Signal":     sig,
                "Price":      int(cl),
                "RSI":        round(rsi_q,1),
                "Vol":        vlbl,
                "🔥":         "🔥" if vsurge else "",
                "MACD":       "✅" if mc>ms2 else "❌",
                "EMA20":      "✅" if cl>safe_float(last['ema20_q']) else "❌",
                "SL":         int(sl_v),
                "TP":         int(tp_v),
                "R:R":        f"1:{rr_v}",
                "Pattern":    pats[0] if pats else "—",
                "Trend_s":    sc_det.get('Trend',0),
                "Mom_s":      sc_det.get('Momentum',0),
                "_cl":        cl,
                "_vr":        vr,
                "_vsurge":    vsurge,
            })
        except: errors+=1; continue

    prog.empty(); status.empty()

    if results:
        df_res=pd.DataFrame(results).sort_values("Score",ascending=False).head(top_n)

        # Generate per-row verdict
        df_res['Verdict'] = df_res.apply(lambda r: interpret_scanner_row(r, ihsg_change), axis=1)

        # Color styling
        def color_score(val):
            if val>=70: return 'background-color:#004422;color:#00ff99'
            elif val>=55: return 'background-color:#332200;color:#ffcc00'
            else: return 'background-color:#2a0010;color:#ff8888'

        display_cols=["Ticker","Score","Signal","Price","RSI","Vol","🔥","MACD","EMA20","SL","TP","R:R","Pattern"]
        styled=df_res[display_cols].style.map(color_score,subset=['Score'])
        st.dataframe(styled,use_container_width=True,hide_index=True)

        st.success(f"✅ **{len(df_res)} saham kandidat** dari {len(tickers_to_scan)} yang discan | Errors: {errors}")

        # VERDICT TABLE — interpretasi kalimat per saham
        st.markdown("### 📝 Interpretasi Tiap Saham")
        for _, row in df_res.iterrows():
            score_v = row['Score']
            sc_clr  = "#00ff99" if score_v>=70 else ("#ffcc00" if score_v>=55 else "#ff4466")
            verdict_html = row['Verdict']
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
                <div style='flex:1;color:#bbc;font-size:13px;line-height:1.7'>{verdict_html}</div>
                <div style='min-width:110px;text-align:right;font-size:11px;color:#556'>
                    RSI: {row['RSI']}<br>
                    Vol: {row['Vol']} {row['🔥']}<br>
                    MACD: {row['MACD']}<br>
                    <span style='color:#ff6666'>SL: {row['SL']:,}</span><br>
                    <span style='color:#66ff99'>TP: {row['TP']:,}</span><br>
                    <span style='color:#aaaaff'>{row['R:R']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # TOP 3 SPOTLIGHT with full narrative
        st.markdown("### 🏆 Top 3 Setup Terbaik — Analisis Lengkap")
        top3=df_res.head(3)
        for i,(_, row) in enumerate(top3.iterrows()):
            sc2    = ("score-high" if row['Score']>=65 else "score-mid")
            tg     = ("tag-sbuy"  if "STRONG" in row['Signal'] else "tag-buy")
            medal  = ["🥇","🥈","🥉"][i]
            sc_clr = "#00ff99" if row['Score']>=70 else "#ffcc00"

            # Try to load full df for deep interpretation
            try:
                df_top = analyze_full(f"{row['Ticker']}.JK", period="60d")
                if df_top is not None:
                    sc_v2, det_v2 = score_ticker(df_top)
                    sig_v2, _, sl_v2, tp_v2, rr_v2 = get_signal(df_top, sc_v2)
                    pats_v2 = detect_patterns(df_top)
                    vr_v2, _, vs_v2 = volume_analysis(df_top)
                    full_html, conf_lbl, conf_clr = interpret_analysis(
                        f"{row['Ticker']}.JK", sc_v2, det_v2, sig_v2,
                        df_top, sl_v2, tp_v2, rr_v2, pats_v2, vr_v2, vs_v2, ihsg_change
                    )
                else:
                    full_html = f"<p style='color:#556'>Interpretasi detail tidak tersedia.</p>"
                    conf_lbl, conf_clr = "—", "#666"
            except:
                full_html = f"<p style='color:#556'>Interpretasi detail tidak tersedia.</p>"
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
                        📦 Volume: <b>{row['Vol']} {row['🔥']}</b><br>
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

        # DISTRIBUTION CHART
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

        # MARKET REVIEW
        st.divider()
        st.subheader("📋 Morning Review — Panduan Eksekusi")
        mktbias="🟢 BULLISH" if ihsg_change>0.3 else ("🔴 BEARISH" if ihsg_change<-0.3 else "🟡 SIDEWAYS")
        strong_picks=[r['Ticker'] for _,r in df_res.iterrows() if "STRONG" in r['Signal']]
        surge_picks=[r['Ticker'] for _,r in df_res.iterrows() if r['🔥']=="🔥"]

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
        <li>R:R wajib ≥ 1:2 sebelum eksekusi. Skip jika R:R {'<'} 1:1.5.</li>
        <li>MACD Bullish Cross ✅ + RSI 40–60 + Volume Surge = <b>trifecta signal terkuat</b>.</li>
        <li>Gunakan max 20–25% modal per saham. Jangan all-in satu emiten.</li>
        </ol>
        </div>
        """,unsafe_allow_html=True)
    else:
        st.warning(f"Tidak ada saham yang memenuhi semua kriteria. Coba turunkan min score atau longgarkan filter.")
        st.info(f"Total discan: {len(tickers_to_scan)} | Errors: {errors}")
