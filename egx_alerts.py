print("EGX ALERTS - BUY / SELL ONLY (EMA FAST + OBV + RSI | 2 of 3)")

import yfinance as yf
import requests
import os
import json
import pandas as pd
import numpy as np
from datetime import datetime
import pytz

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

alerts = []
data_failures = []

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

# =====================
# Fetch data (SAFE DAILY CLOSE)
# =====================
def fetch_yfinance_safe(ticker):
    try:
        df = yf.download(ticker, period="6mo", interval="1d", progress=False)
        if df is None or df.empty:
            return None

        # توحيد التوقيت على القاهرة
        cairo = pytz.timezone("Africa/Cairo")
        now = datetime.now(cairo).date()

        # حذف شمعة اليوم (لو ظهرت)
        df = df[df.index.date < now]

        if len(df) < 70:
            return None

        return df

    except Exception:
        return None

# =====================
# Logic
# =====================
for name, ticker in symbols.items():
    data = fetch_yfinance_safe(ticker)

    if data is None:
        data_failures.append(name)
        continue

    close = data["Close"].astype(float)
    volume = data["Volume"].astype(float)

    candle_date = close.index[-1].date()  # آخر شمعة مؤكدة فقط

    # EMA
    ema13 = close.ewm(span=13, adjust=False).mean()
    ema21 = close.ewm(span=21, adjust=False).mean()

    # RSI
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    # OBV
    obv = (np.sign(close.diff()) * volume).fillna(0).cumsum()
    obv_ema = obv.ewm(span=10, adjust=False).mean()

    price = float(close.iloc[-1])

    buy_conditions = [
        40 <= rsi.iloc[-1] <= 55,
        ema13.iloc[-1] > ema21.iloc[-1],
        obv.iloc[-1] > obv_ema.iloc[-1]
    ]

    sell_conditions = [
        50 <= rsi.iloc[-1] <= 65,
        ema13.iloc[-1] < ema21.iloc[-1],
        obv.iloc[-1] < obv_ema.iloc[-1]
    ]

    if sum(buy_conditions) >= 2 and last_signals.get(name) != "BUY":
        alerts.append(
            f"🟢 شراء | {name}\n"
            f"📅 شمعة: {candle_date}\n"
            f"📊 سعر  :  {price:.2f}"
        )
        new_signals[name] = "BUY"

    elif sum(sell_conditions) >= 2 and last_signals.get(name) != "SELL":
        alerts.append(
            f"🔴 بيع | {name}\n"
            f"📅 شمعة: {candle_date}\n"
            f"📊 سعر  :  {price:.2f}"
        )
        new_signals[name] = "SELL"

# =====================
# Save & Send
# =====================
with open(SIGNALS_FILE, "w") as f:
    json.dump(new_signals, f)

if alerts:
    send_telegram("🚨 إشارات يومية:\n\n" + "\n\n".join(alerts))
else:
    send_telegram("ℹ️ لا توجد إشارات اليوم")

if data_failures:
    send_telegram("⚠️ فشل جلب البيانات:\n" + ", ".join(data_failures))
