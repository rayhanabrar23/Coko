import streamlit as st
import pandas as pd
from datetime import datetime, date
from pathlib import Path
import json
import pytz

from logic_scanner import (
    UNIVERSES, BROKER_FEES, MIN_SCORE_DEFAULT, HOLD_DAYS_MAX_DEFAULT,
    PULLBACK_DAYS_DEFAULT, MAX_SL_PCT_DEFAULT, MIN_AVG_DOLLAR_VALUE_DEFAULT,
    jk, sf, fetch_batch, fetch_one, score_ticker, get_levels,
    calc_position_size, evaluate_trade,
)

# ─────────────────────────────────────────────
# PAGE CONFIG + CSS
# ─────────────────────────────────────────────
st.set_page_config(page_title="IDX Screener", page_icon="📈", layout="wide")

st.markdown("""
<style>
.block-container { padding-top: 1.2rem; }
.big-score { font-size: 34px; font-weight: 900; }
.tag { padding: 3px 12px; border-radius: 20px; font-weight: 700; font-size: 13px; }
.tag-sbuy { background:#003322; color:#00ff99; }
.tag-buy  { background:#002e18; color:#44dd88; }
.tag-avoid{ background:#330011; color:#ff4466; }
</style>
""", unsafe_allow_html=True)

TZ_JKT = pytz.timezone("Asia/Jakarta")
LOG_FILE = Path("idx_trade_log.json")


def load_log():
    if LOG_FILE.exists():
        with open(LOG_FILE) as f:
            return json.load(f)
    return []


def save_log(logs):
    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=2, default=str)


def save_scan_to_log(df_res):
    today = datetime.now(TZ_JKT).strftime("%Y-%m-%d")
    logs = load_log()
    existing = {(e["signal_date"], e["ticker"]) for e in logs}
    n = 0
    for _, row in df_res.iterrows():
        key = (today, row["Ticker"])
        if key in existing:
            continue
        logs.append({
            "id": f"{today}_{row['Ticker']}", "ticker": row["Ticker"], "signal_date": today,
            "signal": row["Signal"], "score": int(row["Score"]), "regime": row["Regime"],
            "entry": float(row["Entry"]), "sl": float(row["SL"]), "tp": float(row["TP"]),
            "status": "PENDING",
        })
        n += 1
    save_log(logs)
    return n


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Pengaturan")
    modal_total = st.number_input("Modal Total (Rp)", value=100_000_000, step=5_000_000, format="%d")
    risk_per_trade = st.slider("Max Risk per Trade (%)", 0.5, 5.0, 2.0, 0.5) / 100
    broker_choice = st.selectbox("Broker", list(BROKER_FEES.keys()))
    broker_fee = BROKER_FEES[broker_choice]
    st.markdown("---")
    hold_days_max = st.slider("Hold Days Max", 5, 30, HOLD_DAYS_MAX_DEFAULT,
                               help="Sesuai backtest_v8: 25 hari")
    max_sl_pct = st.slider("Cap Lebar SL Maks (%)", 3, 15, int(MAX_SL_PCT_DEFAULT * 100)) / 100
    min_dollar_value = st.number_input("Min Nilai Transaksi Harian (Rp)",
                                        value=MIN_AVG_DOLLAR_VALUE_DEFAULT, step=500_000_000,
                                        format="%d")
    st.caption(f"🕐 WIB: {datetime.now(TZ_JKT).strftime('%d %b %Y, %H:%M')}")
    st.caption("Parameter default di sini disamakan dgn backtest_v8.py — "
               "ubah dengan hati-hati kalau lagi validasi forward-test.")

