import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
from pathlib import Path
import json
import pytz

# ─────────────────────────────────────────────
# PAGE CONFIG + CSS RINGAN (native components > custom HTML)
# ─────────────────────────────────────────────
st.set_page_config(page_title="IDX Screener — Simple", page_icon="📈", layout="wide")

st.markdown("""
<style>
.block-container { padding-top: 1.2rem; }
.big-score { font-size: 34px; font-weight: 900; }
.tag { padding: 3px 12px; border-radius: 20px; font-weight: 700; font-size: 13px; }
.tag-sbuy { background:#003322; color:#00ff99; }
.tag-buy  { background:#002e18; color:#44dd88; }
.tag-watch{ background:#332200; color:#ffcc00; }
.tag-avoid{ background:#330011; color:#ff4466; }
</style>
""", unsafe_allow_html=True)

TZ_JKT = pytz.timezone("Asia/Jakarta")
LOG_FILE = Path("idx_trade_log_v2.json")

# ─────────────────────────────────────────────
# UNIVERSE — dipangkas, cuma 2 list inti + gabungan
# ─────────────────────────────────────────────
IDX30 = ["AADI","ADMR","ADRO","AMRT","ANTM","ASII","BBCA","BBNI","BBRI","BMRI",
         "BRPT","BUMI","CPIN","EMTK","EXCL","GOTO","ICBP","INCO","INDF","INKP",
         "JPFA","KLBF","MBMA","MDKA","MEDC","PGAS","PGEO","PTBA","TLKM","TOWR",
         "UNTR","UNVR"]

LQ45 = ["AADI","ADMR","ADRO","AKRA","AMMN","AMRT","ANTM","ASII","BBCA","BBNI",
        "BBRI","BBTN","BMRI","BRPT","BUMI","CPIN","CUAN","DEWA","EMTK","ESSA",
        "EXCL","GOTO","HRTA","ICBP","INCO","INDF","INKP","ISAT","ITMG","JPFA",
        "KLBF","MAPI","MBMA","MDKA","MEDC","PGAS","PGEO","PTBA","SCMA","SMGR",
        "TLKM","TOWR","UNTR","UNVR","WIFI"]

UNIVERSES = {
    "IDX30 — Blue Chip": IDX30,
    "LQ45 — Liquid 45": LQ45,
    "Gabungan (IDX30 + LQ45)": list(dict.fromkeys(IDX30 + LQ45)),
}

BROKER_FEES = {
    "Ajaib / Neo (0.20%)": 0.20,
    "Stockbit (0.30%)": 0.30,
    "Sekuritas standar (0.40%)": 0.40,
}
IDX_LEVY = 0.04  # per sisi

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def jk(t): return t if t.endswith(".JK") else f"{t}.JK"

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
    except Exception:
        return default

# ─────────────────────────────────────────────
# FETCH — BATCH, bukan loop per-ticker (fix bug lambat di versi lama)
# TTL fixed 30 menit — simple & benar (versi lama pakai ttl dinamis
# yang ternyata "beku" karena st.cache_data mengevaluasi ttl sekali saja
# saat decorator dibaca, bukan tiap dipanggil).
# ─────────────────────────────────────────────
@st.cache_data(ttl=1800, show_spinner=False)
def fetch_batch(tickers: tuple, period="1y"):
    """Download banyak ticker sekaligus. Return dict {ticker: df_indikator}."""
    raw = yf.download(list(tickers), period=period, interval="1d",
                       group_by="ticker", threads=True, progress=False,
                       auto_adjust=False)
    result = {}
    single = (len(tickers) == 1)
    for t in tickers:
        try:
            df = clean_df(raw.copy()) if single else clean_df(raw[t].copy())
        except Exception:
            continue
        if df is None or df.empty or len(df) < 60:
            continue
        df = add_indicators(df)
        result[t] = df
    return result

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_one(ticker, period="1y"):
    df = clean_df(yf.download(ticker, period=period, interval="1d", progress=False))
    if df.empty or len(df) < 60:
        return None
    return add_indicators(df)

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
    df["daily_value"] = (df["close"] * df["volume"]).tail(20).mean()
    return df

# ─────────────────────────────────────────────
# REGIME
# ─────────────────────────────────────────────
def detect_regime(last):
    adx = sf(last["adx"])
    if adx > 25:
        return "trending"
    elif adx < 20:
        return "ranging"
    return "transition"

