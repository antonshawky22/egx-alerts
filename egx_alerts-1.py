print("EGX ALERTS - Breakout Engine (Daily Confirmed)")

import yfinance as yf
import requests
import os
import json
import pandas as pd

# =====================
# Telegram settings
# =====================

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram(text):
    if not TOKEN or not CHAT_ID:
        print("Telegram credentials not set")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": text}, timeout=10)
    except Exception as e:
        print("Telegram send failed:", e)

# =====================
# EGX symbols
# =====================

symbols = {
"OFH":"OFH.CA","OLFI":"OLFI.CA","EMFD":"EMFD.CA","ETEL":"ETEL.CA",
"EAST":"EAST.CA","EFIH":"EFIH.CA","ABUK":"ABUK.CA","OIH":"OIH.CA",
"SWDY":"SWDY.CA","ISPH":"ISPH.CA","ATQA":"ATQA.CA","MTIE":"MTIE.CA",
"ELEC":"ELEC.CA","HRHO":"HRHO.CA","ORWE":"ORWE.CA","JUFO":"JUFO.CA",
"DSCW":"DSCW.CA","SUGR":"SUGR.CA","ELSH":"ELSH.CA","RMDA":"RMDA.CA",
"RAYA":"RAYA.CA","EEII":"EEII.CA","MPCO":"MPCO.CA","GBCO":"GBCO.CA",
"TMGH":"TMGH.CA","ORHD":"ORHD.CA","AMOC":"AMOC.CA","FWRY":"FWRY.CA",
"COMI":"COMI.CA","ADIB":"ADIB.CA","PHDC":"PHDC.CA",
"MCQE":"MCQE.CA","SKPC":"SKPC.CA","EGAL":"EGAL.CA"
}

# =====================
# Load last signals
# =====================

SIGNALS_FILE = "last_signals.json"

try:
    with open(SIGNALS_FILE, "r") as f:
        last_signals = json.load(f)
except:
    last_signals = {}

new_signals = {}
data_failures = []
latest_market_date = None

# =====================
# Trading Logic
# =====================

def trading_signal(df):
    if len(df) < 30:
        return None

    close = df['Close']
    high = df['High']
    low = df['Low']
    volume = df['Volume']

    current_price = close.iloc[-1]

    highest_20 = high.rolling(20).max().iloc[-1]
    lowest_20 = low.rolling(20).min().iloc[-1]
    lowest_15 = low.rolling(15).min().iloc[-1]

    range_20 = (highest_20 - lowest_20) / lowest_20
    cond_range = range_20 < 0.10

    cond_break = current_price >= 0.97 * highest_20

    vol_5 = volume.rolling(5).mean().iloc[-1]
    vol_20 = volume.rolling(20).mean().iloc[-1]
    cond_volume = vol_5 > 1.2 * vol_20

    if cond_range and cond_break and cond_volume:
        return "BUY"

    if current_price < lowest_15:
        return "SELL"

    if current_price < lowest_20:
        return "STOP LOSS"

    return None

# =====================
# Main Scan
# =====================

message_lines = []

for name, symbol in symbols.items():
    try:
        df = yf.download(symbol, period="6mo", interval="1d", progress=False)

        if df.empty:
            data_failures.append(name)
            continue

        last_date = df.index[-1].strftime("%Y-%m-%d")
        latest_market_date = last_date

        signal = trading_signal(df)

        if signal and last_signals.get(name) != signal:

            last_price = round(df['Close'].iloc[-1], 2)
            emoji = "🟢" if signal == "BUY" else "🔴" if signal == "SELL" else "🟡"

            message_lines.append(
                f"{emoji} {signal} | {name} {last_price} | {last_date}"
            )

            new_signals[name] = signal

    except:
        data_failures.append(name)

# =====================
# Send Signals
# =====================

if message_lines:
    final_message = "📊 EGX Daily Signals\n\n" + "\n".join(message_lines)
    send_telegram(final_message)

    last_signals.update(new_signals)
    with open(SIGNALS_FILE, "w") as f:
        json.dump(last_signals, f)

else:
    if latest_market_date:
        send_telegram(f"لا توجد إشارات جديدة | {latest_market_date} ✅")
    else:
        send_telegram("لا توجد إشارات جديدة")

# =====================
# Data Failures
# =====================

if data_failures:
    send_telegram("⚠️ فشل تحميل البيانات: " + ", ".join(data_failures))
