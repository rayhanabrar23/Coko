import json
import os
from datetime import datetime
import pytz
import pandas as pd
import requests

from logic_scanner import (
    UNIVERSES,
    HOLD_DAYS_MAX_DEFAULT,
    MAX_SL_PCT_DEFAULT,
    MIN_AVG_DOLLAR_VALUE_DEFAULT,
    MIN_SCORE_DEFAULT,
    jk,
    sf,
    fetch_batch,
    score_ticker,
    get_levels,
    evaluate_trade,
)

TZ_JKT = pytz.timezone("Asia/Jakarta")
LOG_FILE = "idx_trade_log.json"


def load_log():
  if os.path.exists(LOG_FILE):
    with open(LOG_FILE, "r") as f:
      return json.load(f)
  return []


def save_log(logs):
  with open(LOG_FILE, "w") as f:
    json.dump(logs, f, indent=2, default=str)


def send_discord(message):
  webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
  if not webhook_url:
    print("DISCORD_WEBHOOK_URL tidak ditemukan di environment variables.")
    return
  payload = {"content": message}
  response = requests.post(webhook_url, json=payload)
  if response.status_code != 204:
    print(f"Gagal mengirim ke Discord: {response.status_code}, {response.text}")


def main():
  today = datetime.now(TZ_JKT).strftime("%Y-%m-%d")
  print(f"Menjalankan automated scan & P/L check untuk tanggal: {today}")

  # 1. Update status trade yang masih PENDING atau OPEN
  logs = load_log()
  updated_count = 0
  for t in logs:
    if t["status"] not in ("PENDING", "OPEN"):
      continue
    result = evaluate_trade(
        t, fee_pct=0.30, hold_days_max=HOLD_DAYS_MAX_DEFAULT
    )  #[cite: 2]
    t.update({
        "status": result["status"],
        "note": result.get("note", ""),
        "current_or_exit_price": result.get(
            "exit_price", result.get("current_price")
        ),
        "pnl_pct": result.get("pnl_pct", 0),
        "fill_date": result.get("fill_date", t.get("fill_date")),
        "exit_date": result.get("exit_date", t.get("exit_date")),
    })
    updated_count += 1

  # 2. Jalankan scan baru menggunakan universe gabungan
  universe = UNIVERSES["Gabungan (IDX30 + LQ45)"]
  tickers = tuple(jk(t) for t in universe)
  data = fetch_batch(tickers, "2y")

  results = []
  for t, df in data.items():
    name = t.replace(".JK", "")
    median_dv = df["dollar_value_ma20"].median()
    if pd.isna(median_dv) or median_dv < MIN_AVG_DOLLAR_VALUE_DEFAULT:  #[cite: 2]
      continue
    score, detail, regime = score_ticker(df)
    if score < MIN_SCORE_DEFAULT:  #[cite: 2]
      continue
    entry, sl, tp, rr, signal, cls = get_levels(
        df, score, regime, max_sl_pct=MAX_SL_PCT_DEFAULT
    )  #[cite: 2]
    if "AVOID" in signal:
      continue
    results.append({
        "Ticker": name,
        "Score": score,
        "Signal": signal,
        "Regime": regime.title(),
        "Entry": entry,
        "SL": sl,
        "TP": tp,
        "R:R": rr,
        "RSI": detail["RSI"],
        "Vol": round(sf(df["vol_ratio"].iloc[-1]), 2),
    })

  # 3. Simpan sinyal baru ke idx_trade_log.json[cite: 1]
  existing_keys = {(e["signal_date"], e["ticker"]) for e in logs}
  new_signals_msg = []
  for row in results:
    key = (today, row["Ticker"])
    if key in existing_keys:
      continue
    logs.append({
        "id": f"{today}_{row['Ticker']}",
        "ticker": row["Ticker"],
        "signal_date": today,
        "signal": row["Signal"],
        "score": int(row["Score"]),
        "regime": row["Regime"],
        "entry": float(row["Entry"]),
        "sl": float(row["SL"]),
        "tp": float(row["TP"]),
        "status": "PENDING",
    })
    new_signals_msg.append(
        f"- **{row['Ticker']}** | {row['Signal']} (Skor: {row['Score']}) |"
        f" Entry: {row['Entry']:,}"
    )

  save_log(logs)

  # 4. Hitung Statistik Performa (Closed & Open Trades)
  closed = [l for l in logs if l["status"] in ("WIN", "LOSS", "BREAKEVEN")]
  open_trades = [l for l in logs if l["status"] == "OPEN"]

  pnl_summary = "📊 *Belum ada trade yang closed.*"
  if closed:
    wins = [l for l in closed if l["status"] == "WIN"]
    win_rate = round(len(wins) / len(closed) * 100, 1)
    avg_pnl = round(sum(l.get("pnl_pct", 0) for l in closed) / len(closed), 2)
    total_closed = len(closed)

    # Deteksi trade yang selesai hari ini
    closed_today = [l for l in closed if l.get("exit_date") == today]
    today_pnl_str = ""
    if closed_today:
      today_items = [
          f"• `{c['ticker']}`: **{c['pnl_pct']:+.2f}%** ({c['status'])"
          for c in closed_today
      ]
      today_pnl_str = (
          "\n🎯 **Selesai (*Closed*) Hari Ini:**\n"
          + "\n".join(today_items)
          + "\n"
      )

    pnl_summary = (
        f"📈 **Rekap Performa Keseluruhan:**\n"
        f"• Win Rate: **{win_rate}%** ({len(wins)} Win dari {total_closed} Trade"
        f" Closed)\n"
        f"• Rata-rata Net PnL: **{avg_pnl:+.2f}%**"
        f"{today_pnl_str}"
    )

  # 5. Susun format pesan laporan ke Discord
  msg = f"📊 **IDX Screener Daily Report ({today})**\n\n"

  if new_signals_msg:
    msg += (
        "🚨 **Sinyal Baru Ditemukan Hari Ini:**\n"
        + "\n".join(new_signals_msg)
        + "\n\n"
    )
  else:
    msg += "ℹ️ Tidak ada sinyal BUY baru hari ini.\n\n"

  msg += f"{pnl_summary}\n\n"

  if open_trades:
    open_items = [
        f"• `{t['ticker']}`: PnL sementara **{t.get('pnl_pct', 0):+.2f}%**"
        for t in open_trades
    ]
    msg += (
        f"🟢 **Posisi Aktif (*Open*):** {len(open_trades)} emiten\n"
        + "\n".join(open_items)
        + "\n\n"
    )

  msg += f"🔄 Status {updated_count} trade aktif/pending telah diperbarui."

  send_dispatch_msg = send_discord(msg)
  print("Proses otomatisasi selesai dan laporan P/L terkirim ke Discord.")


if __name__ == "__main__":
  main()
