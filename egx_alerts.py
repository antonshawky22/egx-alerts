print("EGX ALERTS - BUY / SELL ONLY (EMA FAST + OBV + RSI | 2 of 3 + TREND FILTER)")

import yfinance as yf
import requests
import os
import json
import pandas as pd
import numpy as np

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
# Fetch data
# =====================
def fetch_yfinance(ticker):
    try:
        df = yf.download(ticker, period="6mo", interval="1d", progress=False)
        if df is None or df.empty:
            return None
        return df
    except Exception:
        return None

# =====================
# Logic
# =====================
for name, ticker in symbols.items():
    data = fetch_yfinance(ticker)

    if data is None or len(data) < 70:
        data_failures.append(name)
        continue

    close = data["Close"].astype(float)
    volume = data["Volume"].astype(float)

    candle_date = close.index[-1].date()

    # =====================
    # Indicators
    # =====================
    ema13 = close.ewm(span=13, adjust=False).mean()
    ema21 = close.ewm(span=21, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()

    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    obv = (np.sign(close.diff()) * volume).fillna(0).cumsum()
    obv_ema = obv.ewm(span=10, adjust=False).mean()

    # =====================
    # Last values
    # =====================
    price = float(close.iloc[-1])
    rsi_last = float(rsi.dropna().iloc[-1])

    # =====================
    # CONDITIONS
    # =====================
    buy_conditions = [
        40 <= rsi_last <= 55,
        ema13.iloc[-1] > ema21.iloc[-1],
        obv.iloc[-1] > obv_ema.iloc[-1],
        price > ema50.iloc[-1]          # فلترة الاتجاه
    ]

    sell_conditions = [
        50 <= rsi_last <= 65,
        ema13.iloc[-1] < ema21.iloc[-1],
        obv.iloc[-1] < obv_ema.iloc[-1],
        price < ema50.iloc[-1]          # فلترة الاتجاه
    ]

    if sum(buy_conditions) >= 3:
        if last_signals.get(name) != "BUY":
            alerts.append(
                f"🟢 شراء | {name}\n"
                f"📊 السعر: {price:.2f}\n"
                f"📅 تاريخ الشمعة: {candle_date}"
            )
            new_signals[name] = "BUY"

    elif sum(sell_conditions) >= 3:
        if last_signals.get(name) != "SELL":
            alerts.append(
                f"🔴 بيع | {name}\n"
                f"📊 السعر: {price:.2f}\n"
                f"📅 تاريخ الشمعة: {candle_date}"
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
