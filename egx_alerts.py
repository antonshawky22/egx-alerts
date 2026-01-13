print("EGX ALERTS - BUY / SELL ONLY (EMA9 + RSI MA | 2 of 3)")

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
        print("Telegram ENV missing")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": text})

# =====================
# EGX symbols
# =====================
symbols = {
    "OFH": "OFH.CA","EMFD": "EMFD.CA","ETEL": "ETEL.CA","EAST": "EAST.CA",
    "OIH": "OIH.CA","ORWE": "ORWE.CA","JUFO": "JUFO.CA",
    "SUGR": "SUGR.CA","ELSH": "ELSH.CA","RMDA": "RMDA.CA","FWRY": "FWRY.CA"
}

alerts = []
data_failures = []

# =====================
# Load last signals (prevent duplicates)
# =====================
SIGNALS_FILE = "last_signals.json"

if os.path.exists(SIGNALS_FILE):
    with open(SIGNALS_FILE, "r") as f:
        last_signals = json.load(f)
else:
    last_signals = {}

new_signals = last_signals.copy()

# =====================
# PRICE FETCH
# =====================
def fetch_yfinance(ticker):
    try:
        df = yf.download(ticker, period="6mo", interval="1d", progress=False)
        if df is None or df.empty or "Close" not in df:
            return None
        return df
    except Exception:
        return None

# =====================
# Logic
# =====================
for name, ticker in symbols.items():
    data = fetch_yfinance(ticker)

    if data is None or len(data) < 50:
        data_failures.append(name)
        continue

    close = data["Close"].astype(float)

    # =====================
    # EMA 9
    # =====================
    ema9 = close.ewm(span=9, adjust=False).mean()
    ema9_smooth = ema9.ewm(span=3, adjust=False).mean()

    # =====================
    # RSI Wilder
    # =====================
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    rsi_ma = rsi.ewm(span=5, adjust=False).mean()

    # =====================
    # LAST VALUES
    # =====================
    price_last = float(close.iloc[-1])
    ema9_last = float(ema9_smooth.iloc[-1])

    rsi_last = float(rsi.iloc[-1])
    rsi_prev = float(rsi.iloc[-2])
    rsi_ma_last = float(rsi_ma.iloc[-1])
    rsi_ma_prev = float(rsi_ma.iloc[-2])

    # =====================
    # CONDITIONS (2 of 3)
    # =====================
    buy_conditions = [
        38 <= rsi_last <= 45,
        rsi_prev < rsi_ma_prev and rsi_last > rsi_ma_last,
        price_last > ema9_last
    ]

    sell_conditions = [
        60 <= rsi_last <= 68,
        rsi_prev > rsi_ma_prev and rsi_last < rsi_ma_last,
        price_last < ema9_last
    ]

    # =====================
    # SIGNAL DECISION
    # =====================
    if sum(buy_conditions) >= 2:
        if last_signals.get(name) != "BUY":
            alerts.append(f"🟢 شراء    {price_last:.2f}    {name}")
            new_signals[name] = "BUY"

    elif sum(sell_conditions) >= 2:
        if last_signals.get(name) != "SELL":
            alerts.append(f"🔴 بيع     {name}    {price_last:.2f}")
            new_signals[name] = "SELL"

# =====================
# Save signals
# =====================
with open(SIGNALS_FILE, "w") as f:
    json.dump(new_signals, f)

# =====================
# Send alerts
# =====================
if alerts:
    send_telegram("🚨 إشارات تنفيذ فوري:\n\n" + "\n".join(alerts))
else:
    send_telegram("ℹ️ لا توجد إشارات اليوم")

if data_failures:
    send_telegram(
        "⚠️ فشل جلب البيانات:\n" +
        ", ".join(data_failures)
    )
