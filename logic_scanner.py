"""
logic_scanner.py — logika inti IDX Screener, DISELARASKAN dengan backtest_v8.py.

Modul ini dipisah dari app.py (Streamlit) supaya logika scoring/entry/exit
punya SATU sumber kebenaran yang sama dipakai baik oleh scanner interaktif
maupun evaluasi riwayat trading -- tidak ada lagi app yang jalan dengan
logika berbeda dari yang sudah divalidasi lewat backtest.

Perubahan kunci dibanding versi app.py lama (v2):
  - Entry SELALU limit price (target pullback), bukan market-buy di close
  - Fill butuh konfirmasi candle (close di paruh atas range harian)
  - SL diberi cap maksimum (MAX_SL_PCT) -- terbukti di v7b memperbaiki
    CAGR & drawdown BERSAMAAN, bukan trade-off
  - Setelah profit capai 1x risk awal -> SL pindah ke breakeven, lalu
    trailing mengikuti ATR (bukan diam di satu level)
  - Universe diperluas (IDX30+LQ45+EXTRA_UNIVERSE, ~167 saham) & filter
    likuiditas (MIN_AVG_DOLLAR_VALUE) supaya tidak scan saham yang
    terlalu tipis untuk dieksekusi riil
  - WATCHLIST (skor 40-54) TIDAK lagi ditampilkan sebagai kandidat --
    band ini terbukti expectancy negatif di backtest

CATATAN: walk-forward pause per-ticker (fitur di backtest_v8 &
paper_trading_log.py yang men-jeda ticker dgn performa trailing jelek)
TIDAK diimplementasikan di sini. Fitur itu butuh state historis
berkelanjutan antar-hari yang lebih pas dijalankan lewat
paper_trading_log.py (proses harian terpisah), bukan di scan interaktif
sekali-klik. Kalau mau menyatukannya, app ini bisa dibuat membaca file
state paper_trading_log.py -- tanya saja kalau itu yang diinginkan.
"""
import numpy as np
import pandas as pd
import yfinance as yf
import pandas_ta as ta
from datetime import date, timedelta

IDX_LEVY = 0.04  # % per sisi transaksi -> x2 untuk roundtrip

# ── Universe -- disamakan dengan backtest_v8.py ──
IDX30 = ["AADI","ADMR","ADRO","AMRT","ANTM","ASII","BBCA","BBNI","BBRI","BMRI",
         "BRPT","BUMI","CPIN","EMTK","EXCL","GOTO","ICBP","INCO","INDF","INKP",
         "JPFA","KLBF","MBMA","MDKA","MEDC","PGAS","PGEO","PTBA","TLKM","TOWR",
         "UNTR","UNVR"]
LQ45 = ["AADI","ADMR","ADRO","AKRA","AMMN","AMRT","ANTM","ASII","BBCA","BBNI",
        "BBRI","BBTN","BMRI","BRPT","BUMI","CPIN","CUAN","DEWA","EMTK","ESSA",
        "EXCL","GOTO","HRTA","ICBP","INCO","INDF","INKP","ISAT","ITMG","JPFA",
        "KLBF","MAPI","MBMA","MDKA","MEDC","PGAS","PGEO","PTBA","SCMA","SMGR",
        "TLKM","TOWR","UNTR","UNVR","WIFI"]
# Bukan daftar resmi real-time -- cek ulang kalau ada perubahan indeks/delisting.
EXTRA_UNIVERSE = [
    "ACES","ADES","ADRO","AGII","AGRO","ALDO","AMAG","ANJT","APIC","ARCI",
    "ARKO","ARTO","AUTO","AVIA","BALI","BANK","BBHI","BBSI","BBYB","BFIN",
    "BJBR","BJTM","BKSL","BNGA","BNII","BOGA","BRIS","BSDE","BSSR","BTPS",
    "BUKA","BULL","CARE","CITA","CLEO","CMNP","CMRY","CNMA","COAL","CTRA",
    "DGWG","DMAS","DOID","DSNG","DUTI","ELSA","ENRG","ERAA","FILM","FREN",
    "GEMS","GGRM","GJTL","GOOD","GPRA","GWSA","HEAL","HMSP","HOKI","HRUM",
    "IMAS","IMJS","INDY","INTP","IPCC","IPCM","JIHD","JRPT","JSMR","KIJA",
    "KPIG","LPKR","LPPF","LSIP","MAIN","MARK","MAYA","MEGA","MERK","MIDI",
    "MIKA","MNCN","MPMX","MTDL","MYOR","NCKL","NICL","NISP","NOBU","OASA",
    "PANI","PNBN","PNLF","PSAB","PSSI","PTPP","PTRO","PWON","RAJA","RALS",
    "SIDO","SILO","SMBR","SMDR","SMRA","SONA","SRTG","SSIA","SSMS","STTP",
    "TAPG","TBIG","TINS","TKIM","TPIA","TRIN","ULTJ","VOKS","WEGE","WIKA",
    "WSBP","WSKT","WTON","ZINC","ZYRX",
]
UNIVERSES = {
    "IDX30 — Blue Chip": IDX30,
    "LQ45 — Liquid 45": LQ45,
    "Gabungan (IDX30 + LQ45)": list(dict.fromkeys(IDX30 + LQ45)),
    "Universe Luas (167 saham, spt backtest_v8)": list(dict.fromkeys(IDX30 + LQ45 + EXTRA_UNIVERSE)),
}

