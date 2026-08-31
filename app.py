"""
Backtest sederhana untuk idx_screener_v2.py.

Tujuan: mengukur apakah skor tinggi benar-benar berkorelasi dengan
return positif, per band skor (40-49, 50-54, ..., 80-100), termasuk
biaya transaksi (fee broker + levy IDX).

PENTING — perbaikan dibanding logika di app:
get_levels() di app pakai df['high'].rolling(10, center=True) untuk
cari resistance -> ini "mengintip" 5 hari ke depan, tidak valid untuk
backtest. Di sini diganti trailing rolling (rolling(20).max(), tanpa
center) supaya keputusan entry/TP/SL hanya berdasar data yang sudah
terjadi sampai hari itu.

Cara pakai (butuh koneksi internet ke Yahoo Finance, jalankan di
mesin sendiri, bukan di sandbox ini):
    python backtest_v2.py
Output: backtest_trades.csv (per-trade) & backtest_summary.csv (per band skor)
"""
import pandas as pd
import numpy as np

try:
    import yfinance as yf
    import pandas_ta as ta
    HAS_LIVE_DEPS = True
except ImportError:
    HAS_LIVE_DEPS = False

IDX_LEVY = 0.04  # % per sisi -> x2 untuk roundtrip

IDX30 = ["AADI","ADMR","ADRO","AMRT","ANTM","ASII","BBCA","BBNI","BBRI","BMRI",
         "BRPT","BUMI","CPIN","EMTK","EXCL","GOTO","ICBP","INCO","INDF","INKP",
         "JPFA","KLBF","MBMA","MDKA","MEDC","PGAS","PGEO","PTBA","TLKM","TOWR",
         "UNTR","UNVR"]
LQ45 = ["AADI","ADMR","ADRO","AKRA","AMMN","AMRT","ANTM","ASII","BBCA","BBNI",
        "BBRI","BBTN","BMRI","BRPT","BUMI","CPIN","CUAN","DEWA","EMTK","ESSA",
        "EXCL","GOTO","HRTA","ICBP","INCO","INDF","INKP","ISAT","ITMG","JPFA",
        "KLBF","MAPI","MBMA","MDKA","MEDC","PGAS","PGEO","PTBA","SCMA","SMGR",
        "TLKM","TOWR","UNTR","UNVR","WIFI"]


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
    # Trailing resistance saja (bukan centered) -> tidak mengintip masa depan
    df["res_trailing"] = df["high"].rolling(20).max()
    return df


def detect_regime(last):
    adx = sf(last["adx"])
    if adx > 25:
        return "trending"
    elif adx < 20:
        return "ranging"
    return "transition"


def detect_divergence(df_slice, lookback=14):
    if len(df_slice) < lookback + 2:
        return "none"
    prices = df_slice["close"].values[-lookback:]
    rsis = df_slice["rsi"].values[-lookback:]
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


def score_ticker(df_slice):
    """Identik dengan logika di idx_screener_v2.py — hanya beroperasi
    pada df_slice (data s.d. hari ini saja, tidak boleh ada baris masa depan)."""
    last = df_slice.iloc[-1]
    cl, e20, e50, e200 = sf(last["close"]), sf(last["ema20"]), sf(last["ema50"]), sf(last["ema200"])
    rsi, macd, sig, hist = sf(last["rsi"]), sf(last["macd"]), sf(last["sig"]), sf(last["hist"])
    hist_p = sf(df_slice["hist"].iloc[-2]) if len(df_slice) > 2 else 0
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
    div = detect_divergence(df_slice)
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

    adx_recent = sf(df_slice["adx"].iloc[-10:].mean()) if len(df_slice) >= 10 else adx
    if adx_recent < 15:
        score = min(score, 50)
    if score >= 70 and vr < 1.3:
        score = min(score, 69)

    return score, regime


def get_levels_bt(df_slice, score, regime):
    """Versi backtest-safe: resistance trailing saja, tidak centered."""
    last = df_slice.iloc[-1]
    cl, e20, atr = sf(last["close"]), sf(last["ema20"]), sf(last["atr"])

    sl_mult = {"trending": 1.5, "ranging": 1.0, "transition": 1.2}[regime]
    sl_dist = max(atr * sl_mult, cl * 0.015)

    entry = cl if cl > e20 else max(e20, cl * 0.98)
    entry = round(entry)
    sl = round(entry - sl_dist)
    sl = max(sl, 1)
    risk = entry - sl

    res = sf(last["res_trailing"])
    if res > entry and (res - entry) >= risk * 1.2:
        tp = round(res)
    else:
        tp = round(entry + risk * 2.2)

    if score >= 70 and cl > e20:
        signal = "STRONG BUY"
    elif score >= 55:
        signal = "BUY"
    elif score >= 40:
        signal = "WATCHLIST"
    else:
        signal = "AVOID"

    return entry, sl, tp, signal