# ─────────────────────────────────────────────
# RSI DIVERGENCE (sederhana — 2 lembah terakhir)
# ─────────────────────────────────────────────
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
# SCORING — 3 komponen saja (Trend, Momentum, Volume), regime-aware
# ─────────────────────────────────────────────
def score_ticker(df):
    last = df.iloc[-1]
    cl, e20, e50, e200 = sf(last["close"]), sf(last["ema20"]), sf(last["ema50"]), sf(last["ema200"])
    rsi, macd, sig, hist = sf(last["rsi"]), sf(last["macd"]), sf(last["sig"]), sf(last["hist"])
    hist_p = sf(df["hist"].iloc[-2]) if len(df) > 2 else 0
    adx, dmp, dmn = sf(last["adx"]), sf(last["dmp"]), sf(last["dmn"])
    vr = sf(last["vol_ratio"], 1.0)
    is_green = cl >= sf(last["open"])

    regime = detect_regime(last)

    # Trend (0-100)
    t = 0
    if cl > e20: t += 25
    if cl > e50: t += 20
    if e20 > e50: t += 15
    if e50 > e200 > 0: t += 15
    if adx > 25 and dmp > dmn: t += 25
    elif adx > 20 and dmp > dmn: t += 12
    t = max(0, min(t, 100))

    # Momentum (0-100)
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

    # Volume (0-100)
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

    # Cap kalau ADX sangat rendah (sideways murni — sinyal trend tidak valid)
    adx_recent = sf(df["adx"].iloc[-10:].mean()) if len(df) >= 10 else adx
    if adx_recent < 15:
        score = min(score, 50)

    # Cap kalau skor tinggi tapi volume tidak konfirmasi
    if score >= 70 and vr < 1.3:
        score = min(score, 69)

    detail = {
        "Regime": regime, "Trend": t, "Momentum": m, "Volume": v,
        "RSI": round(rsi, 1), "ADX": round(adx, 1), "Divergensi": div,
        "MACD Bullish": macd > sig,
    }
    return score, detail, regime

# ─────────────────────────────────────────────
# ENTRY / SL / TP — ATR based, target ke resistance terdekat kalau ada
# ─────────────────────────────────────────────
def get_levels(df, score, regime):
    last = df.iloc[-1]
    cl, e20, atr = sf(last["close"]), sf(last["ema20"]), sf(last["atr"])

    sl_mult = {"trending": 1.5, "ranging": 1.0, "transition": 1.2}[regime]
    sl_dist = max(atr * sl_mult, cl * 0.015)

    entry = cl if cl > e20 else max(e20, cl * 0.98)
    entry = round(entry)
    sl = round(entry - sl_dist)
    sl = max(sl, 1)
    risk = entry - sl

    # Resistance terdekat dari swing high 60 hari terakhir
    highs = df["high"].rolling(10, center=True).max().dropna()
    candidates = sorted([h for h in highs.unique() if h > entry])
    tp_res = next((h for h in candidates if (h - entry) >= risk * 1.2), None)
    tp = round(tp_res) if tp_res else round(entry + risk * 2.2)

    rr = round((tp - entry) / risk, 2) if risk > 0 else 0

    if score >= 70 and cl > e20:
        signal, cls = "⚡ STRONG BUY", "tag-sbuy"
    elif score >= 55:
        signal, cls = "✅ BUY", "tag-buy"
    elif score >= 40:
        signal, cls = "🔄 WATCHLIST", "tag-watch"
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
# TRACKER I/O
# ─────────────────────────────────────────────
def load_log():
    if LOG_FILE.exists():
        with open(LOG_FILE) as f:
            return json.load(f)
    return []

def save_log(logs):
    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=2, default=str)

def save_scan_to_log(df_res, hold_days):
    today = datetime.now(TZ_JKT).strftime("%Y-%m-%d")
    logs = load_log()
    existing = {(e["date"], e["ticker"]) for e in logs}
    n = 0
    for _, row in df_res.iterrows():
        key = (today, row["Ticker"])
        if key in existing:
            continue
        logs.append({
            "id": f"{today}_{row['Ticker']}", "date": today, "ticker": row["Ticker"],
            "signal": row["Signal"], "score": int(row["Score"]),
            "entry": float(row["Entry"]), "sl": float(row["SL"]), "tp": float(row["TP"]),
            "hold_days": hold_days, "exit_price": None, "exit_date": None,
            "status": "OPEN", "note": "",
        })
        n += 1
    save_log(logs)
    return n