BROKER_FEES = {
    "Ajaib / Neo (0.20%)": 0.20,
    "Stockbit (0.30%)": 0.30,
    "Sekuritas standar (0.40%)": 0.40,
}

# ── Parameter default -- disamakan dgn backtest_v8.py ──
MIN_SCORE_DEFAULT = 60
HOLD_DAYS_MAX_DEFAULT = 25
PULLBACK_DAYS_DEFAULT = 3
BREAKEVEN_R_DEFAULT = 1.0
TRAIL_ATR_MULT_DEFAULT = 2.0
MAX_SL_PCT_DEFAULT = 0.10
MIN_AVG_DOLLAR_VALUE_DEFAULT = 2_000_000_000


def jk(t): return t if t.endswith(".JK") else f"{t}.JK"


def clean_df(df):
    if df.empty:
        return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    return df


def sf(val, default=0.0):
    try:
        v = float(val)
        return default if (np.isnan(v) or np.isinf(v)) else v
    except Exception:
        return default


# ─────────────────────────────────────────────
# FETCH
# ─────────────────────────────────────────────
def fetch_batch(tickers, period="2y"):
    """Download banyak ticker sekaligus. Return dict {ticker: df_indikator}."""
    tickers = list(tickers)
    raw = yf.download(tickers, period=period, interval="1d", group_by="ticker",
                       threads=True, progress=False, auto_adjust=False)
    result = {}
    single = (len(tickers) == 1)
    for t in tickers:
        try:
            df = clean_df(raw.copy()) if single else clean_df(raw[t].copy())
        except Exception:
            continue
        if df is None or df.empty or len(df) < 260:
            continue
        result[t] = add_indicators(df)
    return result


def fetch_one(ticker, period="2y"):
    df = clean_df(yf.download(ticker, period=period, interval="1d", progress=False))
    if df.empty or len(df) < 260:
        return None
    return add_indicators(df)


def fetch_history(ticker, start, end=None):
    """Fetch history mentah (tanpa indikator) dari tanggal `start` s.d. `end`
    (default: hari ini). Dipakai untuk evaluasi trade yang sudah berjalan."""
    end = end or (date.today() + timedelta(days=1))
    raw = yf.download(jk(ticker), start=start - timedelta(days=1), end=end, progress=False)
    return clean_df(raw)


# ─────────────────────────────────────────────
# INDIKATOR
# ─────────────────────────────────────────────
def add_indicators(df):
    df = df.copy()
    df["ema20"] = ta.ema(df["close"], length=20)
    df["ema50"] = ta.ema(df["close"], length=50)
    df["ema200"] = ta.ema(df["close"], length=200)
    df["rsi"] = ta.rsi(df["close"], length=14)

    macd_df = ta.macd(df["close"], fast=12, slow=26, signal=9)
    if macd_df is not None and not macd_df.empty:
        df["macd"] = macd_df.iloc[:, 0]
        df["sig"] = macd_df.iloc[:, 1]
        df["hist"] = macd_df.iloc[:, 2]
    else:
        df["macd"] = df["sig"] = df["hist"] = 0.0

    df["atr"] = ta.atr(df["high"], df["low"], df["close"], length=14)

    adx_df = ta.adx(df["high"], df["low"], df["close"], length=14)
    if adx_df is not None and not adx_df.empty:
        df["adx"] = adx_df.iloc[:, 0]
        df["dmp"] = adx_df.iloc[:, 1]
        df["dmn"] = adx_df.iloc[:, 2]
    else:
        df["adx"] = df["dmp"] = df["dmn"] = 20.0

    df["vol_ma20"] = df["volume"].rolling(20).mean()
    df["vol_ratio"] = df["volume"] / df["vol_ma20"].replace(0, np.nan)
    df["res_trailing"] = df["high"].rolling(20).max()
    df["dollar_value"] = df["close"] * df["volume"]
    df["dollar_value_ma20"] = df["dollar_value"].rolling(20).mean()
    return df


