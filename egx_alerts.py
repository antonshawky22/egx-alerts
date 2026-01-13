print("EGX ALERTS - BUY / SELL ONLY (EMA 9 + RSI MA)")

import yfinance as yf
import requests
import os
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
    # EMA 9 (أسرع لكن ثابت)
    # =====================
    ema9 = close.ewm(span=9, adjust=False).mean()

    # =====================
    # RSI Wilder + Moving Average
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
    # Last values
    # =====================
    price_last = float(close.iloc[-1])
    ema9_last = float(ema9.iloc[-1])

    rsi_prev = float(rsi.iloc[-2])
    rsi_last = float(rsi.iloc[-1])
    rsi_ma_prev = float(rsi_ma.iloc[-2])
    rsi_ma_last = float(rsi_ma.iloc[-1])

    # =====================
    # 🟢 BUY NOW
    # =====================
    if (
        price_last > ema9_last
        and rsi_last <= 40
        and rsi_prev < rsi_ma_prev
        and rsi_last > rsi_ma_last
    ):
        alerts.append(f"🟢 BUY NOW: {name} | RSI={round(rsi_last,1)}")

    # =====================
    # 🔴 SELL NOW
    # =====================
    elif (
        price_last < ema9_last
        or rsi_last >= 65
        or (rsi_prev > rsi_ma_prev and rsi_last < rsi_ma_last)
    ):
        alerts.append(f"🔴 SELL NOW: {name} | RSI={round(rsi_last,1)}")

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