def eval_trade(trade):
    ticker = trade["ticker"]
    entry, sl, tp = float(trade["entry"]), float(trade["sl"]), float(trade["tp"])
    start = date.fromisoformat(trade["date"])
    hold = trade.get("hold_days", 3)
    today = datetime.now(TZ_JKT).date()
    days = (today - start).days
    try:
        hist = clean_df(yf.download(jk(ticker), start=start - timedelta(days=1),
                                     end=today + timedelta(days=1), progress=False))
        hist = hist[hist.index.date >= start]
        if hist.empty:
            return "OPEN", entry, days, "Data kosong", 0
        hi, lo, last_c = hist["high"].max(), hist["low"].min(), sf(hist["close"].iloc[-1])
        if hi >= tp:
            return "WIN", tp, days, "TP tercapai", round((tp - entry) / entry * 100, 2)
        if lo <= sl:
            return "LOSS", sl, days, "SL tersentuh", round((sl - entry) / entry * 100, 2)
        if days >= hold:
            pnl = round((last_c - entry) / entry * 100, 2)
            return ("WIN" if pnl >= 0 else "LOSS"), last_c, days, f"Force close D{hold}", pnl
        return "OPEN", last_c, days, "Masih berjalan", round((last_c - entry) / entry * 100, 2)
    except Exception:
        return "OPEN", entry, days, "Gagal fetch", 0

def tracker_stats(logs):
    closed = [l for l in logs if l["status"] in ("WIN", "LOSS")]
    wins = [l for l in closed if l["status"] == "WIN"]
    pnls = [(float(l["exit_price"]) - float(l["entry"])) / float(l["entry"]) * 100
            for l in closed if l.get("exit_price")]
    return {
        "closed": len(closed), "open": len(logs) - len(closed),
        "win_rate": round(len(wins) / len(closed) * 100, 1) if closed else 0,
        "avg_pnl": round(sum(pnls) / len(pnls), 2) if pnls else 0,
    }

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Pengaturan")
    modal_total = st.number_input("Modal Total (Rp)", value=50_000_000, step=5_000_000, format="%d")
    risk_per_trade = st.slider("Max Risk per Trade (%)", 0.5, 5.0, 2.0, 0.5) / 100
    broker_choice = st.selectbox("Broker", list(BROKER_FEES.keys()))
    broker_fee = BROKER_FEES[broker_choice]
    st.caption(f"🕐 WIB: {datetime.now(TZ_JKT).strftime('%d %b %Y, %H:%M')}")

st.markdown("<h1 style='text-align:center;'>📈 IDX Screener — Simple</h1>", unsafe_allow_html=True)
st.caption("<p style='text-align:center;color:#889'>Trend · Momentum · Volume — regime-aware scoring</p>",
           unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["🔍 Scanner", "📊 Analisa Saham", "🗂️ Riwayat Trading"])