def detect_regime(last):
    adx = sf(last["adx"])
    if adx > 25:
        return "trending"
    elif adx < 20:
        return "ranging"
    return "transition"


def detect_divergence(df, lookback=14):
    if len(df) < lookback + 2:
        return "none"
    prices = df["close"].values[-lookback:]
    rsis = df["rsi"].values[-lookback:]
    lows = [(i, prices[i]) for i in range(1, len(prices) - 1)
            if prices[i] < prices[i - 1] and prices[i] < prices[i + 1]]
    if len(lows) < 2:
        return "none"
    p1, p2 = lows[-2], lows[-1]
    r1, r2 = rsis[p1[0]], rsis[p2[0]]
    if p2[1] < p1[1] and r2 > r1 + 3:
        return "bullish"
    if p2[1] > p1[1] and r2 < r1 - 3:
        return "bearish"
    return "none"


# ─────────────────────────────────────────────
# SCORING — identik dengan backtest_v8.score_ticker
# ─────────────────────────────────────────────
def score_ticker(df, disable_score_caps=False):
    last = df.iloc[-1]
    cl, e20, e50, e200 = sf(last["close"]), sf(last["ema20"]), sf(last["ema50"]), sf(last["ema200"])
    rsi, macd, sig, hist = sf(last["rsi"]), sf(last["macd"]), sf(last["sig"]), sf(last["hist"])
    hist_p = sf(df["hist"].iloc[-2]) if len(df) > 2 else 0
    adx, dmp, dmn = sf(last["adx"]), sf(last["dmp"]), sf(last["dmn"])
    vr = sf(last["vol_ratio"], 1.0)
    is_green = cl >= sf(last["open"])

    regime = detect_regime(last)

    t = 0
    if cl > e20: t += 25
    if cl > e50: t += 20
    if e20 > e50: t += 15
    if e50 > e200 > 0: t += 15
    if adx > 25 and dmp > dmn: t += 25
    elif adx > 20 and dmp > dmn: t += 12
    t = max(0, min(t, 100))

    m = 0
    if regime == "trending":
        if 50 <= rsi <= 70: m += 35
        elif 40 <= rsi < 50: m += 15
        elif rsi > 70: m += 5
    else:
        if 30 <= rsi <= 45: m += 35
        elif 45 < rsi <= 55: m += 15
    if macd > sig: m += 25
    if hist > 0 and hist > hist_p: m += 20
    div = detect_divergence(df)
    if div == "bullish": m += 20
    elif div == "bearish": m -= 15
    m = max(0, min(m, 100))

    if vr >= 2.0 and is_green: v = 90
    elif vr >= 1.5 and is_green: v = 75
    elif vr >= 1.0 and is_green: v = 55
    elif vr >= 1.0: v = 35
    else: v = 20

    weights = {
        "trending":   {"trend": 0.45, "momentum": 0.30, "volume": 0.25},
        "ranging":    {"trend": 0.20, "momentum": 0.50, "volume": 0.30},
        "transition": {"trend": 0.30, "momentum": 0.40, "volume": 0.30},
    }[regime]

    raw = t * weights["trend"] + m * weights["momentum"] + v * weights["volume"]
    score = int(min(raw, 100))

    if not disable_score_caps:
        adx_recent = sf(df["adx"].iloc[-10:].mean()) if len(df) >= 10 else adx
        if adx_recent < 15:
            score = min(score, 50)
        if score >= 70 and vr < 1.3:
            score = min(score, 69)

    detail = {
        "Regime": regime, "Trend": t, "Momentum": m, "Volume": v,
        "RSI": round(rsi, 1), "ADX": round(adx, 1), "Divergensi": div,
        "MACD Bullish": macd > sig,
    }
    return score, detail, regime