def simulate_ticker(ticker, df, min_score=40, hold_days_max=10, fee_pct=0.30):
    trades = []
    n = len(df)
    i = 250  # warmup: EMA200 baru valid & stabil setelah ini
    while i < n - 1:
        df_slice = df.iloc[: i + 1]
        e200 = sf(df_slice["ema200"].iloc[-1])
        if e200 <= 0 or pd.isna(df_slice["ema200"].iloc[-1]):
            i += 1
            continue

        score, regime = score_ticker(df_slice)
        entry, sl, tp, signal = get_levels_bt(df_slice, score, regime)

        if score < min_score or signal == "AVOID":
            i += 1
            continue

        end_idx = min(i + hold_days_max, n - 1)
        exit_idx, exit_price, outcome = None, None, None
        for j in range(i + 1, end_idx + 1):
            hi, lo = sf(df["high"].iloc[j]), sf(df["low"].iloc[j])
            if hi >= tp:
                exit_idx, exit_price, outcome = j, tp, "WIN"
                break
            if lo <= sl:
                exit_idx, exit_price, outcome = j, sl, "LOSS"
                break
        if exit_idx is None:
            exit_idx = end_idx
            exit_price = sf(df["close"].iloc[end_idx])
            outcome = "WIN" if exit_price >= entry else "LOSS"

        raw_pnl = (exit_price - entry) / entry * 100
        net_pnl = raw_pnl - fee_pct - IDX_LEVY * 2

        trades.append({
            "ticker": ticker, "entry_date": str(df.index[i].date()), "score": score,
            "regime": regime, "signal": signal, "entry": entry, "sl": sl, "tp": tp,
            "exit_date": str(df.index[exit_idx].date()), "exit_price": exit_price,
            "outcome": outcome, "raw_pnl_pct": round(raw_pnl, 2),
            "net_pnl_pct": round(net_pnl, 2), "days_held": exit_idx - i,
        })
        i = exit_idx + 1  # tidak overlap: satu posisi per ticker pada satu waktu

    return trades


def band_label(score):
    for lo, label in [(80, "80-100"), (75, "75-79"), (70, "70-74"), (65, "65-69"),
                       (60, "60-64"), (55, "55-59"), (50, "50-54"), (40, "40-49")]:
        if score >= lo:
            return label
    return "<40"


BAND_ORDER = ["40-49", "50-54", "55-59", "60-64", "65-69", "70-74", "75-79", "80-100"]


def summarize(df_trades):
    if df_trades.empty:
        print("Tidak ada trade yang tercatat.")
        return pd.DataFrame()
    df_trades = df_trades.copy()
    df_trades["band"] = df_trades["score"].apply(band_label)
    rows = []
    for b in BAND_ORDER:
        sub = df_trades[df_trades["band"] == b]
        if sub.empty:
            continue
        n = len(sub)
        win_rate = (sub["outcome"] == "WIN").mean() * 100
        avg_net = sub["net_pnl_pct"].mean()
        wins = sub[sub["outcome"] == "WIN"]["net_pnl_pct"]
        losses = sub[sub["outcome"] == "LOSS"]["net_pnl_pct"]
        avg_win = wins.mean() if not wins.empty else 0
        avg_loss = losses.mean() if not losses.empty else 0
        expectancy = (win_rate / 100) * avg_win + (1 - win_rate / 100) * avg_loss
        rows.append({
            "Band Skor": b, "N Trades": n, "Win Rate %": round(win_rate, 1),
            "Avg Net PnL %": round(avg_net, 2), "Avg Win %": round(avg_win, 2),
            "Avg Loss %": round(avg_loss, 2), "Expectancy % / trade": round(expectancy, 2),
        })
    summary = pd.DataFrame(rows)
    return summary


def run_backtest(tickers, period="2y", min_score=40, hold_days_max=10, fee_pct=0.30, verbose=True):
    if not HAS_LIVE_DEPS:
        raise RuntimeError("yfinance / pandas_ta belum terinstal di environment ini.")
    all_trades = []
    for idx, t in enumerate(tickers):
        try:
            raw = yf.download(jk(t), period=period, interval="1d", progress=False)
            df = clean_df(raw)
            if df.empty or len(df) < 280:
                if verbose:
                    print(f"[skip] {t}: data kurang ({len(df)} baris)")
                continue
            df = add_indicators(df)
            trades = simulate_ticker(t, df, min_score, hold_days_max, fee_pct)
            all_trades.extend(trades)
            if verbose:
                print(f"[{idx+1}/{len(tickers)}] {t}: {len(trades)} trade")
        except Exception as e:
            if verbose:
                print(f"[error] {t}: {e}")
    return pd.DataFrame(all_trades)


if __name__ == "__main__":
    universe = list(dict.fromkeys(IDX30 + LQ45))
    print(f"Menjalankan backtest untuk {len(universe)} saham, periode 2 tahun...")
    df_trades = run_backtest(universe, period="2y", min_score=40, hold_days_max=10, fee_pct=0.30)
    df_trades.to_csv("backtest_trades.csv", index=False)
    print(f"\nTotal trade tersimulasi: {len(df_trades)}")

    summary = summarize(df_trades)
    if not summary.empty:
        summary.to_csv("backtest_summary.csv", index=False)
        print("\n=== Expectancy per Band Skor (net biaya) ===")
        print(summary.to_string(index=False))
        print("\nFile tersimpan: backtest_trades.csv, backtest_summary.csv")
