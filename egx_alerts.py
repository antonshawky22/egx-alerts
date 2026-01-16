print("EGX ALERTS - DAILY CLOSE STRATEGY (EMA + RSI + OBV)")

import yfinance as yf
import requests
import os
import json
import pandas as pd
import numpy as np

# =====================
# Telegram
# =====================
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram(msg):
    if not TOKEN or not CHAT_ID:
        print("Telegram ENV missing")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# =====================
# Symbols
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
# State
# =====================
SIGNALS_FILE = "last_signals.json"
last_signals = json.load(open(SIGNALS_FILE)) if os.path.exists(SIGNALS_FILE) else {}
new_signals = last_signals.copy()

alerts = []
failures = []

# =====================
# Fetch Data
# =====================
def fetch_data(ticker):
    try:
        df = yf.download(ticker, period="6mo", interval="1d", progress=False)
        if df is None or len(df) < 80:
            return None
        return df
    except:
        return None

# =====================
# Logic
# =====================
for name, ticker in symbols.items():
    df = fetch_data(ticker)
    if df is None:
        failures.append(name)
        continue

    close = df["Close"].astype(float)
    volume = df["Volume"].astype(float)

    # 🔥 Gap filter
    gap = abs(close.iloc[-1] - close.iloc[-2]) / close.iloc[-2] * 100
    if gap > 7:
        continue

    candle_date = close.index[-1].date()
    price = float(close.iloc[-1])

    # EMA
    ema13 = close.ewm(span=13).mean()
    ema21 = close.ewm(span=21).mean()

    # RSI
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    rs = gain.ewm(alpha=1/14).mean() / loss.ewm(alpha=1/14).mean()
    rsi = 100 - (100 / (1 + rs))

    # OBV
    obv = (np.sign(close.diff()) * volume).fillna(0).cumsum()
    obv_ema = obv.ewm(span=10).mean()

    buy = [
        40 <= rsi.iloc[-1] <= 55,
        ema13.iloc[-1] > ema21.iloc[-1],
        obv.iloc[-1] > obv_ema.iloc[-1]
    ]

    sell = [
        50 <= rsi.iloc[-1] <= 65,
        ema13.iloc[-1] < ema21.iloc[-1],
        obv.iloc[-1] < obv_ema.iloc[-1]
    ]

    if sum(buy) >= 2 and last_signals.get(name) != "BUY":
        alerts.append(
            f"🟢 شراء | {name}\n"
            f"📅 شمعة: {candle_date}\n"
            f"📊 سعر : {price:.2f}"
        )
        new_signals[name] = "BUY"

    elif sum(sell) >= 2 and last_signals.get(name) != "SELL":
        alerts.append(
            f"🔴 بيع | {name}\n"
            f"📅 شمعة: {candle_date}\n"
            f"📊 سعر : {price:.2f}"
        )
        new_signals[name] = "SELL"

# =====================
# Save
# =====================
with open(SIGNALS_FILE, "w") as f:
    json.dump(new_signals, f)

# =====================
# Telegram
# =====================
if alerts:
    send_telegram("🚨 إشارات اليوم:\n\n" + "\n\n".join(alerts))
else:
    send_telegram("ℹ️ لا توجد إشارات اليوم")

if failures:
    send_telegram("⚠️ فشل جلب البيانات:\n" + ", ".join(failures))