# ─────────────────────────────────────────────
# ENTRY / SL / TP — identik dengan backtest_v8.get_levels_bt
# ─────────────────────────────────────────────
def get_levels(df, score, regime, max_sl_pct=MAX_SL_PCT_DEFAULT):
    """Entry di sini SELALU target limit price (pullback), BUKAN harga beli
    langsung. Baru dianggap 'terisi' kalau harga betulan turun ke level ini
    (dicek terpisah lewat simulate_fill_and_exit)."""
    last = df.iloc[-1]
    cl, e20, atr = sf(last["close"]), sf(last["ema20"]), sf(last["atr"])

    sl_mult = {"trending": 1.5, "ranging": 1.0, "transition": 1.2}[regime]
    sl_dist = max(atr * sl_mult, cl * 0.015)
    if max_sl_pct is not None:
        sl_dist = min(sl_dist, cl * max_sl_pct)

    if cl > e20:
        entry = min(cl, max(e20, cl * 0.985))
    else:
        entry = max(e20, cl * 0.98)
    entry = round(entry)
    sl = round(entry - sl_dist)
    sl = max(sl, 1)
    risk = entry - sl

    res = sf(last["res_trailing"])
    if res > entry and (res - entry) >= risk * 1.2:
        tp = round(res)
    else:
        tp = round(entry + risk * 2.2)

    rr = round((tp - entry) / risk, 2) if risk > 0 else 0

    if score >= 70 and cl > e20:
        signal, cls = "⚡ STRONG BUY", "tag-sbuy"
    elif score >= 55:
        signal, cls = "✅ BUY", "tag-buy"
    else:
        signal, cls = "❌ AVOID", "tag-avoid"

    return entry, sl, tp, rr, signal, cls


def calc_position_size(modal, risk_pct, entry, sl, broker_fee_pct, lot_size=100):
    if entry <= sl or entry <= 0:
        return 0, 0, 0, 0
    risk_per_share = entry - sl
    max_risk_rp = modal * risk_pct
    total_fee_pct = (broker_fee_pct + IDX_LEVY * 2) / 100
    max_lot_risk = int(max_risk_rp / (risk_per_share * lot_size))
    max_lot_capital = int((modal * 0.20) / (entry * lot_size))
    max_lot = max(min(max_lot_risk, max_lot_capital), 0)
    position_value = max_lot * entry * lot_size
    actual_risk = max_lot * risk_per_share * lot_size
    fee_total = position_value * total_fee_pct
    return max_lot, position_value, actual_risk, fee_total