st.markdown("<h1 style='text-align:center;'>📈 IDX Screener</h1>", unsafe_allow_html=True)
st.caption("<p style='text-align:center;color:#889'>Konsisten dengan backtest_v8 — "
           "entry pullback, breakeven-stop, trailing ATR</p>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["🔍 Scanner", "📊 Analisa Saham", "🗂️ Riwayat Trading"])

# ══════════════════════════════════════════════
# TAB 1 — SCANNER
# ══════════════════════════════════════════════
with tab1:
    c1, c2, c3 = st.columns(3)
    with c1:
        universe_choice = st.selectbox("Universe", list(UNIVERSES.keys()), index=2)
    with c2:
        min_score = st.slider("Min Score", 0, 100, MIN_SCORE_DEFAULT)
    with c3:
        top_n = st.number_input("Top N", 5, 40, 15)

    universe = UNIVERSES[universe_choice]
    st.caption(f"Universe aktif: **{len(universe)} saham** | Sinyal ditampilkan hanya BUY/STRONG BUY "
               f"(skor≥55) — WATCHLIST dibuang, terbukti expectancy negatif di backtest.")

    if st.button("🚀 Scan Sekarang", type="primary", use_container_width=True):
        tickers = tuple(jk(t) for t in universe)
        with st.spinner(f"Mengambil data {len(tickers)} saham..."):
            data = fetch_batch(tickers, "2y")

        results = []
        for t, df in data.items():
            name = t.replace(".JK", "")
            median_dv = df["dollar_value_ma20"].median()
            if pd.isna(median_dv) or median_dv < min_dollar_value:
                continue
            score, detail, regime = score_ticker(df)
            if score < min_score:
                continue
            entry, sl, tp, rr, signal, cls = get_levels(df, score, regime, max_sl_pct=max_sl_pct)
            if "AVOID" in signal:
                continue
            results.append({
                "Ticker": name, "Score": score, "Signal": signal, "Regime": regime.title(),
                "Entry": entry, "SL": sl, "TP": tp, "R:R": rr,
                "RSI": detail["RSI"], "Vol": round(sf(df["vol_ratio"].iloc[-1]), 2),
                "DailyVal": f"Rp{median_dv/1e9:.1f}M", "_cls": cls,
            })

        if not results:
            st.warning("Tidak ada saham yang lolos filter. Coba turunkan Min Score atau likuiditas.")
        else:
            df_res = pd.DataFrame(results).sort_values("Score", ascending=False).head(top_n)
            n_saved = save_scan_to_log(df_res)
            if n_saved:
                st.success(f"💾 {n_saved} sinyal baru disimpan ke Riwayat Trading (status PENDING).")

            st.markdown(f"### Top {len(df_res)} Sinyal")
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
            st.caption("⚠️ **Entry = limit price target**, bukan harga beli langsung. Sinyal baru "
                       "dianggap valid kalau harga betulan pullback ke level Entry dalam "
                       f"{PULLBACK_DAYS_DEFAULT} hari (dicek otomatis di tab Riwayat Trading).")

            st.markdown("#### Detail & Position Sizing")
            for _, row in df_res.iterrows():
                with st.container(border=True):
                    left, right = st.columns([2, 1])
                    with left:
                        st.markdown(
                            f"<span style='font-size:22px;font-weight:900;color:#00bbff'>{row['Ticker']}</span>"
                            f"&nbsp;&nbsp;<span class='tag {row['_cls']}'>{row['Signal']}</span>"
                            f"&nbsp;&nbsp;<span style='color:#889'>{row['Regime']} | RSI {row['RSI']} | "
                            f"Vol {row['Vol']}x | {row['DailyVal']}/hari</span>",
                            unsafe_allow_html=True,
                        )
                        st.markdown(f"<div class='big-score'>{row['Score']}"
                                    f"<span style='font-size:14px;color:#889'>/100</span></div>",
                                    unsafe_allow_html=True)
                    with right:
                        st.metric("Target Entry", f"{row['Entry']:,}")
                        st.metric("SL awal / TP", f"{row['SL']:,} / {row['TP']:,}", f"R:R 1:{row['R:R']}")

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
            df = fetch_one(jk(ticker_input), "2y")

        if df is None:
            st.error("Data tidak ditemukan / kurang panjang (butuh min. ~260 hari data).")
        else:
            score, detail, regime = score_ticker(df)
            entry, sl, tp, rr, signal, cls = get_levels(df, score, regime, max_sl_pct=max_sl_pct)
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
                cA.metric("Target Entry (limit)", f"{entry:,}")
                cB.metric("Stop Loss awal", f"{sl:,}", f"-{(entry-sl)/entry*100:.1f}%")
                cC.metric("Take Profit", f"{tp:,}", f"+{(tp-entry)/entry*100:.1f}%")
                st.caption(f"Risk : Reward = 1 : {rr}  |  SL akan naik ke breakeven setelah profit "
                           f"1×risk, lalu trailing ikut ATR — bukan diam di angka ini selamanya.")

                max_lot, pos_val, actual_risk, fee_total = calc_position_size(
                    modal_total, risk_per_trade, entry, sl, broker_fee
                )
                if max_lot > 0:
                    sc1, sc2, sc3 = st.columns(3)
                    sc1.metric("Max Lot", f"{max_lot} lot")
                    sc2.metric("Nilai Posisi", f"Rp {pos_val:,.0f}")
                    sc3.metric("Est. Biaya", f"Rp {fee_total:,.0f}")

            import plotly.graph_objects as go
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
                               margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h", y=1.02))
            cutoff = df.index[-1] - pd.DateOffset(months=6)
            fig.update_xaxes(range=[cutoff, df.index[-1]])
            st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════
# TAB 3 — RIWAYAT TRADING
# ══════════════════════════════════════════════
with tab3:
    logs = load_log()
    if not logs:
        st.info("Belum ada data. Jalankan Scanner untuk menghasilkan sinyal.")
    else:
        if st.button("🔄 Update Status Semua Trade"):
            updated = False
            with st.spinner("Mengecek harga terkini untuk trade yang belum final..."):
                for t in logs:
                    if t["status"] not in ("PENDING", "OPEN"):
                        continue
                    result = evaluate_trade(t, fee_pct=broker_fee, hold_days_max=hold_days_max)
                    if result["status"] != t["status"]:
                        updated = True
                    t.update({
                        "status": result["status"],
                        "note": result.get("note", ""),
                        "current_or_exit_price": result.get("exit_price", result.get("current_price")),
                        "pnl_pct": result.get("pnl_pct", 0),
                        "fill_date": result.get("fill_date", t.get("fill_date")),
                        "exit_date": result.get("exit_date", t.get("exit_date")),
                    })
            if updated:
                save_log(logs)
            st.success("Status diperbarui.")
            st.rerun()

        closed = [l for l in logs if l["status"] in ("WIN", "LOSS", "BREAKEVEN")]
        if closed:
            wins = [l for l in closed if l["status"] == "WIN"]
            win_rate = round(len(wins) / len(closed) * 100, 1)
            avg_pnl = round(sum(l.get("pnl_pct", 0) for l in closed) / len(closed), 2)
            c1, c2, c3 = st.columns(3)
            c1.metric("Win Rate", f"{win_rate}%")
            c2.metric("Avg Net PnL", f"{avg_pnl:+.2f}%")
            c3.metric("Trade Closed", len(closed))
            st.caption("PnL sudah termasuk biaya transaksi (fee broker + levy IDX).")

        pending = [l for l in logs if l["status"] == "PENDING"]
        open_trades = [l for l in logs if l["status"] == "OPEN"]

        if open_trades:
            st.markdown("#### 🟢 Posisi Terbuka")
            for t in open_trades:
                with st.container(border=True):
                    st.markdown(f"**{t['ticker']}** — {t['signal']} (skor {t['score']}) | "
                                f"Entry {float(t['entry']):,.0f} → Sekarang "
                                f"{t.get('current_or_exit_price', 0):,.0f} "
                                f"({t.get('pnl_pct', 0):+.2f}%)")
                    st.caption(t.get("note", ""))

        if pending:
            st.markdown("#### 🟡 Menunggu Fill (Pending)")
            st.dataframe(
                pd.DataFrame(pending)[["ticker", "signal_date", "signal", "score", "entry", "sl", "tp"]],
                use_container_width=True, hide_index=True,
            )

        if closed:
            st.markdown("#### 📜 Riwayat Closed")
            df_closed = pd.DataFrame(closed)
            cols = ["ticker", "signal_date", "signal", "score", "entry", "sl", "tp",
                    "current_or_exit_price", "status", "pnl_pct"]
            cols = [c for c in cols if c in df_closed.columns]
            st.dataframe(df_closed[cols].sort_values("signal_date", ascending=False),
                         use_container_width=True, hide_index=True)

        cancelled = [l for l in logs if l["status"] == "CANCELLED"]
        if cancelled:
            st.caption(f"({len(cancelled)} sinyal batal — tidak pernah pullback ke level entry)")

        cdl, crst = st.columns([3, 1])
        with cdl:
            st.download_button("⬇️ Download CSV", pd.DataFrame(logs).to_csv(index=False).encode("utf-8"),
                                "idx_trade_log.csv", "text/csv")
        with crst:
            if st.button("🗑️ Reset Data"):
                save_log([])
                st.rerun()
