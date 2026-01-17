print("EGX ALERTS - Moving Average Converging (LUX STYLE | SAFE TREND MODE)")

import yfinance as yf
import requests
import os
import json
import numpy as np
from datetime import datetime

# =====================
# Telegram settings
# =====================
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram(text):
    if not TOKEN or not CHAT_ID:
        print("Telegram ENV missing")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": text})

# =====================
# EGX symbols
# =====================
symbols = {
    "OFH": "OFH.CA","OLFI": "OLFI.CA","EMFD": "EMFD.CA","ETEL": "ETEL.CA",
    "EAST": "EAST.CA","EFIH": "EFIH.CA","ABUK": "ABUK.CA","OIH": "OIH.CA",
    "SWDY": "SWDY.CA","ISPH": "ISPH.CA","ATQA": "ATQA.CA","MTIE": "MTIE.CA",
    "ELEC": "ELEC.CA","HRHO": "HRHO.CA","ORWE": "ORWE.CA","JUFO": "JUFO.CA",
    "DSCW": "DSCW.CA","SUGR": "SUGR.CA","ELSH": "ELSH.CA","RMDA": "RMDA.CA",
    "RAYA": "RAYA.CA","EEII": "EEII.CA","MPCO": "MPCO.CA","GBCO": "GBCO.CA",
    "TMGH": "TMGH.CA","ORAS": "ORAS.CA","AMOC": "AMOC.CA","FWRY": "FWRY.CA"
}

# =====================
# Load last signals
# =====================
SIGNALS_FILE = "last_signals.json"

if os.path.exists(SIGNALS_FILE):
    with open(SIGNALS_FILE, "r") as f:
        last_signals = json.load(f)
else:
    last_signals = {}

new_signals = last_signals.copy()
alerts = []
data_failures = []

# =====================
# Fetch data
# =====================
def fetch_data(ticker):
    try:
        df = yf.download(ticker, period="6mo", interval="1d", progress=False)
        if df is None or df.empty:
            return None
        return df
    except Exception:
        return None

# =====================
# Main Logic
# =====================
EMA_PERIODS = [12, 24, 36, 48, 60, 72]

for name, ticker in symbols.items():
    data = fetch_data(ticker)

    if data is None or len(data) < 100:
        data_failures.append(name)
        continue

    close = data["Close"].astype(float)
    price = float(close.iloc[-1])
    candle_date = close.index[-1].date()

    # ---- Calculate EMAs
    emas = {p: close.ewm(span=p, adjust=False).mean() for p in EMA_PERIODS}
    ema_last = {p: float(emas[p].iloc[-1]) for p in EMA_PERIODS}

    ema_values = list(ema_last.values())
    ema_mean = np.mean(ema_values)

    # ---- Counts
    below_price = sum(price > v for v in ema_values)
    above_price = sum(price < v for v in ema_values)

    # ---- Trend
    fast_above_slow = ema_last[12] > ema_last[72]
    fast_below_slow = ema_last[12] < ema_last[72]

    # =====================
    # BUY / SELL Logic
    # =====================
    if (
        price > ema_mean and
        fast_above_slow and
        below_price >= 4 and
        last_signals.get(name) != "BUY"
    ):
        alerts.append(
            f"🟢 BUY | {name}\n"
            f"Price: {price:.2f}\n"
            f"Date: {candle_date}"
        )
        new_signals[name] = "BUY"

    elif (
        price < ema_mean and
        fast_below_slow and
        above_price >= 4 and
        last_signals.get(name) != "SELL"
    ):
        alerts.append(
            f"🔴 SELL | {name}\n"
            f"Price: {price:.2f}\n"
            f"Date: {candle_date}"
        )
        new_signals[name] = "SELL"

# =====================
# Save signals
# =====================
with open(SIGNALS_FILE, "w") as f:
    json.dump(new_signals, f)

# =====================
# Telegram messages
# =====================
if alerts:
    send_telegram("🚨 EGX Signals (MAC Converging SAFE):\n\n" + "\n\n".join(alerts))
else:
    send_telegram("ℹ️ لا توجد إشارات اليوم – البوت يعمل")

send_telegram(
    f"✅ البوت يعمل\n"
    f"📅 {datetime.utcnow().date()}\n"
    f"📊 إشارات: {len(alerts)}\n"
    f"⚠️ أخطاء بيانات: {len(data_failures)}"
    )
