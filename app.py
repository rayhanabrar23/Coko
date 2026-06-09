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
    page_title="DASHBOARD SCREENING STOCK ID",
    page_icon="💵",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
body, .stApp { background-color: #07090f; color: #d0d8e8; }
.block-container { padding-top: 1.2rem; padding-bottom: 1rem; }

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

.score-high { color: #00ff99; font-size: 28px; font-weight: 900; }
.score-mid  { color: #ffcc00; font-size: 28px; font-weight: 900; }
.score-low  { color: #ff4466; font-size: 28px; font-weight: 900; }

.regime-trend    { background:#003322; color:#00ff99; padding:4px 12px; border-radius:20px; font-weight:700; font-size:13px; }
.regime-range    { background:#332200; color:#ffcc00; padding:4px 12px; border-radius:20px; font-weight:700; font-size:13px; }
.regime-transit  { background:#1a1a33; color:#8888ff; padding:4px 12px; border-radius:20px; font-weight:700; font-size:13px; }

.tag-sbuy { background:#004422; color:#00ff99; padding:3px 10px; border-radius:20px; font-weight:700; font-size:13px; }
.tag-buy  { background:#002e18; color:#44dd88; padding:3px 10px; border-radius:20px; font-weight:700; font-size:13px; }
.tag-hold { background:#332200; color:#ffcc00; padding:3px 10px; border-radius:20px; font-weight:700; font-size:13px; }
.tag-sell { background:#330011; color:#ff4466; padding:3px 10px; border-radius:20px; font-weight:700; font-size:13px; }

.corp-warn { background:#2a1500; border:1px solid #ff8800; border-radius:8px;
             padding:8px 12px; margin:4px 0; font-size:12px; color:#ffaa44; }
.gap-stat  { background:#0d1628; border-radius:8px; padding:8px 12px;
             font-size:12px; color:#aac; margin:4px 0; }
.sizing-box { background:#001a0a; border:1px solid #00aa44; border-radius:10px;
              padding:12px 16px; margin:8px 0; }

.trade-row {
    background:#0a1020; border-radius:8px; border:1px solid #1e3050;
    padding:10px 14px; margin:4px 0; font-size:13px;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# UNIVERSE DATA — dari IDX resmi per 09 Jun 2026
# ─────────────────────────────────────────────

# Konstituen resmi per evaluasi Apr 2026 (berlaku 4 Mei – 31 Jul 2026)
IDX30 = ["AADI","ADMR","ADRO","AMRT","ANTM","ASII","BBCA","BBNI","BBRI","BMRI",
         "BRPT","BUMI","CPIN","EMTK","EXCL","GOTO","ICBP","INCO","INDF","INKP",
         "JPFA","KLBF","MBMA","MDKA","MEDC","PGAS","PGEO","PTBA","TLKM","TOWR",
         "UNTR","UNVR"]

LQ45 = ["AADI","ADMR","ADRO","AKRA","AMMN","AMRT","ANTM","ASII","BBCA","BBNI",
        "BBRI","BBTN","BMRI","BRPT","BUMI","CPIN","CUAN","DEWA","EMTK","ESSA",
        "EXCL","GOTO","HRTA","ICBP","INCO","INDF","INKP","ISAT","ITMG","JPFA",
        "KLBF","MAPI","MBMA","MDKA","MEDC","PGAS","PGEO","PTBA","SCMA","SMGR",
        "TLKM","TOWR","UNTR","UNVR","WIFI"]

IDX80 = list(dict.fromkeys(IDX30 + LQ45 + [
    "ACES","AKRA","AMMN","ARTO","BBHI","BBTN","BDMN","BELI","BNGA","BRIS",
    "BSDE","CTRA","DCII","DSSA","GEMS","GGRM","HEAL","HMSP","INTP","ISAT",
    "ITMG","JSMR","KLBF","MAPI","MDKA","MIKA","MTEL","MYOR","NCKL","NISP",
    "PNBN","PWON","SILO","SMGR","SMRA","SSIA","TAPG","TBIG","TINS","TOWR"
]))[:80]

IDX_HIDIV20 = ["ADRO","ANTM","ASII","BBCA","BBNI","BBRI","BMRI","CPIN","GGRM","HMSP",
               "INDF","ITMG","KLBF","MEDC","PGAS","PTBA","SMGR","TLKM","UNTR","UNVR"]

IDX_GROWTH30 = ["ARTO","BELI","BREN","BRIS","BUKA","CBDK","CMRY","CUAN","DCII","DEWA",
                "DSSA","EMTK","GOTO","HEAL","HRTA","MIKA","MDKA","MTEL","NCKL","PGEO",
                "SILO","TBIG","TOWR","VKTR","AMMN","AADI","BRMS","MBMA","TCPI","WIFI"]

# Sektor resmi IDX — 11 sektor
SECTORS = {
    "Energy":                  ["ABMM","AKRA","AADI","ADRO","BIPI","BSSR","BULL","BUMI","BYAN","CUAN","DEWA","DOID","DSSA","ELSA","ENRG","GEMS","HRUM","INDY","ITMG","MBAP","MEDC","MYOH","PGAS","PTBA","PTRO","RAJA","TCPI","TOBA","TPMA","WINS"],
    "Financials":              ["ARTO","BBCA","BBHI","BBNI","BBRI","BBTN","BDMN","BJBR","BJTM","BKSW","BMRI","BNGA","BNII","BNLI","BRIS","BSIM","BTPN","MEGA","NISP","NOBU","PNBN","PNBS","BFIN","ADMF","AGRO","ADMG","SMMA","SRTG"],
    "Basic Materials":         ["AMMN","ANTM","BRMS","BRPT","ESSA","INCO","INKP","INTP","ISSP","MBMA","MDKA","NCKL","NIKL","SMGR","SMCB","TINS","TKIM","TPIA","ZINC","AKPI","ALDO","ALKA","DPNS","EKAD","FASW","IGAR","INAI","FPNI","SMBR","SPMA"],
    "Consumer Cyclicals":      ["ACES","AUTO","BRAM","CSAP","ERAA","FAST","GJTL","IMAS","INDS","LPPF","MAPI","MAPA","MAPB","MNCN","MPMX","RALS","SCMA","SMSM","VKTR","MDIY","FILM","HRTA","WOOD","BOGA","PJAA","SHID","BMTR","PBRX"],
    "Consumer Non-Cyclicals":  ["AALI","AMRT","BISI","CEKA","CPIN","DLTA","GGRM","HMSP","ICBP","INDF","JPFA","KLBF","LSIP","MYOR","ROTI","SGRO","SIDO","SIMP","SKBM","SMAR","SSMS","STTP","TAPG","TBLA","TCID","ULTJ","UNVR","CMRY","GOOD","KEJU"],
    "Healthcare":              ["DVLA","HEAL","INAF","KAEF","KLBF","MERK","MIKA","PYFA","SAME","SIDO","SILO","SOHO","TSPC","BMHS","RSGK","PRDA","PEHA","IRRA","MEDS","LABS","CARE","DGNS"],
    "Industrials":             ["AMFG","ASII","ARNA","ASGR","HEXA","IMPC","JECC","KBLI","KBLI","LION","SCCO","TOTO","UNTR","VOKS","ZBRA","MARK","CAKK","SMIL","BOLT","SMSM"],
    "Infrastructures":         ["BREN","DCII","EXCL","IBST","ISAT","JSMR","LINK","MTEL","PGEO","POWR","SSIA","SUPR","TBIG","TLKM","TOWR","WIKA","WSKT","ADHI","PTPP","TOTL","ACST","JKON","NRCA","MORA","GHON","INET","ARKO"],
    "Properties & RE":         ["BSDE","CBDK","CTRA","DMAS","DUTI","INPP","JRPT","KIJA","LPCK","LPKR","MKPI","MMLP","MTLA","PANI","PWON","RDTX","SMRA","APLN","ASRI","BEST","DART","DILD","EMDE","GMTD","GPRA","LPLI","MDLN","PLIN","CITY","URBN"],
    "Technology":              ["ATIC","BELI","BUKA","DCII","DMMX","EMTK","GOTO","KIOS","LUCK","MCAS","MLPT","MTDL","NFCX","PTSN","WIFI","AXIO","CHIP","CYBR","EDGE","KREN","TECH","AWAN"],
    "Transportation & Logistic":["ASSA","BIRD","GIAA","IMJS","NELY","SAFE","SMDR","TMAS","WEHA","HELI","TRUK","TNCA","SAPX","JAYA","LAJU","GTRA","KLAS","BLOG"],
}

# Proxy untuk heatmap sektor (pilih saham paling liquid per sektor)
SECTOR_PROXY = {
    "Energy":                   "ADRO",
    "Financials":               "BBCA",
    "Basic Materials":          "ANTM",
    "Consumer Cyclicals":       "MAPI",
    "Consumer Non-Cyclicals":   "ICBP",
    "Healthcare":               "KLBF",
    "Industrials":              "ASII",
    "Infrastructures":          "TLKM",
    "Properties & RE":          "BSDE",
    "Technology":               "GOTO",
    "Transportation & Logistic":"BIRD",
}

# Saham Pemantauan Khusus — auto-exclude dari scanner
PEMANTAUAN_KHUSUS = {
    "ABBA","ACST","AKKU","ALMI","ALTO","ARTI","ASMI","BATA","BEKS","BHIT",
    "BIKA","BIMA","BLTA","BLTZ","BSWD","BTEK","BTEL","CANI","CMPP","CNKO",
    "DEWA","DOID","ELTY","ENRG","ETWA","FPNI","GIAA","GTBO","HADE","IATA",
    "IIKP","IKAI","INAF","INDX","INRU","KARW","KBRI","KOPI","KRAS","LAPD",
    "LPIN","MDRN","META","MFMI","MIRA","MITI","MYTX","NIRO","OKAS","PANR",
    "PKPK","PSAB","PSKT","RIMO","RIGS","SAFE","SDMU","SILI","SIMA","SMRU",
    "SOCI","SONA","SQMI","SSTM","SUGI","SULI","TAXI","TFCO","TIRT","TRAM",
    "TRIO","UNIT","UNSP","VIVA","WAPO","WSKT","WTON","YPAS","ZBRA","BBYB",
}

UNIVERSES = {
    "IDX30 — Blue Chip":              IDX30,
    "LQ45 — Liquid 45":               LQ45,
    "IDX80 — Broad Market":           IDX80,
    "IDX High Dividend 20":           IDX_HIDIV20,
    "IDX Growth 30":                  IDX_GROWTH30,
    "ALL Sektor (semua)": list(dict.fromkeys([t for tickers in SECTORS.values() for t in tickers])),
}

# Biaya transaksi per broker (roundtrip %)
BROKER_FEES = {
    "Ajaib / Neo (0.1% + 0.1%)":       0.20,
    "Stockbit (0.1% + 0.2%)":          0.30,
    "BNI Sekuritas (0.15% + 0.25%)":   0.40,
    "Mandiri Sekuritas (0.18% + 0.28%)":0.46,
    "MNC / lainnya (0.2% + 0.3%)":     0.50,
}
# Tambahan levy + VAT IDX (fixed per transaksi, approx)
IDX_LEVY = 0.04  # 0.04% per sisi, total ~0.08%

TZ_JKT   = pytz.timezone("Asia/Jakarta")
TRACKER       = Path("idx_trade_log.json")
WATCHLIST_FILE = Path("idx_watchlist.json")

def load_watchlist():
    if WATCHLIST_FILE.exists():
        with open(WATCHLIST_FILE) as f: return json.load(f)
    return []

def save_watchlist(tickers: list):
    with open(WATCHLIST_FILE, "w") as f: json.dump(tickers, f)
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
# FIX 1: SMART CACHE TTL — POST-MARKET AWARE
# ─────────────────────────────────────────────
def get_cache_ttl():
    """
    Setelah 16:15 WIB (data closing sudah final),
    cache sampai 09:00 esok hari — data tidak berubah semalam.
    Sebelum market close, cache 30 menit saja.
    """
    now = datetime.now(TZ_JKT)
    market_close = now.replace(hour=16, minute=15, second=0, microsecond=0)
    next_open    = (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
    # Skip weekend
    if next_open.weekday() >= 5:
        days_ahead = 7 - next_open.weekday()
        next_open  = next_open + timedelta(days=days_ahead)
    if now >= market_close:
        ttl = int((next_open - now).total_seconds())
        return max(ttl, 3600)  # minimal 1 jam
    return 1800  # saat market buka: 30 menit

# ─────────────────────────────────────────────
# IDX EOD DATA LOADER
# ─────────────────────────────────────────────
@st.cache_data(ttl=get_cache_ttl(), show_spinner=False, hash_funcs={"streamlit.runtime.uploaded_file_manager.UploadedFile": lambda f: f.name})
def load_idx_eod(uploaded_file):
    """
    Parse Ringkasan_Saham-YYYYMMDD.xlsx dari IDX.
    Returns dict: {ticker: {net_foreign, foreign_buy, foreign_sell,
                             nilai, frekuensi, bid, ask, bid_vol, ask_vol,
                             close, prev_close, pct_change}}
    """
    df = pd.read_excel(uploaded_file, header=0)
    result = {}
    for _, row in df.iterrows():
        ticker = str(row.get('Kode Saham', '')).strip()
        if not ticker or ticker == 'nan': continue
        try:
            fb   = float(row.get('Foreign Buy',  0) or 0)
            fs   = float(row.get('Foreign Sell', 0) or 0)
            close = float(row.get('Penutupan',   0) or 0)
            prev  = float(row.get('Sebelumnya',  0) or 0)
            result[ticker] = {
                'foreign_buy':  fb,
                'foreign_sell': fs,
                'net_foreign':  fb - fs,
                'nilai':        float(row.get('Nilai',      0) or 0),
                'frekuensi':    int(row.get('Frekuensi',    0) or 0),
                'ask':          float(row.get('Offer',      0) or 0),
                'ask_vol':      float(row.get('Offer Volume', 0) or 0),
                'bid':          float(row.get('Bid',        0) or 0),
                'bid_vol':      float(row.get('Bid Volume', 0) or 0),
                'close':        close,
                'prev_close':   prev,
                'pct_change':   round((close - prev) / prev * 100, 2) if prev > 0 else 0,
                'volume':       float(row.get('Volume',     0) or 0),
            }
        except: continue
    return result
    
# ─────────────────────────────────────────────
# CORE: FETCH + INDICATORS
# FIX 2: Fetch 1y untuk EMA200 valid, trim display ke 6mo
# FIX 3: Validasi volume data IDX
# ─────────────────────────────────────────────
@st.cache_data(ttl=get_cache_ttl(), show_spinner=False)
def fetch_df(ticker, period="6mo"):
    # Selalu fetch minimal 1y agar EMA200 konvergen
    fetch_period = "1y" if period in ("6mo","3mo") else period
    df = clean_df(yf.download(ticker, period=fetch_period, progress=False, timeout=10))
    if df.empty or len(df) < 52: return None
    df = df.copy()

    # ── FIX: Validasi volume IDX (yfinance sering underreport) ──
    median_vol = df['volume'].median()
    df.attrs['volume_suspect'] = bool(median_vol < 500_000)  # < 5000 lot
    df.attrs['avg_daily_value'] = float(
        (df['close'] * df['volume']).tail(20).mean()
    )  # estimasi nilai transaksi harian (Rupiah)

    # Trend
    df['ema20']  = ta.ema(df['close'], length=20)
    df['ema50']  = ta.ema(df['close'], length=50)
    df['ema200'] = ta.ema(df['close'], length=200)  # sekarang valid karena 1y data

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
        df['dmp'] = adx_df.iloc[:, 1]
        df['dmn'] = adx_df.iloc[:, 2]
    else:
        df['adx'] = df['dmp'] = df['dmn'] = 20

    # Volume
    df['vol_ma20'] = df['volume'].rolling(20).mean()
    df['vol_ratio'] = df['volume'] / df['vol_ma20'].replace(0, np.nan)

    # ── FIX 4: Overnight gap statistics ──
    df['overnight_gap_pct'] = (
        (df['open'] - df['close'].shift(1)) / df['close'].shift(1) * 100
    )

    # ── FIX 5: IHSG Beta rolling 20 hari ──
    # Disimpan di attrs, dihitung terpisah untuk efisiensi
    df.attrs['beta_20d'] = None  # akan diisi oleh calc_beta()
    df.attrs['ticker_name'] = ticker.replace(".JK", "")
    
    # Trim ke period yang diminta untuk display
    if period == "6mo":
        cutoff = df.index[-1] - pd.DateOffset(months=6)
        df = df[df.index >= cutoff]
    elif period == "3mo":
        cutoff = df.index[-1] - pd.DateOffset(months=3)
        df = df[df.index >= cutoff]

    if len(df) < 30: return None
    return df

@st.cache_data(ttl=get_cache_ttl(), show_spinner=False)
def fetch_ihsg(period="1y"):
    df = clean_df(yf.download("^JKSE", period=period, progress=False))
    if df.empty: return None
    df['ret'] = df['close'].pct_change()
    return df

def calc_beta(ticker_df, ihsg_df, window=20):
    """Rolling beta terhadap IHSG, 20 hari terakhir."""
    if ticker_df is None or ihsg_df is None: return None
    try:
        t_ret = ticker_df['close'].pct_change().dropna()
        i_ret = ihsg_df['close'].pct_change().dropna()
        aligned = pd.DataFrame({'t': t_ret, 'i': i_ret}).dropna().tail(window)
        if len(aligned) < 10: return None
        cov  = aligned['t'].cov(aligned['i'])
        var  = aligned['i'].var()
        return round(cov / var, 2) if var > 0 else None
    except: return None

# ─────────────────────────────────────────────
# FIX 6: CORPORATE ACTION CHECK
# ─────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def check_corporate_actions(ticker):
    """
    Cek dividen dan splits dalam 7 hari ke depan.
    Returns list of warning strings.
    """
    warnings = []
    try:
        tk = yf.Ticker(ticker)
        today = date.today()
        lookahead = today + timedelta(days=7)

        # Cek dividen
        divs = tk.dividends
        if divs is not None and not divs.empty:
            divs.index = divs.index.tz_localize(None) if divs.index.tzinfo else divs.index
            upcoming = divs[(divs.index.date >= today) & (divs.index.date <= lookahead)]
            for idx, val in upcoming.items():
                warnings.append(f"📅 Cum-date dividen ~{idx.date()} | Nilai: Rp {val:,.0f}/lembar — harga akan adjust saat ex-date")

        # Cek splits
        splits = tk.splits
        if splits is not None and not splits.empty:
            splits.index = splits.index.tz_localize(None) if splits.index.tzinfo else splits.index
            upcoming_s = splits[(splits.index.date >= today) & (splits.index.date <= lookahead)]
            for idx, val in upcoming_s.items():
                warnings.append(f"✂️ Stock split {val}:1 pada {idx.date()} — harga akan adjust otomatis")

        # Cek earnings / calendar
        try:
            cal = tk.calendar
            if cal is not None and not cal.empty:
                # calendar bisa berupa DataFrame atau dict tergantung versi yfinance
                if isinstance(cal, pd.DataFrame) and 'Earnings Date' in cal.index:
                    earn_dates = cal.loc['Earnings Date']
                    for ed in (earn_dates if hasattr(earn_dates, '__iter__') else [earn_dates]):
                        try:
                            ed_date = pd.to_datetime(ed).date()
                            if today <= ed_date <= lookahead:
                                warnings.append(f"📊 Earnings / laporan keuangan diestimasi ~{ed_date} — volatilitas tinggi")
                        except: pass
        except: pass

    except Exception:
        pass
    return warnings

# ─────────────────────────────────────────────
# OVERNIGHT GAP ANALYSIS
# ─────────────────────────────────────────────
def overnight_gap_stats(df):
    """
    Statistik gap overnight dari historical data.
    Returns dict dengan avg_gap, gap_std, max_gap, gap_up_pct, gap_down_pct.
    """
    if df is None or 'overnight_gap_pct' not in df.columns:
        return None
    gaps = df['overnight_gap_pct'].dropna()
    if len(gaps) < 10: return None
    return {
        "avg_abs":    round(gaps.abs().mean(), 2),
        "std":        round(gaps.std(), 2),
        "max_up":     round(gaps.max(), 2),
        "max_down":   round(gaps.min(), 2),
        "gap_up_pct": round((gaps > 1.0).sum() / len(gaps) * 100, 1),    # % hari gap up > 1%
        "gap_down_pct": round((gaps < -1.0).sum() / len(gaps) * 100, 1), # % hari gap down > 1%
        "freq_large": round((gaps.abs() > 2.0).sum() / len(gaps) * 100, 1),  # % gap > 2%
    }

# ─────────────────────────────────────────────
# FIX 7: POSITION SIZING
# ─────────────────────────────────────────────
def calc_position_size(modal, risk_pct, entry, sl, broker_fee_pct, lot_size=100):
    """
    Hitung max lot berdasarkan risk management.
    modal        : total modal dalam Rupiah
    risk_pct     : max risk per trade (misal 0.02 = 2%)
    entry        : harga entry
    sl           : stop loss price
    broker_fee   : total roundtrip fee %
    """
    if entry <= sl or entry <= 0 or sl <= 0:
        return 0, 0, 0, 0

    risk_per_share = entry - sl
    max_risk_rp    = modal * risk_pct

    # Total biaya transaksi per lot
    total_fee_pct  = (broker_fee_pct + IDX_LEVY * 2) / 100
    fee_per_lot    = entry * lot_size * total_fee_pct

    # Adjust TP minimum agar profit setelah biaya
    min_tp_to_breakeven = entry * (1 + total_fee_pct)

    # Max lot dari perspektif risk
    max_lot_risk = int(max_risk_rp / (risk_per_share * lot_size))

    # Max lot dari perspektif modal (tidak boleh > 20% modal per posisi — diversifikasi)
    max_position_value = modal * 0.20
    max_lot_capital    = int(max_position_value / (entry * lot_size))

    max_lot  = min(max_lot_risk, max_lot_capital)
    max_lot  = max(max_lot, 0)

    position_value = max_lot * entry * lot_size
    actual_risk    = max_lot * risk_per_share * lot_size
    fee_total      = position_value * total_fee_pct

    return max_lot, position_value, actual_risk, fee_total

# ─────────────────────────────────────────────
# REGIME DETECTION
# ─────────────────────────────────────────────
def detect_regime(df):
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
# VOLUME DIRECTION
# ─────────────────────────────────────────────
def volume_score(df):
    last = df.iloc[-1]
    vr   = sf(last['vol_ratio'], 1.0)
    cl   = sf(last['close'])
    op   = sf(last['open'])
    is_green = cl >= op

    if vr >= 2.0:
        label = f"{vr:.1f}x 🔥🔥"
        if is_green:   return 25, label, "surge_bull"
        else:          return -20, label, "surge_bear"
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
# RSI DIVERGENCE
# ─────────────────────────────────────────────
def detect_rsi_divergence(df, lookback=14):
    if len(df) < lookback + 2: return "none"
    prices = df['close'].values[-lookback:]
    rsis   = df['rsi'].values[-lookback:]
    price_lows = [(i, prices[i]) for i in range(1, len(prices)-1)
                  if prices[i] < prices[i-1] and prices[i] < prices[i+1]]
    if len(price_lows) < 2: return "none"
    p1, p2 = price_lows[-2], price_lows[-1]
    r1, r2 = rsis[p1[0]], rsis[p2[0]]
    if p2[1] < p1[1] and r2 > r1 + 3:   return "bullish"
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

# ── TARUH SETELAH def detect_patterns(df): ──────────────────

def generate_reasoning(ticker, df, score, detail, regime, ihsg_df, sector_perfs=None):
    reasons = []
    last = df.iloc[-1]
    cl   = sf(last['close'])
    e20  = sf(last['ema20'])
    e50  = sf(last['ema50'])
    e200 = sf(last['ema200'])
    rsi  = sf(last['rsi'])
    macd = sf(last['macd'])
    sig_v= sf(last['sig'])
    hist = sf(last['hist'])
    hist_p = sf(df['hist'].iloc[-2]) if len(df) > 2 else 0
    vr   = sf(last['vol_ratio'])
    is_green = cl >= sf(last['open'])

    # ① MACRO
    if ihsg_df is not None and not ihsg_df.empty:
        ihsg_last = sf(ihsg_df['close'].iloc[-1])
        ihsg_ma20 = ihsg_df['close'].rolling(20).mean().iloc[-1]
        ihsg_chg5 = (ihsg_last - sf(ihsg_df['close'].iloc[-5])) / sf(ihsg_df['close'].iloc[-5]) * 100 if len(ihsg_df) >= 5 else 0
        if ihsg_last > ihsg_ma20 and ihsg_chg5 > 0:
            reasons.append(f"① MACRO ✅ IHSG di atas MA20, momentum {ihsg_chg5:+.1f}% (5D) — kondisi market mendukung")
        elif ihsg_last > ihsg_ma20:
            reasons.append(f"① MACRO 🟡 IHSG di atas MA20 tapi momentum flat {ihsg_chg5:+.1f}% (5D)")
        else:
            reasons.append(f"① MACRO ⚠️ IHSG di bawah MA20 ({ihsg_chg5:+.1f}% 5D) — headwind, score dikurangi otomatis")
    else:
        reasons.append("① MACRO — Data IHSG tidak tersedia")

    # ② SEKTOR
    ticker_name = ticker.replace(".JK", "")
    sektor = next((s for s, tickers in SECTORS.items() if ticker_name in tickers), None)
    if sektor and sector_perfs and sektor in sector_perfs:
        perf = sector_perfs[sektor]
        icon = "✅" if perf > 0.5 else ("🟡" if perf > -0.5 else "⚠️")
        reasons.append(f"② SEKTOR {icon} {sektor}: {perf:+.2f}% (5D) — {'outperform' if perf > 0 else 'underperform'}")
    elif sektor:
        reasons.append(f"② SEKTOR — {sektor} (performa 5D tidak tersedia)")
    else:
        reasons.append("② SEKTOR — Tidak ditemukan di mapping sektor")

    # ③ TREND
    if cl > e20 > e50 > e200 > 0:
        reasons.append("③ TREND ✅ Full alignment: Harga > EMA20 > EMA50 > EMA200 — struktur uptrend sempurna")
    elif cl > e20 > e50:
        reasons.append("③ TREND 🟡 Harga > EMA20 > EMA50, EMA200 belum aligned — uptrend jangka pendek-menengah")
    elif cl > e20:
        reasons.append("③ TREND 🟡 Harga di atas EMA20 saja — trend jangka pendek, konfirmasi lemah")
    else:
        reasons.append("③ TREND ⚠️ Harga di bawah EMA20 — struktur trend belum bullish")

    adx_v = sf(last['adx'])
    dmp   = sf(last['dmp'])
    dmn   = sf(last['dmn'])
    if adx_v > 25 and dmp > dmn:
        reasons.append(f"   ADX {adx_v:.0f} > 25 dengan DI+ > DI- — trend kuat dan valid ✅")
    elif adx_v > 20:
        reasons.append(f"   ADX {adx_v:.0f} — trend mulai terbentuk 🟡")
    else:
        reasons.append(f"   ADX {adx_v:.0f} < 20 — pasar masih sideways/ranging")

    # ④ MOMENTUM
    macd_status = ""
    if macd > sig_v and hist > 0 and hist > hist_p:
        macd_status = "MACD golden cross + histogram naik ✅"
    elif macd > sig_v:
        macd_status = "MACD bullish tapi histogram melemah 🟡"
    else:
        macd_status = "MACD masih bearish ⚠️"

    rsi_note = ""
    if regime == "trending":
        if 50 <= rsi <= 70:   rsi_note = f"RSI {rsi:.0f} zona sehat trending ✅"
        elif rsi > 70:        rsi_note = f"RSI {rsi:.0f} overbought — hati-hati ⚠️"
        else:                 rsi_note = f"RSI {rsi:.0f} belum konfirmasi momentum 🟡"
    else:
        if 30 <= rsi <= 45:   rsi_note = f"RSI {rsi:.0f} oversold recovery — potensi bouncing ✅"
        elif rsi < 30:        rsi_note = f"RSI {rsi:.0f} sangat oversold 🟡"
        else:                 rsi_note = f"RSI {rsi:.0f} netral 🟡"
    reasons.append(f"④ MOMENTUM — {rsi_note} | {macd_status}")

    # ⑤ VOLUME
    if vr >= 2.0 and is_green:
        reasons.append(f"⑤ VOLUME ✅ {vr:.1f}x rata-rata dengan candle hijau — sinyal akumulasi kuat")
    elif vr >= 1.5 and is_green:
        reasons.append(f"⑤ VOLUME ✅ {vr:.1f}x rata-rata — volume di atas normal, konfirmasi bullish")
    elif vr >= 1.0:
        reasons.append(f"⑤ VOLUME 🟡 {vr:.1f}x rata-rata — volume cukup, {'hijau' if is_green else 'merah ⚠️'}")
    else:
        reasons.append(f"⑤ VOLUME ⚠️ {vr:.1f}x rata-rata — volume sepi, sinyal kurang meyakinkan")

    # ⑥ CANDLESTICK
    pats = detect_patterns(df)
    pat_str = pats[0] if pats and pats[0] != "—" else "Tidak ada pola signifikan"
    bullish_pats = ['Bull Engulfing','Morning Star','Bull Marubozu','Hammer']
    if any(k in pat_str for k in bullish_pats):
        reasons.append(f"⑥ PATTERN ✅ {pat_str} — pola bullish terkonfirmasi")
    elif pat_str != "Tidak ada pola signifikan":
        reasons.append(f"⑥ PATTERN 🟡 {pat_str}")
    else:
        reasons.append("⑥ PATTERN — Tidak ada pola candlestick signifikan hari ini")

    # ⑦ FOREIGN FLOW
    foreign_note = detail.get("Foreign Flow", "—")
    foreign_sig  = detail.get("Foreign Signal", 0)
    if foreign_sig > 0:
        reasons.append(f"⑦ FOREIGN ✅ {foreign_note}")
    elif foreign_sig < 0:
        reasons.append(f"⑦ FOREIGN ⚠️ {foreign_note}")
    else:
        reasons.append("⑦ FOREIGN — Tidak ada data foreign flow (upload EOD untuk aktifkan)")

    # ⑧ DIVERGENCE / BONUS
    div = detail.get("RSI Div", "none")
    if div == "bullish":
        reasons.append("⑧ BONUS ✅ RSI Bullish Divergence terdeteksi — harga lower low tapi RSI higher low, potensi reversal kuat")
    elif div == "bearish":
        reasons.append("⑧ BONUS ⚠️ RSI Bearish Divergence — waspadai pembalikan arah")
    
    bb_w = sf(last.get('bb_width', 0))
    if bb_w < 0.03:
        reasons.append("⑧ BONUS ✅ Bollinger Band Squeeze — volatilitas rendah, potensi breakout besar segera")

    return reasons

# ─────────────────────────────────────────────
# FIX 8: WEIGHTED SCORING — REGIME AWARE
# BB Bonus dipindahkan ke dalam momentum sub-score
# Market context multiplier (IHSG trend)
# ─────────────────────────────────────────────
def score_ticker(df, ihsg_df=None, idx_eod=None):
    if df is None or df.empty or len(df) < 30:
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
    if cl > e20:             t += 20
    if cl > e50:             t += 15
    if e20 > e50:            t += 15
    if e50 > e200 and e200 > 0: t += 10   # valid sekarang karena fetch 1y
    if adx_v > 30 and dmp > dmn: t += 20
    elif adx_v > 25 and dmp > dmn: t += 10
    if len(df) > 3:
        ema20_slope = sf(df['ema20'].iloc[-1]) - sf(df['ema20'].iloc[-3])
        if ema20_slope > 0: t += 10
        elif ema20_slope < 0: t -= 10
    t = max(0, min(t, 100))

    # ── MOMENTUM SCORE (raw 0–100) — BB masuk sini ──
    m = 0
    if regime == "trending":
        if 50 <= rsi <= 70:  m += 30
        elif 40 <= rsi < 50: m += 15
        elif rsi > 70:       m += 5
    else:
        if 30 <= rsi <= 45:  m += 35
        elif 45 < rsi <= 55: m += 15
        elif rsi > 70:       m -= 10
    if macd > sig:           m += 20
    if hist > 0 and hist > hist_p: m += 15
    if stk < 20 and stk > std_d:   m += 20
    elif stk < 40 and stk > std_d: m += 10
    div = detect_rsi_divergence(df)
    if div == "bullish":     m += 20
    elif div == "bearish":   m -= 15

    # FIX: BB masuk momentum, bukan additive terpisah
    if cl <= bb_l * 1.005:   m += 15   # di bawah lower = oversold momentum
    elif cl <= bb_m:          m += 8
    if bb_w < 0.03:           m += 10  # BB squeeze
    m = max(0, min(m, 100))

    # ── VOLUME SCORE ────────────────────────────
    vs_raw, vol_label, vol_type = volume_score(df)
    v = max(0, min(vs_raw + 50, 100))

    # ── PATTERN SCORE ───────────────────────────
    pats = detect_patterns(df)
    p = 0
    for pat in pats:
        if any(k in pat for k in ['Bull Engulfing','Morning Star','Bull Marubozu','Hammer']): p = 80; break
        elif 'Doji' in pat: p = max(p, 40)
        elif any(k in pat for k in ['Bear Engulfing','Evening Star','Bear Marubozu']): p = max(p, 10)
    if p == 0: p = 30

    # ── REGIME WEIGHTS ───────────────────────────
    if regime == "trending":
        weights = {"trend": 0.40, "momentum": 0.25, "volume": 0.25, "pattern": 0.10}
    elif regime == "ranging":
        weights = {"trend": 0.15, "momentum": 0.45, "volume": 0.20, "pattern": 0.20}
    else:
        weights = {"trend": 0.25, "momentum": 0.30, "volume": 0.30, "pattern": 0.15}

    raw = (t * weights["trend"] +
           m * weights["momentum"] +
           v * weights["volume"] +
           p * weights["pattern"])

    score = min(int(raw), 100)

    # ── FIX: IHSG MARKET CONTEXT MULTIPLIER ─────
    ihsg_penalty = 0
    ihsg_context = "—"
    if ihsg_df is not None and not ihsg_df.empty:
        ihsg_ma20 = ihsg_df['close'].rolling(20).mean().iloc[-1]
        ihsg_last = sf(ihsg_df['close'].iloc[-1])
        ihsg_chg5 = ((ihsg_last - sf(ihsg_df['close'].iloc[-5])) / sf(ihsg_df['close'].iloc[-5]) * 100
                     if len(ihsg_df) >= 5 else 0)
        if ihsg_last < ihsg_ma20 and ihsg_chg5 < -2.0:
            ihsg_penalty = 15
            ihsg_context = f"⚠️ IHSG di bawah MA20 & -5D {ihsg_chg5:.1f}% → -15 pts"
        elif ihsg_last < ihsg_ma20:
            ihsg_penalty = 8
            ihsg_context = f"⚠️ IHSG di bawah MA20 → -8 pts"
        elif ihsg_chg5 > 1.5:
            ihsg_context = f"✅ IHSG momentum bullish +5D {ihsg_chg5:.1f}%"

    # ── FOREIGN FLOW dari IDX EOD ─────────────────
    foreign_signal = 0
    foreign_note   = "—"
    if idx_eod:
        ticker_name = df.attrs.get('ticker_name', '')
        eod = idx_eod.get(ticker_name, {})
        if eod:
            net     = eod.get('net_foreign', 0)
            vol     = eod.get('volume', 1)
            net_pct = net / vol * 100 if vol > 0 else 0
            if net > 0 and net_pct > 20:
                foreign_signal = 15
                foreign_note   = f"✅ Asing net BUY {net/1e6:.1f}jt lembar ({net_pct:.0f}% vol)"
            elif net > 0:
                foreign_signal = 8
                foreign_note   = f"🟡 Asing net buy minor {net/1e6:.1f}jt lembar"
            elif net < 0 and abs(net_pct) > 20:
                foreign_signal = -20
                foreign_note   = f"🔴 Asing net SELL {abs(net)/1e6:.1f}jt lembar ({abs(net_pct):.0f}% vol)"
            elif net < 0:
                foreign_signal = -8
                foreign_note   = f"🟡 Asing net sell minor {abs(net)/1e6:.1f}jt lembar"

    score = max(0, min(score + foreign_signal - ihsg_penalty, 100))

    # ── GOLDEN ALIGNMENT BONUS ──────────────────
    if cl > e20 > e50 > e200 > 0:
        score = min(score + 15, 100)

    # ── VOLUME HARD RULE: Strong BUY wajib konfirmasi volume ──
    last_vr = sf(df['vol_ratio'].iloc[-1])
    if score >= 70 and last_vr < 1.3:
        score = min(score, 69)  # cap di bawah Strong BUY threshold

    # ── ADX SIDEWAYS CAP ────────────────────────
    adx_recent = df['adx'].iloc[-10:].mean() if len(df) >= 10 else adx_val
    if sf(adx_recent) < 15:
        score = min(score, 50)

    # ── BETA ─────────────────────────────────────
    beta = calc_beta(df, ihsg_df)

    detail = {
        "Regime": f"{regime.title()} (ADX {adx_val:.0f})",
        "Trend": f"{t}/100",
        "Momentum": f"{m}/100 (incl. BB)",
        "Volume": f"{v}/100 [{vol_label}]",
        "Pattern": f"{p}/100",
        "IHSG Context": ihsg_context,
        "IHSG Penalty": ihsg_penalty,
        "Foreign Flow": foreign_note,
        "Foreign Signal": foreign_signal,
        "Beta (20D)": beta if beta else "—",
        "Weights": weights,
        "RSI Div": div,
        "Vol Type": vol_type,
        "EMA200 Valid": e200 > 0,
    }
    return score, detail, regime, adx_val

# ─────────────────────────────────────────────
# TECHNICAL LEVELS — ENTRY / SL / TP
# FIX: SL berbasis ATR per regime, bukan flat %
# ─────────────────────────────────────────────
def get_levels(df, score, regime, broker_fee_pct=0.30):
    if df is None or len(df) < 20: return None, None, None, None, "—", "#888"

    last  = df.iloc[-1]
    cl    = sf(last['close'])
    e20   = sf(last['ema20'])
    atr   = sf(last['atr'])
    bb_l  = sf(last['bb_l'])
    bb_m  = sf(last['bb_m'])

    # ATR-based SL multiplier per regime
    sl_atr_mult = {
        "trending":   1.5,   # trend kuat — SL lebih longgar
        "ranging":    1.0,   # range — SL ketat di bawah support
        "transition": 1.2,
    }
    mult = sl_atr_mult.get(regime, 1.2)
    atr_sl_dist = max(atr * mult, cl * 0.01)  # minimal 1%

    # Pivot
    hv, lv, cv = sf(last['high']), sf(last['low']), cl
    pivot = (hv + lv + cv) / 3
    r1 = 2*pivot - lv;  r2 = pivot + (hv - lv)
    s1 = 2*pivot - hv;  s2 = pivot - (hv - lv)

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

    # FIX: SL berbasis ATR regime, bukan hard cap flat %
    swing_low  = df['low'].iloc[-5:].min()
    sl_atr     = entry - atr_sl_dist
    sl_swing   = swing_low * 0.99
    sl_pivot   = s1 * 0.99
    sl_options = [s for s in [sl_atr, sl_swing, sl_pivot] if 0 < s < entry]
    sl = max(sl_options) if sl_options else entry - atr_sl_dist

    # Guard: SL jangan lebih dari 8% dari entry (hard cap lebih longgar, regime-aware)
    max_sl_dist_pct = {"trending": 0.08, "ranging": 0.05, "transition": 0.06}
    max_sl_dist = entry * max_sl_dist_pct.get(regime, 0.06)
    sl = max(sl, entry - max_sl_dist)
    sl = round(sl)

    # TP — ke resistance terdekat, minimum cover biaya
    risk = max(entry - sl, entry * 0.005)
    total_fee = (broker_fee_pct + IDX_LEVY * 2) / 100
    min_tp_for_profit = entry * (1 + total_fee) + risk  # TP minimal = cover fee + 1:1 risk
    res_cands = [r for r in res_levels[:3] if r > entry] + [r1, r2]
    valid_res = [r for r in res_cands if r > entry]
    tp = min(valid_res) if valid_res else entry + risk * 2.5
    if (tp - entry) < risk * 1.8:
        tp = entry + risk * 2.5
    # Pastikan TP menutup biaya transaksi
    tp = max(tp, min_tp_for_profit)
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
     min_vr, req_surge, req_macd, min_rsi, max_rsi,
     min_daily_value, ihsg_df, broker_fee_pct, idx_eod) = args
    name = ticker.replace(".JK", "")
    try:
        df = fetch_df(ticker, "6mo")
        if df is None: return None, name, "Data kosong"
        if name in PEMANTAUAN_KHUSUS:
            return None, name, "Pemantauan Khusus — skip"

        # FIX: Filter daily value (likuiditas)
        avg_val = df.attrs.get('avg_daily_value', 0)
        if avg_val < min_daily_value:
            return None, name, f"Likuiditas rendah (Rp {avg_val/1e9:.1f}M/hari)"

        last = df.iloc[-1]
        rsi_v  = sf(last.get('rsi', 50))
        cl_v   = sf(last.get('close', 0))
        e20_v  = sf(last.get('ema20', cl_v))
        macd_v = sf(last.get('macd', 0))
        sig_v  = sf(last.get('sig', 0))
        vr_v   = sf(last.get('vol_ratio', 1.0))

        if not (min_rsi <= rsi_v <= max_rsi):   return None, name, f"RSI {rsi_v:.0f}"
        if above_ema and cl_v < e20_v:           return None, name, "< EMA20"
        if req_macd and macd_v <= sig_v:         return None, name, "MACD bearish"
        if vr_v < min_vr:                        return None, name, f"Vol {vr_v:.1f}x"

        score, detail, regime, adx_v = score_ticker(df, ihsg_df, idx_eod)
        if score < min_score:                    return None, name, f"Score {score}"

        entry, sl, tp, rr, signal, _ = get_levels(df, score, regime, broker_fee_pct)
        if entry is None:                        return None, name, "Level error"
        if "AVOID" in signal:                    return None, name, "Signal AVOID"
        if sig_filter == "Strong BUY" and "STRONG" not in signal: return None, name, "Bukan Strong BUY"
        if sig_filter == "BUY saja" and "BUY" not in signal:      return None, name, "Bukan BUY"

        _, vol_lbl, vol_type = volume_score(df)
        if req_surge and "surge" not in vol_type: return None, name, "Bukan surge"

        div   = detail.get("RSI Div", "none")
        pats  = detect_patterns(df)
        beta  = detail.get("Beta (20D)", "—")
        g_stats = overnight_gap_stats(df)
        vol_suspect = df.attrs.get('volume_suspect', False)

        return {
            "Ticker":    name,
            "Score":     score,
            "Regime":    regime.title(),
            "ADX":       round(adx_v, 1),
            "Signal":    signal,
            "Entry":     int(entry),
            "SL":        int(sl),
            "TP":        int(tp),
            "R:R":       f"1:{rr}",
            "RSI":       round(rsi_v, 1),
            "Vol":       vol_lbl,
            "VolType":   vol_type,
            "MACD":      "✅" if macd_v > sig_v else "❌",
            "Div":       "🔼" if div=="bullish" else ("🔽" if div=="bearish" else "—"),
            "Pattern":   pats[0] if pats else "—",
            "Beta":      beta if beta else "—",
            "GapAvg":    f"±{g_stats['avg_abs']}%" if g_stats else "—",
            "VolSuspect": "⚠️" if vol_suspect else "",
            "DailyVal":  f"Rp {avg_val/1e9:.1f}M",
            "IHSGNote":  detail.get("IHSG Context", "—"),
            "Foreign":   detail.get("Foreign Flow", "—"),
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
# SIDEBAR — GLOBAL SETTINGS
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Global Settings")
    st.markdown("**Position Sizing**")
    modal_total    = st.number_input("Modal Total (Rp):", value=50_000_000, step=5_000_000,
                                      format="%d", help="Total modal aktif untuk trading")
    risk_per_trade = st.slider("Max Risk per Trade:", 0.5, 5.0, 2.0, 0.5,
                                format="%.1f%%",
                                help="% modal yang berani hilang per satu trade") / 100
    broker_choice  = st.selectbox("Broker:", list(BROKER_FEES.keys()))
    broker_fee     = BROKER_FEES[broker_choice]

    st.markdown("---")
    st.markdown("**Scanner Defaults**")
    min_daily_val  = st.selectbox("Min Nilai Transaksi Harian:",
                                   ["Rp 5M", "Rp 10M", "Rp 50M", "Rp 100M"], index=1)
    min_val_map    = {"Rp 5M": 5e9, "Rp 10M": 10e9, "Rp 50M": 50e9, "Rp 100M": 100e9}
    min_daily_value = min_val_map[min_daily_val]

    st.markdown("---")
    st.markdown("**IDX EOD Data**")
    idx_eod_file = st.file_uploader(
        "Upload Ringkasan_Saham-YYYYMMDD.xlsx:",
        type=["xlsx"],
        help="Download dari idx.co.id → Data Pasar → Ringkasan Saham"
    )
    idx_eod = load_idx_eod(idx_eod_file) if idx_eod_file else {}
    if idx_eod:
        st.success(f"✅ EOD loaded: {len(idx_eod)} saham")
    else:
        st.caption("Belum ada data EOD — foreign flow tidak aktif")

    st.markdown("---")
    st.markdown("**📌 Watchlist Persistent**")
    wl_current = load_watchlist()
    wl_input = st.text_input(
        "Tambah ke watchlist (pisah koma):",
        placeholder="BBRI, TLKM, BMRI",
        key="wl_input_sidebar"
    )
    if st.button("Simpan Watchlist", key="save_wl"):
        new_tickers = [t.strip().upper() for t in wl_input.split(",") if t.strip()]
        merged = list(dict.fromkeys(wl_current + new_tickers))
        save_watchlist(merged)
        st.success(f"✅ {len(merged)} saham tersimpan")
        wl_current = merged
    if wl_current:
        st.caption(f"📌 {len(wl_current)} saham: {', '.join(wl_current[:8])}{'...' if len(wl_current)>8 else ''}")
        if st.button("🗑️ Reset Watchlist", key="reset_wl"):
            save_watchlist([])
            st.rerun()

    st.markdown("---")
    now_jkt = datetime.now(TZ_JKT)
    ttl_val = get_cache_ttl()
    st.caption(f"🕐 WIB: {now_jkt.strftime('%H:%M')}")
    st.caption(f"💾 Cache TTL: {ttl_val//3600}j {(ttl_val%3600)//60}m")
    if now_jkt.hour >= 16:
        st.success("✅ Post-market — data closing sudah final")
    else:
        st.warning("⚠️ Market hours — data belum final")

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
st.markdown("""
<h1 style='text-align:center; color:#00bbff; margin-bottom:4px; letter-spacing:2px;'>DASHBOARD SCREENING STOCK ID</h1>
<p style='text-align:center; color:#445566; margin-bottom:1rem;'>
Regime-Aware · Volume Direction · RSI Divergence · Position Sizing · Gap Analysis · Corp Action Check · IHSG Context
</p>
""", unsafe_allow_html=True)

auto_resolve()

# Load IHSG sekali untuk dipakai semua tab
ihsg_df_global = fetch_ihsg("1y")

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
        if ihsg_df_global is not None:
            raw = ihsg_df_global
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

            # IHSG trend context
            ihsg_ma20_last = raw['close'].rolling(20).mean().iloc[-1]
            ihsg_last_val  = raw['close'].iloc[-1]
            ihsg_chg5 = (ihsg_last_val - raw['close'].iloc[-5]) / raw['close'].iloc[-5] * 100

            if ihsg_last_val < ihsg_ma20_last and ihsg_chg5 < -2:
                st.error(f"🔴 IHSG di bawah MA20 & -5D {ihsg_chg5:.1f}% — market sedang distribusi. Score semua saham otomatis dikurangi 15 poin.")
            elif ihsg_last_val < ihsg_ma20_last:
                st.warning(f"🟡 IHSG di bawah MA20. Score semua saham dikurangi 8 poin.")
            else:
                bias = "🟢 BULLISH" if ihsg_change > 0.3 else ("🔴 BEARISH" if ihsg_change < -0.3 else "🟡 SIDEWAYS")
                st.caption(f"Market Bias: **{bias}**")

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
            st.caption(f"🏆 Terkuat: **{best['Sektor']}** ({best['Perf']:+.2f}%) | ⚠️ Terlemah: **{worst['Sektor']}** ({worst['Perf']:+.2f}%)")

    st.divider()
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
    st.subheader("Smart Scanner — Rekomendasi Malam Ini")

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
    st.caption(f"Universe aktif: **{len(universe)} saham** | Min nilai harian: **{min_daily_val}** | Broker: **{broker_choice.split('(')[0].strip()}**")

    if st.button("🚀 MULAI SCAN", use_container_width=True, type="primary"):
        tickers = add_jk(universe)
        params  = (min_score, sig_filter, above_ema, min_vr, req_surge, req_macd,
                   min_rsi, max_rsi, min_daily_value, ihsg_df_global, broker_fee, idx_eod)
        args    = [(t, *params) for t in tickers]

        prog  = st.progress(0)
        info  = st.empty()
        results = []; done = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=25) as ex:
            futs = {ex.submit(scan_one, a): a[0] for a in args}
            for fut in concurrent.futures.as_completed(futs):
                done += 1
                prog.progress(done / len(tickers))
                info.markdown(f"⚡ {done}/{len(tickers)} | Kandidat: **{len(results)}**")
                res, name, reason = fut.result()
                if res: results.append(res)

        prog.empty(); info.empty()

        if not results:
            st.warning("Tidak ada saham yang lolos filter. Coba turunkan min score atau min daily value.")
        else:
            df_res = pd.DataFrame(results).sort_values("Score", ascending=False).head(top_n)
            n_saved = save_scan_to_log(df_res, hold_period)
            if n_saved:
                st.success(f"💾 {n_saved} rekomendasi disimpan ke tracker.")

            st.markdown(f"### Top {len(df_res)} Rekomendasi — {datetime.now(TZ_JKT).strftime('%d %b %Y %H:%M')} WIB")

            show_cols = ["Ticker","Score","Regime","Signal","Entry","SL","TP","R:R",
                         "RSI","Vol","MACD","Div","Pattern","Beta","GapAvg","DailyVal","Foreign","VolSuspect"]
            st.dataframe(df_res[show_cols], use_container_width=True, hide_index=True)

            st.markdown("---")
            st.markdown("#### Detail, Sizing & Risk per Saham")

            # Hitung sector performance SEKALI untuk semua saham
            sector_perfs = {}
            for s, proxy in SECTOR_PROXY.items():
                try:
                    d = clean_df(yf.download(jk(proxy), period="10d", progress=False))
                    if d is not None and not d.empty and len(d) >= 5:
                        sector_perfs[s] = round(
                            (sf(d['close'].iloc[-1]) - sf(d['close'].iloc[-5]))
                            / sf(d['close'].iloc[-5]) * 100, 2
                        )
                except:
                    sector_perfs[s] = 0

            for _, row in df_res.iterrows():
                score_c = "#00ff99" if row['Score']>=70 else ("#ffcc00" if row['Score']>=55 else "#ff4466")
                regime_badge = (f"<span class='regime-trend'>{row['Regime']}</span>" if row['Regime']=="Trending"
                                else f"<span class='regime-range'>{row['Regime']}</span>" if row['Regime']=="Ranging"
                                else f"<span class='regime-transit'>{row['Regime']}</span>")
                sig_class = "tag-sbuy" if "STRONG" in row['Signal'] else ("tag-sell" if "AVOID" in row['Signal'] else "tag-buy")
                vol_warn = " ⚠️ <i>Volume distribusi — hati-hati!</i>" if row.get('VolType','') in ('surge_bear','bear') else ""
                vol_suspect_warn = " ⚠️ <i>Volume data suspect (yfinance)</i>" if row.get('VolSuspect') else ""
                div_note = " | 🔼 <b>RSI Bullish Divergence!</b>" if row['Div']=="🔼" else ""

                # ── Ambil data dulu, BARU build HTML ──
                df_tmp = fetch_df(jk(row['Ticker']), "6mo")

                # Position sizing
                max_lot, pos_val, actual_risk, fee_total = calc_position_size(
                    modal_total, risk_per_trade,
                    float(row['Entry']), float(row['SL']), broker_fee
                )

                # Corporate action
                corp_warns = check_corporate_actions(jk(row['Ticker']))

                # Gap stats
                g_stats = overnight_gap_stats(df_tmp) if df_tmp is not None else None

                # Reasoning
                if df_tmp is not None:
                    _, detail_tmp, _, _ = score_ticker(df_tmp, ihsg_df_global, idx_eod)
                    reasoning = generate_reasoning(
                        jk(row['Ticker']), df_tmp, row['Score'],
                        detail_tmp, row['Regime'].lower(),
                        ihsg_df_global, sector_perfs
                    )
                else:
                    reasoning = ["— Data tidak tersedia —"]

                # ── Build semua HTML fragments ──
                # ── Card utama — TANPA sizing ──
                st.markdown(
                    f"<div class='reco-card'>"
                    f"<div style='display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:8px'>"
                    f"<div>"
                    f"<span style='font-size:22px; font-weight:900; color:#00bbff'>{row['Ticker']}</span>"
                    f"&nbsp; <span class='{sig_class}'>{row['Signal']}</span>"
                    f"&nbsp; {regime_badge}"
                    f"&nbsp; <span style='font-size:12px; color:#667'>Beta:{row['Beta']}</span>"
                    f"<div style='font-size:30px; font-weight:900; color:{score_c}; line-height:1.2'>"
                    f"{row['Score']}<span style='font-size:14px; color:#667'>/100</span></div>"
                    f"</div>"
                    f"<div style='font-size:13px; color:#aac; text-align:right'>"
                    f"<b>Entry:</b> {row['Entry']:,} &nbsp; <b>SL:</b> {row['SL']:,} &nbsp; <b>TP:</b> {row['TP']:,} &nbsp; <b>R:R</b> {row['R:R']}<br>"
                    f"<b>RSI:</b> {row['RSI']} &nbsp; <b>ADX:</b> {row['ADX']} &nbsp; <b>MACD:</b> {row['MACD']} &nbsp; <b>Vol:</b> {row['Vol']}<br>"
                    f"<b>Pola:</b> {row['Pattern']} &nbsp; <b>Div:</b> {row['Div']}<br>"
                    f"<b>Nilai Harian:</b> {row['DailyVal']}<br>"
                    f"{vol_warn}{vol_suspect_warn}{div_note}"
                    f"</div></div></div>",
                    unsafe_allow_html=True
                )

                # ── Sizing — terpisah ──
                if max_lot > 0:
                    st.markdown(
                        f"<div style='background:#001a0a; border:1px solid #00aa44; border-radius:10px; padding:12px 16px; margin:2px 0 4px 0;'>"
                        f"<div style='font-size:12px; color:#00aa44; font-weight:700; margin-bottom:6px;'>💰 POSITION SIZING ({risk_per_trade*100:.1f}% risk dari Rp {modal_total:,.0f})</div>"
                        f"<div style='display:grid; grid-template-columns:repeat(4,1fr); gap:6px; font-size:12px;'>"
                        f"<div><span style='color:#667'>Max Lot</span><br><b style='color:#00ff99; font-size:16px'>{max_lot} lot</b></div>"
                        f"<div><span style='color:#667'>Nilai Posisi</span><br><b>Rp {pos_val:,.0f}</b></div>"
                        f"<div><span style='color:#667'>Risk (Rp)</span><br><b style='color:#ff8844'>Rp {actual_risk:,.0f}</b></div>"
                        f"<div><span style='color:#667'>Est. Biaya</span><br><b style='color:#ffcc00'>Rp {fee_total:,.0f}</b></div>"
                        f"</div></div>",
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        "<div style='background:#001a0a; border:1px solid #444; border-radius:10px; "
                        "padding:10px 16px; margin:2px 0 4px 0; color:#ff4466; font-size:12px;'>"
                        "⚠️ Modal tidak cukup untuk 1 lot dengan risk parameter ini.</div>",
                        unsafe_allow_html=True
                    )

                # ── Gap stats ──
                if g_stats:
                    gap_warn_txt = "⚠️ Saham ini sering gap besar!" if g_stats['freq_large'] > 20 else ""
                    st.markdown(
                        f"<div style='background:#0d1628; border-radius:8px; padding:8px 12px; font-size:12px; color:#aac; margin:2px 0;'>"
                        f"🌙 <b>Overnight Gap History:</b> avg ±{g_stats['avg_abs']}% | max up +{g_stats['max_up']}% | max down {g_stats['max_down']}% "
                        f"| gap &gt;1%: {g_stats['gap_up_pct']}% hari naik / {g_stats['gap_down_pct']}% hari turun"
                        f"{'  <b style=\"color:#ff8844\">' + gap_warn_txt + '</b>' if gap_warn_txt else ''}"
                        f"</div>",
                        unsafe_allow_html=True
                    )

                # ── Corp action ──
                for cw in corp_warns:
                    st.markdown(
                        f"<div style='background:#2a1500; border:1px solid #ff8800; border-radius:8px; "
                        f"padding:8px 12px; margin:2px 0; font-size:12px; color:#ffaa44;'>{cw}</div>",
                        unsafe_allow_html=True
                    )

                # ── IHSG note ──
                if row.get('IHSGNote') and row['IHSGNote'] != '—':
                    st.markdown(
                        f"<div style='font-size:11px; color:#556; margin:2px 0 8px 0;'>{row['IHSGNote']}</div>",
                        unsafe_allow_html=True
                    )

                # ── Reasoning ──
                with st.expander(f"📋 Kenapa {row['Ticker']} masuk rekomendasi?"):
                    for r in reasoning:
                        icon_color = "#00ff99" if "✅" in r else ("#ffcc00" if "🟡" in r else ("#ff4466" if "⚠️" in r else "#aac"))
                        st.markdown(
                            f"<div style='padding:5px 0; font-size:13px; color:{icon_color}; "
                            f"border-bottom:1px solid #111d2e;'>{r}</div>",
                            unsafe_allow_html=True
                        )

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
            score, detail, regime, adx_v = score_ticker(df, ihsg_df_global)
            entry, sl, tp, rr, signal, sig_col = get_levels(df, score, regime, broker_fee)
            last  = df.iloc[-1]
            cl    = sf(last['close']); rsi = sf(last['rsi'])
            e20   = sf(last['ema20']); e50 = sf(last['ema50'])
            e200  = sf(last['ema200'])
            adx   = sf(last['adx'])
            pats  = detect_patterns(df)
            _, vol_lbl, vol_type = volume_score(df)
            div   = detect_rsi_divergence(df)
            beta  = detail.get("Beta (20D)", "—")
            g_stats = overnight_gap_stats(df)
            corp_warns = check_corporate_actions(target)
            vol_suspect = df.attrs.get('volume_suspect', False)
            avg_daily_val = df.attrs.get('avg_daily_value', 0)

            # Position sizing
            max_lot, pos_val, actual_risk, fee_total = calc_position_size(
                modal_total, risk_per_trade, entry or cl, sl or cl*0.95, broker_fee
            )

            # Regime badge
            if regime == "trending":
                rbadge = f"<span class='regime-trend'>📈 TRENDING (ADX {adx:.0f})</span>"
            elif regime == "ranging":
                rbadge = f"<span class='regime-range'>↔️ RANGING (ADX {adx:.0f})</span>"
            else:
                rbadge = f"<span class='regime-transit'>🔄 TRANSITION (ADX {adx:.0f})</span>"

            m1, m2, m3, m4, m5, m6 = st.columns(6)
            m1.metric("Score",  f"{score}/100")
            m2.metric("Signal", signal)
            m3.metric("RSI",    f"{rsi:.1f}")
            m4.metric("ADX",    f"{adx:.1f}")
            m5.metric("Beta",   str(beta))
            m6.metric("Close",  f"{cl:,.0f}")

            st.markdown(rbadge, unsafe_allow_html=True)

            # Warnings
            if div == "bullish":
                st.success("🔼 RSI Bullish Divergence terdeteksi! Potential reversal kuat.")
            elif div == "bearish":
                st.warning("🔽 RSI Bearish Divergence — hati-hati potensi turun.")
            if vol_type in ("surge_bear", "bear"):
                st.error("⚠️ Volume surge tapi candle merah — distribusi institusi, hati-hati!")
            if vol_suspect:
                st.warning("⚠️ Volume data suspect dari yfinance — konfirmasi manual di broker.")
            if avg_daily_val < 10e9:
                st.warning(f"⚠️ Nilai transaksi harian rendah: Rp {avg_daily_val/1e9:.1f}M — likuiditas tipis, exit bisa susah.")
            for cw in corp_warns:
                st.error(f"🏢 Corporate Action: {cw}")
            if detail.get("IHSG Penalty", 0) > 0:
                st.warning(detail.get("IHSG Context",""))

            # Trade plan
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
                            <td><b>{pats[0] if pats else "—"}</b></td>
                            <td style='color:#889'>📈 Beta</td>
                            <td><b>{beta}</b></td></tr>
                        <tr><td style='color:#889'>💰 Max Lot</td>
                            <td><b style='color:#00ff99'>{max_lot} lot</b> (Rp {pos_val:,.0f})</td>
                            <td style='color:#889'>💸 Est. Biaya</td>
                            <td><b style='color:#ffcc00'>Rp {fee_total:,.0f}</b></td></tr>
                        <tr><td style='color:#889'>⚠️ Risk (Rp)</td>
                            <td><b style='color:#ff8844'>Rp {actual_risk:,.0f}</b> ({risk_per_trade*100:.1f}%)</td>
                            <td style='color:#889'>🏦 Nilai Harian</td>
                            <td><b>Rp {avg_daily_val/1e9:.1f}M</b></td></tr>
                    </table>
                </div>
                """, unsafe_allow_html=True)

            # Overnight gap info
            if g_stats:
                st.markdown(f"""
                <div class='gap-stat'>
                    🌙 <b>Overnight Gap Statistics (historical):</b>
                    Avg gap ±{g_stats['avg_abs']}% | Std {g_stats['std']}% |
                    Max up +{g_stats['max_up']}% | Max down {g_stats['max_down']}% |
                    Frekuensi gap >1% : {g_stats['gap_up_pct']}% hari naik / {g_stats['gap_down_pct']}% hari turun |
                    Gap besar (>2%): {g_stats['freq_large']}% hari
                    {'| <span style="color:#ff8844">⚠️ Saham ini sering gap besar — pertimbangkan SL lebih longgar atau sizing lebih kecil!</span>' if g_stats['freq_large'] > 20 else ''}
                </div>
                """, unsafe_allow_html=True)

            with st.expander("📐 Score Breakdown"):
                st.json(detail)

            # Chart
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                                row_heights=[0.55, 0.25, 0.20],
                                subplot_titles=["Harga + EMA + BB", "RSI + ADX", "Volume"])
            fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'],
                                          low=df['low'], close=df['close'],
                                          increasing_line_color='#00ff99',
                                          decreasing_line_color='#ff4466',
                                          name="OHLC"), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['ema20'],
                                     line=dict(color='orange', width=1.2), name="EMA20"), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['ema50'],
                                     line=dict(color='#8888ff', width=1.2), name="EMA50"), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['ema200'],
                                     line=dict(color='#ff6688', width=1.5, dash='dot'), name="EMA200"), row=1, col=1)
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
            fig.add_trace(go.Scatter(x=df.index, y=df['rsi'],
                                     line=dict(color='#bb77ff', width=1.5), name="RSI"), row=2, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['adx'],
                                     line=dict(color='#ffaa33', width=1.2, dash='dot'), name="ADX"), row=2, col=1)
            fig.add_hline(y=70, line_dash="dot", line_color="red",   row=2, col=1)
            fig.add_hline(y=30, line_dash="dot", line_color="green", row=2, col=1)
            fig.add_hline(y=25, line_dash="dot", line_color="#ffaa33", annotation_text="ADX 25", row=2, col=1)
            colors_vol = ['#00ff99' if c >= o else '#ff4466'
                          for c, o in zip(df['close'], df['open'])]
            fig.add_trace(go.Bar(x=df.index, y=df['volume'],
                                 marker_color=colors_vol, name="Volume"), row=3, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['vol_ma20'],
                                     line=dict(color='yellow', width=1), name="Vol MA20"), row=3, col=1)

            # ── Highlight candle penting ──────────────────
            pattern_markers = []
            for idx_i in range(2, len(df)):
                row_c = df.iloc[idx_i]
                o_c, h_c, l_c, c_c = sf(row_c['open']), sf(row_c['high']), sf(row_c['low']), sf(row_c['close'])
                body_c = abs(c_c - o_c)
                rng_c  = h_c - l_c
                if rng_c <= 0: continue
                uw_c = h_c - max(c_c, o_c)
                lw_c = min(c_c, o_c) - l_c
                pb_c = abs(sf(df.iloc[idx_i-1]['close']) - sf(df.iloc[idx_i-1]['open']))
                label_c, color_c, sym_c = None, None, None
                if lw_c >= 2*body_c and uw_c <= 0.3*body_c and body_c/rng_c > 0.05:
                    label_c, color_c, sym_c = "🔨 Hammer", "#00ff99", "triangle-up"
                elif uw_c >= 2*body_c and lw_c <= 0.3*body_c:
                    label_c, color_c, sym_c = "⬆️ Shooting Star", "#ff4466", "triangle-down"
                elif body_c/rng_c < 0.1:
                    label_c, color_c, sym_c = "✳️ Doji", "#ffcc00", "diamond"
                elif (sf(df.iloc[idx_i-1]['close']) < sf(df.iloc[idx_i-1]['open'])
                      and c_c > o_c and body_c > pb_c):
                    label_c, color_c, sym_c = "🟢 Bull Engulfing", "#00ff99", "star"
                elif (sf(df.iloc[idx_i-1]['close']) > sf(df.iloc[idx_i-1]['open'])
                      and c_c < o_c and body_c > pb_c):
                    label_c, color_c, sym_c = "🔴 Bear Engulfing", "#ff4466", "star"
                elif idx_i >= 3:
                    o3,c3 = sf(df.iloc[idx_i-2]['open']), sf(df.iloc[idx_i-2]['close'])
                    o2,c2 = sf(df.iloc[idx_i-1]['open']), sf(df.iloc[idx_i-1]['close'])
                    if c3 < o3 and abs(c2-o2) < 0.003*c2 and c_c > o_c:
                        label_c, color_c, sym_c = "🌅 Morning Star", "#00ff99", "star"
                    elif c3 > o3 and abs(c2-o2) < 0.003*c2 and c_c < o_c:
                        label_c, color_c, sym_c = "🌇 Evening Star", "#ff4466", "star"
                if label_c:
                    pattern_markers.append({
                        "x": df.index[idx_i],
                        "y": l_c * 0.985 if color_c == "#00ff99" else h_c * 1.015,
                        "label": label_c,
                        "color": color_c,
                        "sym": sym_c,
                        "pos": "bottom center" if color_c == "#00ff99" else "top center"
                    })

            if pattern_markers:
                fig.add_trace(go.Scatter(
                    x=[m["x"] for m in pattern_markers],
                    y=[m["y"] for m in pattern_markers],
                    mode="markers+text",
                    marker=dict(
                        symbol=[m["sym"] for m in pattern_markers],
                        color=[m["color"] for m in pattern_markers],
                        size=12, line=dict(width=1, color="#ffffff")
                    ),
                    text=[m["label"] for m in pattern_markers],
                    textposition=[m["pos"] for m in pattern_markers],
                    textfont=dict(size=9, color="#ffffff"),
                    name="Pattern",
                    hovertemplate="%{text}<extra></extra>",
                ), row=1, col=1)

            fig.update_layout(height=680, template='plotly_dark',
                              xaxis_rangeslider_visible=False,
                              margin=dict(l=0,r=0,t=30,b=0), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

            # ── Penjelasan chart ──────────────────────────
            with st.expander("📖 Cara Baca Grafik Ini", expanded=False):
                last_r   = df.iloc[-1]
                cl_r     = sf(last_r['close'])
                e20_r    = sf(last_r['ema20'])
                e50_r    = sf(last_r['ema50'])
                e200_r   = sf(last_r['ema200'])
                bb_u_r   = sf(last_r['bb_u'])
                bb_l_r   = sf(last_r['bb_l'])
                bb_m_r   = sf(last_r['bb_m'])
                bb_w_r   = sf(last_r['bb_width'])
                rsi_r    = sf(last_r['rsi'])
                adx_r    = sf(last_r['adx'])
                dmp_r    = sf(last_r['dmp'])
                dmn_r    = sf(last_r['dmn'])
                vr_r     = sf(last_r['vol_ratio'])

                # EMA status
                if cl_r > e20_r > e50_r > e200_r > 0:
                    ema_status = "✅ Full alignment — harga di atas semua EMA. Struktur uptrend sempurna."
                elif cl_r > e20_r > e50_r:
                    ema_status = "🟡 Harga di atas EMA20 & EMA50, tapi EMA200 belum aligned. Uptrend jangka menengah."
                elif cl_r > e20_r:
                    ema_status = "🟡 Harga di atas EMA20 saja. Trend jangka pendek, perlu konfirmasi lebih."
                else:
                    ema_status = "⚠️ Harga di bawah EMA20. Struktur belum bullish — tunggu recovery."

                # BB status
                bb_pct = (cl_r - bb_l_r) / (bb_u_r - bb_l_r) * 100 if (bb_u_r - bb_l_r) > 0 else 50
                if cl_r <= bb_l_r * 1.005:
                    bb_status = f"✅ Harga di BB Lower ({bb_pct:.0f}%) — area oversold, potensi reversal/bouncing"
                elif cl_r >= bb_u_r * 0.995:
                    bb_status = f"⚠️ Harga di BB Upper ({bb_pct:.0f}%) — area overbought, waspadai pullback"
                elif bb_w_r < 0.03:
                    bb_status = f"✅ BB Squeeze (width {bb_w_r:.3f}) — volatilitas sangat rendah, potensi breakout besar"
                else:
                    bb_status = f"🟡 Harga di tengah BB ({bb_pct:.0f}%) — netral"

                # RSI status
                if rsi_r < 30:
                    rsi_status = f"✅ RSI {rsi_r:.0f} — Oversold, potensi reversal ke atas"
                elif rsi_r < 45:
                    rsi_status = f"✅ RSI {rsi_r:.0f} — Recovery zone, momentum mulai membaik"
                elif rsi_r <= 70:
                    rsi_status = f"🟡 RSI {rsi_r:.0f} — Zona normal/sehat"
                else:
                    rsi_status = f"⚠️ RSI {rsi_r:.0f} — Overbought, hati-hati potensi koreksi"

                # ADX status
                if adx_r > 30 and dmp_r > dmn_r:
                    adx_status = f"✅ ADX {adx_r:.0f} — Trend kuat ke atas (DI+ {dmp_r:.0f} > DI- {dmn_r:.0f})"
                elif adx_r > 30 and dmn_r > dmp_r:
                    adx_status = f"⚠️ ADX {adx_r:.0f} — Trend kuat ke bawah (DI- {dmn_r:.0f} > DI+ {dmp_r:.0f})"
                elif adx_r > 20:
                    adx_status = f"🟡 ADX {adx_r:.0f} — Trend mulai terbentuk"
                else:
                    adx_status = f"⚠️ ADX {adx_r:.0f} — Pasar sideways/ranging, sinyal trend tidak valid"

                # Vol status
                if vr_r >= 2.0:
                    vol_status = f"✅ Volume {vr_r:.1f}x rata-rata — surge, konfirmasi kuat"
                elif vr_r >= 1.3:
                    vol_status = f"🟡 Volume {vr_r:.1f}x rata-rata — di atas normal"
                else:
                    vol_status = f"⚠️ Volume {vr_r:.1f}x rata-rata — sepi, sinyal kurang meyakinkan"

                n_patterns = len(pattern_markers)

                st.markdown(f"""
                <div style='background:#0a1020; border-radius:10px; padding:16px; font-size:13px; color:#ccd;'>

                <div style='color:#00bbff; font-weight:700; font-size:14px; margin-bottom:12px;'>
                    📊 Kondisi Chart {target.replace(".JK","")} Saat Ini
                </div>

                <div style='display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:14px;'>
                    <div style='background:#0d1628; border-radius:8px; padding:10px;'>
                        <div style='color:#ffaa33; font-weight:700; margin-bottom:6px;'>📈 EMA (Garis Tren)</div>
                        <div style='color:#889; font-size:11px; margin-bottom:4px;'>
                        🟠 EMA20 = tren jangka pendek (20 hari)<br>
                        🟣 EMA50 = tren jangka menengah (50 hari)<br>
                        🔴 EMA200 = tren jangka panjang (200 hari)
                        </div>
                        <div style='color:#ddd;'>{ema_status}</div>
                    </div>
                    <div style='background:#0d1628; border-radius:8px; padding:10px;'>
                        <div style='color:#336699; font-weight:700; margin-bottom:6px;'>〰️ Bollinger Bands</div>
                        <div style='color:#889; font-size:11px; margin-bottom:4px;'>
                        Garis biru putus-putus = batas atas/bawah volatilitas normal.<br>
                        Harga di luar band = kondisi ekstrem (overbought/oversold).<br>
                        Band menyempit = squeeze, siap breakout.
                        </div>
                        <div style='color:#ddd;'>{bb_status}</div>
                    </div>
                    <div style='background:#0d1628; border-radius:8px; padding:10px;'>
                        <div style='color:#bb77ff; font-weight:700; margin-bottom:6px;'>📉 RSI (Momentum)</div>
                        <div style='color:#889; font-size:11px; margin-bottom:4px;'>
                        Garis ungu di panel tengah. Range 0–100.<br>
                        &lt;30 = oversold (murah, potensi naik).<br>
                        &gt;70 = overbought (mahal, potensi koreksi).<br>
                        Garis merah = 70 | Garis hijau = 30.
                        </div>
                        <div style='color:#ddd;'>{rsi_status}</div>
                    </div>
                    <div style='background:#0d1628; border-radius:8px; padding:10px;'>
                        <div style='color:#ffaa33; font-weight:700; margin-bottom:6px;'>〽️ ADX (Kekuatan Trend)</div>
                        <div style='color:#889; font-size:11px; margin-bottom:4px;'>
                        Garis oranye putus-putus di panel RSI.<br>
                        &gt;25 = trend sedang kuat dan valid.<br>
                        &lt;20 = pasar ranging/sideways — sinyal EMA & MACD kurang reliabel.<br>
                        Garis kuning putus = ADX 25.
                        </div>
                        <div style='color:#ddd;'>{adx_status}</div>
                    </div>
                </div>

                <div style='background:#0d1628; border-radius:8px; padding:10px; margin-bottom:10px;'>
                    <div style='color:#ffcc00; font-weight:700; margin-bottom:6px;'>📊 Volume (Panel Bawah)</div>
                    <div style='color:#889; font-size:11px; margin-bottom:4px;'>
                    Batang hijau = hari closing naik | Batang merah = hari closing turun.<br>
                    Garis kuning = rata-rata volume 20 hari. Batang lebih tinggi dari garis kuning = volume di atas normal.<br>
                    Volume surge + candle hijau = akumulasi. Volume surge + candle merah = distribusi (⚠️ sinyal bahaya).
                    </div>
                    <div style='color:#ddd;'>{vol_status}</div>
                </div>

                <div style='background:#0d1628; border-radius:8px; padding:10px; margin-bottom:10px;'>
                    <div style='color:#ffffff; font-weight:700; margin-bottom:6px;'>🕯️ Garis Horizontal di Chart</div>
                    <div style='color:#889; font-size:11px; margin-bottom:4px;'>
                    🟢 Garis hijau putus-putus = <b>Take Profit (TP)</b> — target harga keluar dengan profit.<br>
                    🟡 Garis kuning putus-putus = <b>Entry</b> — harga ideal masuk posisi.<br>
                    🔴 Garis merah putus-putus = <b>Stop Loss (SL)</b> — batas maksimal kerugian, wajib dipasang saat beli.
                    </div>
                </div>

                <div style='background:#0d1628; border-radius:8px; padding:10px;'>
                    <div style='color:#ffffff; font-weight:700; margin-bottom:6px;'>
                        🕯️ Pola Candlestick Terdeteksi ({n_patterns} marker di chart)
                    </div>
                    <div style='color:#889; font-size:11px; margin-bottom:6px;'>
                    Marker muncul di atas/bawah candle yang memiliki pola signifikan.<br>
                    Marker hijau (⬆) = pola bullish | Marker merah (⬇) = pola bearish | Kuning = netral/doji
                    </div>
                    <div style='display:grid; grid-template-columns:1fr 1fr; gap:6px; font-size:12px;'>
                        <div><span style='color:#00ff99'>🔨 Hammer</span> — ekor panjang bawah, potensi reversal naik kuat</div>
                        <div><span style='color:#ff4466'>⬆️ Shooting Star</span> — ekor panjang atas, potensi reversal turun</div>
                        <div><span style='color:#00ff99'>🟢 Bull Engulfing</span> — candle hijau menelan candle merah sebelumnya</div>
                        <div><span style='color:#ff4466'>🔴 Bear Engulfing</span> — candle merah menelan candle hijau sebelumnya</div>
                        <div><span style='color:#00ff99'>🌅 Morning Star</span> — 3 candle: turun → doji → naik, reversal bullish</div>
                        <div><span style='color:#ff4466'>🌇 Evening Star</span> — 3 candle: naik → doji → turun, reversal bearish</div>
                        <div><span style='color:#ffcc00'>✳️ Doji</span> — buka = tutup, pasar ragu-ragu, perhatikan candle berikutnya</div>
                        <div><span style='color:#00ff99'>💪 Bull Marubozu</span> — candle penuh hijau tanpa ekor, momentum kuat</div>
                    </div>
                </div>

                </div>
                """, unsafe_allow_html=True)

# ══════════════════════════════════════════════
# TAB 4 — PRE-MARKET CHECK
# ══════════════════════════════════════════════
with tab4:
    st.subheader("Pre-Market Check — IEP Adjustment")
    st.caption("Masukkan IEP (Indicative Equilibrium Price) dari Ajaib sebelum market buka. "
               "Sistem akan recalculate entry, SL, TP, dan beri keputusan GO / SKIP / WAIT.")
    st.divider()

    logs_pm   = load_log()
    open_pm   = [l for l in logs_pm if l["status"] == "OPEN"]
    scan_date = datetime.now(TZ_JKT).strftime("%Y-%m-%d")
    today_pm  = [l for l in open_pm if l["date"] == scan_date]

    col_wl1, col_wl2 = st.columns([3, 1])
    with col_wl1:
        manual_tickers = st.text_input("Tambah ticker manual (pisahkan koma):",
                                        placeholder="BBRI, TLKM, GOTO")
    with col_wl2:
        ihsg_open = st.number_input("IHSG Open estimasi:", value=0, step=10)

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
            df_pm = fetch_df(jk(t_clean), "6mo")
            if df_pm is not None:
                sc_pm, _, reg_pm, _ = score_ticker(df_pm, ihsg_df_global)
                e_pm, sl_pm, tp_pm, _, sig_pm, _ = get_levels(df_pm, sc_pm, reg_pm, broker_fee)
                if e_pm:
                    base_rows.append({
                        "ticker": t_clean, "entry": float(e_pm),
                        "sl": float(sl_pm), "tp": float(tp_pm),
                        "score": sc_pm, "signal": sig_pm, "from": "Manual",
                    })
            else:
                base_rows.append({
                    "ticker": t_clean, "entry": 0, "sl": 0, "tp": 0,
                    "score": 0, "signal": "—", "from": "Manual (no data)",
                })

    if not base_rows:
        st.info("Belum ada watchlist. Jalankan scanner dulu atau tambah ticker manual.")
    else:
        seen = {}
        for row in base_rows:
            if row["ticker"] not in seen:
                seen[row["ticker"]] = row
        base_rows = list(seen.values())

        st.divider()
        st.markdown("#### Input IEP per Saham")
        st.caption("Harga IEP terlihat di Ajaib pada fase Pre-Opening (08:45–09:00 WIB).")

        iep_inputs = {}
        prev_closes = {}
        gap_stats_pm = {}

        for row in base_rows:
            try:
                d_prev = clean_df(yf.download(jk(row["ticker"]), period="5d", progress=False))
                prev_closes[row["ticker"]] = sf(d_prev['close'].iloc[-1]) if not d_prev.empty else row["entry"]
            except:
                prev_closes[row["ticker"]] = row["entry"]
            # Gap stats untuk pre-market
            df_gs = fetch_df(jk(row["ticker"]), "6mo")
            gap_stats_pm[row["ticker"]] = overnight_gap_stats(df_gs) if df_gs is not None else None

        cols_per_row = 3
        for i in range(0, len(base_rows), cols_per_row):
            chunk = base_rows[i:i+cols_per_row]
            cols  = st.columns(cols_per_row)
            for col, (row_idx, row) in zip(cols, [(i+j, base_rows[i+j]) for j in range(len(chunk))]):
                with col:
                    prev_c = prev_closes.get(row["ticker"], row["entry"])
                    iep_val = col.number_input(
                        f"{row['ticker']}  (close: {prev_c:,.0f})",
                        min_value=0, value=int(prev_c), step=1,
                        key=f"iep_{row_idx}_{row['ticker']}"
                    )
                    iep_inputs[row["ticker"]] = iep_val

        st.divider()

        if st.button("Hitung Ulang dengan IEP", type="primary", use_container_width=True):
            st.markdown("#### Hasil Analisis Pre-Market")

            for row in base_rows:
                ticker  = row["ticker"]
                iep     = iep_inputs.get(ticker, 0)
                prev_c  = prev_closes.get(ticker, row["entry"])
                entry_o = row["entry"]
                sl_o    = row["sl"]
                tp_o    = row["tp"]

                if iep <= 0 or prev_c <= 0: continue

                gap_pct  = (iep - prev_c) / prev_c * 100
                gap_type = ("gap_up" if gap_pct > 1.0 else "gap_down" if gap_pct < -1.0 else "flat")

                new_entry = iep
                original_sl_dist_pct = (entry_o - sl_o) / entry_o if entry_o > 0 else 0.02
                new_sl = round(new_entry * (1 - original_sl_dist_pct))

                # Adjust TP untuk cover biaya transaksi
                total_fee = (broker_fee + IDX_LEVY * 2) / 100
                if tp_o > new_entry:
                    new_tp = tp_o
                else:
                    new_tp = round(new_entry + (new_entry - new_sl) * 2.0)
                new_tp = max(new_tp, round(new_entry * (1 + total_fee) + (new_entry - new_sl)))

                new_risk   = new_entry - new_sl
                new_reward = new_tp - new_entry
                new_rr     = round(new_reward / new_risk, 2) if new_risk > 0 else 0

                # Position sizing dengan IEP
                new_lot, new_pos_val, new_actual_risk, new_fee = calc_position_size(
                    modal_total, risk_per_trade, new_entry, new_sl, broker_fee
                )

                # Decision
                if gap_type == "gap_up":
                    if gap_pct > 5:
                        decision, reason, dec_color = "SKIP", f"Gap up {gap_pct:+.1f}% terlalu jauh. Setup rusak, R:R tidak layak.", "#ff4466"
                    elif new_rr >= 1.5:
                        decision, reason, dec_color = "GO", f"Gap up {gap_pct:+.1f}% wajar. R:R masih {new_rr} — layak entry di harga buka.", "#00ff99"
                    else:
                        decision, reason, dec_color = "WAIT", f"Gap up {gap_pct:+.1f}% memperburuk R:R jadi {new_rr}. Tunggu pullback ke {int(entry_o):,}.", "#ffcc00"
                elif gap_type == "gap_down":
                    if gap_pct < -5:
                        decision, reason, dec_color = "SKIP", f"Gap down {gap_pct:+.1f}%. Potensi panic sell lanjutan. Tunggu hari lain.", "#ff4466"
                    elif gap_pct < -2:
                        decision, reason, dec_color = "WAIT", f"Gap down {gap_pct:+.1f}%. Tunggu stabilisasi 15–30 menit pertama sebelum entry.", "#ffcc00"
                    else:
                        decision, reason, dec_color = "GO", f"Gap down minor {gap_pct:+.1f}%. Entry lebih murah dari plan. R:R membaik jadi {new_rr}.", "#00ff99"
                else:
                    if new_rr >= 1.5:
                        decision, reason, dec_color = "GO", f"Open flat ({gap_pct:+.1f}%). Entry sesuai plan. R:R {new_rr}.", "#00ff99"
                    else:
                        decision, reason, dec_color = "WAIT", f"Open flat tapi R:R hanya {new_rr}. Entry lebih ideal di {int(entry_o):,}.", "#ffcc00"

                # IHSG context
                ihsg_note = ""
                if ihsg_open > 0:
                    try:
                        ihsg_prev_c = sf(ihsg_df_global['close'].iloc[-1]) if ihsg_df_global is not None else 0
                        ihsg_gap = (ihsg_open - ihsg_prev_c) / ihsg_prev_c * 100 if ihsg_prev_c > 0 else 0
                        if ihsg_gap < -1.0:
                            ihsg_note = f" | IHSG estimasi gap down {ihsg_gap:+.1f}% — pertimbangkan sizing lebih kecil ({max(1, new_lot//2)} lot)."
                            if decision == "GO": decision = "WAIT"; dec_color = "#ffcc00"
                        elif ihsg_gap > 0.5:
                            ihsg_note = f" | IHSG gap up {ihsg_gap:+.1f}% — konfirmasi bullish."
                    except: pass

                # Gap history context
                gs = gap_stats_pm.get(ticker)
                gap_hist_note = ""
                if gs and gs['freq_large'] > 20:
                    gap_hist_note = f" | Historis: saham ini gap >2% sebanyak {gs['freq_large']}% hari — SL adjustment disarankan."

                # Corp action warnings
                corp_warns_pm = check_corporate_actions(jk(ticker))

                gap_label = f"{gap_pct:+.1f}%"
                gap_color = "#00ff99" if gap_pct >= 0 else "#ff4466"

                st.markdown(f"""
                <div style='background:#0a1020; border-radius:12px; border-left:5px solid {dec_color};
                            padding:16px 20px; margin:10px 0;'>
                    <div style='display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:10px;'>
                        <div>
                            <span style='font-size:20px; font-weight:900; color:#00bbff;'>{ticker}</span>
                            &nbsp;&nbsp;
                            <span style='font-size:22px; font-weight:900; color:{dec_color};'>{decision}</span>
                        </div>
                        <div style='font-size:13px; color:#889;'>{row['from']} | Score: {row['score']}</div>
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
                            <div style='color:#667; font-size:11px; margin-bottom:2px;'>R:R Baru</div>
                            <div style='font-weight:700; color:{"#00ff99" if new_rr >= 2 else ("#ffcc00" if new_rr >= 1.5 else "#ff4466")};'>1:{new_rr}</div>
                        </div>
                        <div style='background:#0d1628; border-radius:8px; padding:8px; text-align:center;'>
                            <div style='color:#667; font-size:11px; margin-bottom:2px;'>Max Lot (IEP)</div>
                            <div style='font-weight:700; color:#00ff99;'>{new_lot} lot</div>
                        </div>
                    </div>
                    <div style='display:grid; grid-template-columns:repeat(3,1fr); gap:8px; font-size:13px; margin-bottom:10px;'>
                        <div style='background:#0d1628; border-radius:8px; padding:8px; text-align:center;'>
                            <div style='color:#667; font-size:11px; margin-bottom:2px;'>Stop Loss</div>
                            <div style='font-weight:700; color:#ff4466;'>{new_sl:,} <span style='font-size:11px;'>({(new_entry-new_sl)/new_entry*100:.1f}%)</span></div>
                        </div>
                        <div style='background:#0d1628; border-radius:8px; padding:8px; text-align:center;'>
                            <div style='color:#667; font-size:11px; margin-bottom:2px;'>Take Profit</div>
                            <div style='font-weight:700; color:#00ff99;'>{new_tp:,} <span style='font-size:11px;'>(+{(new_tp-new_entry)/new_entry*100:.1f}%)</span></div>
                        </div>
                        <div style='background:#0d1628; border-radius:8px; padding:8px; text-align:center;'>
                            <div style='color:#667; font-size:11px; margin-bottom:2px;'>Est. Biaya</div>
                            <div style='font-weight:700; color:#ffcc00;'>Rp {new_fee:,.0f}</div>
                        </div>
                    </div>
                    <div style='font-size:13px; color:#ccd; background:#0d1628; border-radius:8px; padding:10px;'>
                        {reason}{ihsg_note}{gap_hist_note}
                    </div>
                    {"".join([f"<div class='corp-warn' style='margin-top:6px;'>{w}</div>" for w in corp_warns_pm])}
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

        # Broker fee disclaimer
        st.caption(f"⚠️ P&L di tracker belum include biaya transaksi ({broker_fee + IDX_LEVY*2:.2f}% roundtrip dengan {broker_choice.split('(')[0].strip()}). Real P&L lebih rendah.")

        if stats['closed'] > 0:
            fig_wr = go.Figure(go.Pie(
                values=[stats['wins'], stats['losses']],
                labels=["WIN","LOSS"],
                marker_colors=['#00ff99','#ff4466'],
                hole=0.6, textinfo='label+percent'
            ))
            fig_wr.update_layout(height=200, template='plotly_dark',
                                 margin=dict(l=0,r=0,t=0,b=0), showlegend=False)
            col_pie, col_empty = st.columns([1,2])
            with col_pie:
                st.plotly_chart(fig_wr, use_container_width=True)

        open_trades = [l for l in logs if l["status"] == "OPEN"]
        if open_trades:
            st.markdown("#### Trade Aktif")
            for trade in open_trades:
                status, curr, days, action, pnl = eval_trade(trade)
                # Adjust P&L untuk biaya
                fee_adj = broker_fee + IDX_LEVY * 2
                pnl_after_fee = round(pnl - fee_adj, 2)
                pnl_color = "#00ff99" if pnl_after_fee >= 0 else "#ff4466"
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
                    &nbsp;|&nbsp; P&L gross: <b>{pnl:+.2f}%</b>
                    &nbsp;|&nbsp; P&L net: <b style='color:{pnl_color}'>{pnl_after_fee:+.2f}%</b>
                    &nbsp;|&nbsp; {action}
                    &nbsp;|&nbsp; <span style='color:#889'>D{days}/{trade.get('hold_days',3)}</span>
                </div>
                """, unsafe_allow_html=True)

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
