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
  # Discord menggunakan format json dengan key 'content'
  payload = {"content": message}
  response = requests.post(webhook_url, json=payload)
  if response.status_code != 204:
    print(f"Gagal mengirim ke Discord: {response.status_code}, {response.text}")


def main():
  today = datetime.now(TZ_JKT).strftime("%Y-%m-%d")
  print(f"Menjalankan automated scan untuk tanggal: {today}")

  # 1. Update status trade yang masih PENDING atau OPEN
  logs = load_log()
  updated_count = 0
  for t in logs:
    if t["status"] not in ("PENDING", "OPEN"):
      continue
    result = evaluate_trade(
        t, fee_pct=0.30, hold_days_max=HOLD_DAYS_MAX_DEFAULT
    )  #
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

  # 4. Susun pesan dan kirim ke Discord
  msg = f"📊 **IDX Screener Daily Report ({today})**\n"
  if new_signals_msg:
    msg += (
        "🚨 **Sinyal Baru Ditemukan:**\n"
        + "\n".join(new_signals_msg)
        + "\n\n"
    )
  else:
    msg += "ℹ️ Tidak ada sinyal BUY baru hari ini.\n\n"

  msg += f"🔄 Status {updated_count} trade aktif/pending telah diperbarui."
  send_discord(msg)
  print("Proses otomatisasi selesai dan laporan terkirim ke Discord.")


if __name__ == "__main__":
  main()