# ─────────────────────────────────────────────
# SIMULASI FILL + EXIT (breakeven + trailing ATR) — untuk Riwayat Trading.
# Re-simulasi dari histori harga sejak signal_date s.d. hari ini, jadi
# TIDAK butuh state harian tersimpan (beda dgn paper_trading_log.py yang
# perlu incremental state karena dijalankan otomatis tiap hari).
# ─────────────────────────────────────────────
def evaluate_trade(trade, fee_pct, pullback_days=PULLBACK_DAYS_DEFAULT,
                    breakeven_r=BREAKEVEN_R_DEFAULT, trail_atr_mult=TRAIL_ATR_MULT_DEFAULT,
                    hold_days_max=HOLD_DAYS_MAX_DEFAULT):
    """Return dict berisi status terkini trade: PENDING / CANCELLED / OPEN /
    WIN / LOSS / BREAKEVEN, beserta harga & tanggal relevan."""
    ticker = trade["ticker"]
    signal_date = date.fromisoformat(trade["signal_date"])
    entry, sl, tp = float(trade["entry"]), float(trade["sl"]), float(trade["tp"])

    # PENTING: fetch jauh ke belakang (bukan cuma dari signal_date), supaya ATR
    # dan indikator lain yang dipakai untuk trailing-stop punya warmup yang benar.
    # Kalau di-fetch mepet dari signal_date, ATR(14) awal2 NaN -> default 0 ->
    # trailing stop jadi salah (terlalu ketat, bisa trigger instan).
    try:
        lookback_start = signal_date - timedelta(days=400)
        raw = yf.download(jk(ticker), start=lookback_start,
                           end=date.today() + timedelta(days=1), progress=False)
        full = clean_df(raw)
        if not full.empty:
            full = add_indicators(full)
    except Exception:
        return {"status": "OPEN", "note": "Gagal fetch data", "current_price": entry,
                "pnl_pct": 0, "days": 0}

    if full.empty:
        return {"status": "OPEN", "note": "Data kosong", "current_price": entry,
                "pnl_pct": 0, "days": 0}

    hist = full[full.index.date > signal_date]  # mulai cek dari hari SETELAH sinyal
    if hist.empty:
        return {"status": "PENDING", "note": "Menunggu data hari berikutnya",
                "current_price": entry, "pnl_pct": 0, "days": 0}

    # ── 1. cari fill (pullback + konfirmasi candle) ──
    fill_idx, fill_price = None, entry
    fill_candidates = hist.iloc[:pullback_days]
    for i in range(len(fill_candidates)):
        row = fill_candidates.iloc[i]
        lo, hi, cl_, op_ = sf(row["low"]), sf(row["high"]), sf(row["close"]), sf(row["open"])
        if lo <= entry:
            midpoint = (hi + lo) / 2
            if cl_ >= midpoint:
                fill_price = entry
                if op_ < entry:
                    if op_ <= sl:
                        return {"status": "CANCELLED",
                                "note": "Gap-down tembus SL sebelum sempat fill",
                                "current_price": op_, "pnl_pct": 0, "days": 0}
                    fill_price = op_
                fill_idx = i
            break  # entry tersentuh (lolos konfirmasi atau tidak) -> berhenti cari

    if fill_idx is None:
        days_since_signal = (hist.index[min(len(fill_candidates), len(hist)) - 1].date() - signal_date).days
        if len(fill_candidates) >= pullback_days or days_since_signal > pullback_days:
            return {"status": "CANCELLED", "note": "Tidak pernah pullback ke level entry",
                    "current_price": sf(hist["close"].iloc[-1]), "pnl_pct": 0, "days": 0}
        return {"status": "PENDING", "note": "Menunggu harga pullback ke level entry",
                "current_price": sf(hist["close"].iloc[-1]), "pnl_pct": 0, "days": 0}

    # ── 2. simulasi forward: breakeven + trailing ATR ──
    fill_date = hist.index[fill_idx].date()
    initial_risk = fill_price - sl
    dynamic_sl = sl
    breakeven_moved = False
    forward = hist.iloc[fill_idx + 1:]  # `hist` sudah punya kolom 'atr' dgn warmup benar dari `full`

    outcome, exit_price, exit_date_ = None, None, None
    for j in range(len(forward)):
        row = forward.iloc[j]
        hi, lo, cl_j = sf(row["high"]), sf(row["low"]), sf(row["close"])
        op_j = sf(row["open"])
        atr_j = sf(row["atr"], initial_risk)

        if not breakeven_moved and hi >= fill_price + initial_risk * breakeven_r:
            dynamic_sl = fill_price
            breakeven_moved = True
        if breakeven_moved:
            trail_candidate = round(cl_j - atr_j * trail_atr_mult)
            dynamic_sl = max(dynamic_sl, trail_candidate)

        if hi >= tp:
            exit_price = op_j if op_j > tp else tp
            outcome = "WIN"
            exit_date_ = forward.index[j].date()
            break
        if lo <= dynamic_sl:
            exit_price = op_j if op_j < dynamic_sl else dynamic_sl
            outcome = "BREAKEVEN" if breakeven_moved and exit_price >= fill_price else "LOSS"
            if breakeven_moved and exit_price > fill_price:
                outcome = "WIN"
            exit_date_ = forward.index[j].date()
            break

        days_held_sofar = (forward.index[j].date() - fill_date).days
        if days_held_sofar >= hold_days_max:
            exit_price = cl_j
            outcome = "WIN" if exit_price >= fill_price else "LOSS"
            exit_date_ = forward.index[j].date()
            break

    if outcome:
        raw_pnl = (exit_price - fill_price) / fill_price * 100
        net_pnl = raw_pnl - fee_pct - IDX_LEVY * 2
        return {"status": outcome, "note": f"Closed {outcome}", "entry": fill_price,
                "sl": sl, "tp": tp, "fill_date": str(fill_date), "exit_date": str(exit_date_),
                "exit_price": exit_price, "pnl_pct": round(net_pnl, 2),
                "days": (exit_date_ - fill_date).days}

    # masih open
    curr = sf(hist["close"].iloc[-1])
    days_open = (hist.index[-1].date() - fill_date).days
    raw_pnl = (curr - fill_price) / fill_price * 100
    return {"status": "OPEN", "note": f"Breakeven: {'ya' if breakeven_moved else 'belum'} | "
                                       f"SL dinamis: {dynamic_sl:,.0f}",
            "entry": fill_price, "sl": dynamic_sl, "tp": tp, "fill_date": str(fill_date),
            "current_price": curr, "pnl_pct": round(raw_pnl, 2), "days": days_open}