# ══════════════════════════════════════════════
# TAB 1 — SCANNER
# ══════════════════════════════════════════════
with tab1:
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        universe_choice = st.selectbox("Universe", list(UNIVERSES.keys()))
    with c2:
        min_score = st.slider("Min Score", 0, 100, 55)
    with c3:
        top_n = st.number_input("Top N", 5, 30, 10)
    with c4:
        hold_days = st.radio("Hold (hari)", [1, 3], index=1, horizontal=True)

    universe = UNIVERSES[universe_choice]
    st.caption(f"Universe aktif: **{len(universe)} saham**")

    if st.button("🚀 Scan Sekarang", type="primary", use_container_width=True):
        tickers = tuple(jk(t) for t in universe)
        with st.spinner(f"Mengambil data {len(tickers)} saham..."):
            data = fetch_batch(tickers, "1y")

        results = []
        for t, df in data.items():
            name = t.replace(".JK", "")
            score, detail, regime = score_ticker(df)
            if score < min_score:
                continue
            entry, sl, tp, rr, signal, cls = get_levels(df, score, regime)
            if "AVOID" in signal:
                continue
            results.append({
                "Ticker": name, "Score": score, "Signal": signal, "Regime": regime.title(),
                "Entry": entry, "SL": sl, "TP": tp, "R:R": rr,
                "RSI": detail["RSI"], "Vol": round(sf(df["vol_ratio"].iloc[-1]), 2),
                "_cls": cls,
            })

        if not results:
            st.warning("Tidak ada saham yang lolos filter. Coba turunkan Min Score.")
        else:
            df_res = pd.DataFrame(results).sort_values("Score", ascending=False).head(top_n)
            n_saved = save_scan_to_log(df_res, hold_days)
            if n_saved:
                st.success(f"💾 {n_saved} rekomendasi baru disimpan ke tracker.")

            st.markdown(f"### Top {len(df_res)} Rekomendasi")
            st.dataframe(
                df_res.drop(columns=["_cls"]),
                use_container_width=True, hide_index=True,
                column_config={
                    "Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%d"),
                    "Entry": st.column_config.NumberColumn(format="%d"),
                    "SL": st.column_config.NumberColumn(format="%d"),
                    "TP": st.column_config.NumberColumn(format="%d"),
                },
            )

            st.markdown("#### Detail & Position Sizing")
            for _, row in df_res.iterrows():
                with st.container(border=True):
                    left, right = st.columns([2, 1])
                    with left:
                        st.markdown(
                            f"<span style='font-size:22px;font-weight:900;color:#00bbff'>{row['Ticker']}</span>"
                            f"&nbsp;&nbsp;<span class='tag {row['_cls']}'>{row['Signal']}</span>"
                            f"&nbsp;&nbsp;<span style='color:#889'>{row['Regime']} | RSI {row['RSI']} | Vol {row['Vol']}x</span>",
                            unsafe_allow_html=True,
                        )
                        st.markdown(f"<div class='big-score'>{row['Score']}<span style='font-size:14px;color:#889'>/100</span></div>",
                                    unsafe_allow_html=True)
                    with right:
                        st.metric("Entry", f"{row['Entry']:,}")
                        st.metric("SL / TP", f"{row['SL']:,} / {row['TP']:,}", f"R:R 1:{row['R:R']}")

                    max_lot, pos_val, actual_risk, fee_total = calc_position_size(
                        modal_total, risk_per_trade, row["Entry"], row["SL"], broker_fee
                    )
                    if max_lot > 0:
                        sc1, sc2, sc3 = st.columns(3)
                        sc1.metric("Max Lot", f"{max_lot} lot")
                        sc2.metric("Nilai Posisi", f"Rp {pos_val:,.0f}")
                        sc3.metric("Risk (Rp)", f"Rp {actual_risk:,.0f}")
                    else:
                        st.warning("Modal tidak cukup untuk 1 lot dengan risk parameter ini.")

# ══════════════════════════════════════════════
# TAB 2 — ANALISA SAHAM
# ══════════════════════════════════════════════
with tab2:
    ticker_input = st.text_input("Kode Saham", "BBRI").upper().strip()

    if ticker_input and st.button("🔍 Analisis", type="primary"):
        with st.spinner(f"Menganalisis {ticker_input}..."):
            df = fetch_one(jk(ticker_input), "1y")

        if df is None:
            st.error("Data tidak ditemukan / kurang panjang.")
        else:
            score, detail, regime = score_ticker(df)
            entry, sl, tp, rr, signal, cls = get_levels(df, score, regime)
            last = df.iloc[-1]

            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Score", f"{score}/100")
            m2.metric("Signal", signal)
            m3.metric("Close", f"{sf(last['close']):,.0f}")
            m4.metric("RSI", f"{detail['RSI']}")
            m5.metric("ADX", f"{detail['ADX']}")

            st.caption(f"Regime: **{regime.title()}** | Divergensi RSI: **{detail['Divergensi']}** | "
                       f"MACD Bullish: **{'Ya' if detail['MACD Bullish'] else 'Tidak'}**")

            with st.container(border=True):
                cA, cB, cC = st.columns(3)
                cA.metric("Entry", f"{entry:,}")
                cB.metric("Stop Loss", f"{sl:,}", f"-{(entry-sl)/entry*100:.1f}%")
                cC.metric("Take Profit", f"{tp:,}", f"+{(tp-entry)/entry*100:.1f}%")
                st.caption(f"Risk : Reward = 1 : {rr}")

                max_lot, pos_val, actual_risk, fee_total = calc_position_size(
                    modal_total, risk_per_trade, entry, sl, broker_fee
                )
                if max_lot > 0:
                    sc1, sc2, sc3 = st.columns(3)
                    sc1.metric("Max Lot", f"{max_lot} lot")
                    sc2.metric("Nilai Posisi", f"Rp {pos_val:,.0f}")
                    sc3.metric("Est. Biaya", f"Rp {fee_total:,.0f}")

            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=df.index, open=df["open"], high=df["high"],
                                          low=df["low"], close=df["close"],
                                          increasing_line_color="#00ff99",
                                          decreasing_line_color="#ff4466", name="OHLC"))
            fig.add_trace(go.Scatter(x=df.index, y=df["ema20"], line=dict(color="orange", width=1.2), name="EMA20"))
            fig.add_trace(go.Scatter(x=df.index, y=df["ema50"], line=dict(color="#8888ff", width=1.2), name="EMA50"))
            fig.add_trace(go.Scatter(x=df.index, y=df["ema200"], line=dict(color="#ff6688", width=1.2, dash="dot"), name="EMA200"))
            fig.add_hline(y=sl, line_dash="dash", line_color="#ff4466", annotation_text=f"SL {sl:,}")
            fig.add_hline(y=tp, line_dash="dash", line_color="#00ff99", annotation_text=f"TP {tp:,}")
            fig.add_hline(y=entry, line_dash="dot", line_color="#ffcc00", annotation_text=f"Entry {entry:,}")
            fig.update_layout(height=480, template="plotly_dark", xaxis_rangeslider_visible=False,
                               margin=dict(l=0, r=0, t=10, b=0),
                               legend=dict(orientation="h", y=1.02))
            # Trim tampilan ke 6 bulan terakhir biar tidak terlalu padat
            cutoff = df.index[-1] - pd.DateOffset(months=6)
            fig.update_xaxes(range=[cutoff, df.index[-1]])
            st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════
# TAB 3 — RIWAYAT TRADING
# ══════════════════════════════════════════════
with tab3:
    logs = load_log()
    if not logs:
        st.info("Belum ada data. Jalankan Scanner untuk menghasilkan rekomendasi.")
    else:
        updated = False
        for t in logs:
            if t["status"] != "OPEN":
                continue
            status, ep, days, note, pnl = eval_trade(t)
            if status != "OPEN":
                t.update({"status": status, "exit_price": ep,
                          "exit_date": str(datetime.now(TZ_JKT).date()), "note": note})
                updated = True
        if updated:
            save_log(logs)

        stats = tracker_stats(logs)
        c1, c2, c3 = st.columns(3)
        c1.metric("Win Rate", f"{stats['win_rate']}%")
        c2.metric("Avg P&L", f"{stats['avg_pnl']:+.2f}%")
        c3.metric("Open Trades", stats["open"])
        st.caption(f"⚠️ P&L belum termasuk biaya transaksi (~{broker_fee + IDX_LEVY*2:.2f}% roundtrip).")

        open_trades = [l for l in logs if l["status"] == "OPEN"]
        if open_trades:
            st.markdown("#### Trade Aktif")
            for trade in open_trades:
                _, curr, days, note, pnl = eval_trade(trade)
                with st.container(border=True):
                    st.markdown(
                        f"**{trade['ticker']}** — Entry {float(trade['entry']):,.0f} → Now {curr:,.0f} "
                        f"({pnl:+.2f}%) · {note} · D{days}/{trade.get('hold_days', 3)}"
                    )

        closed = [l for l in logs if l["status"] != "OPEN"]
        if closed:
            st.markdown("#### Riwayat Tertutup")
            st.dataframe(
                pd.DataFrame(closed)[["date", "ticker", "signal", "score", "entry", "sl", "tp",
                                       "exit_price", "status", "note"]].sort_values("date", ascending=False),
                use_container_width=True, hide_index=True,
            )

        cdl, crst = st.columns([3, 1])
        with cdl:
            st.download_button("⬇️ Download CSV", pd.DataFrame(logs).to_csv(index=False).encode("utf-8"),
                                "idx_trade_log_v2.csv", "text/csv")
        with crst:
            if st.button("🗑️ Reset Data"):
                save_log([])
                st.rerun()
