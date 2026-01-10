print("EGX EMA ALERTS - CLEAN START")

import yfinance as yf
import requests
import os

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
    requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": text
    })

# =====================
# EGX symbols (20)
# =====================
symbols = {
    "COMI": "COMI.CA",
    "ETEL": "ETEL.CA",
    "EFG": "EFGH.CA",
    "CIB": "CIB.CA",
    "HRHO": "HRHO.CA",
    "TMGH": "TMGH.CA",
    "EAST": "EAST.CA",
    "PHDC": "PHDC.CA",
    "SWDY": "SWDY.CA",
    "ORAS": "ORAS.CA",
    "ABUK": "ABUK.CA",
    "AMOC": "AMOC.CA",
    "CCAP": "CCAP.CA",
    "SKPC": "SKPC.CA",
    "JUFO": "JUFO.CA",
    "ISPH": "ISPH.CA",
    "MFPC": "MFPC.CA",
    "POUL": "POUL.CA",
    "RAYA": "RAYA.CA",
    "ZEOT": "ZEOT.CA"
}

alerts = []

# =====================
# EMA calculation
# =====================
for name, ticker in symbols.items():
    data = yf.download(ticker, period="4mo", interval="1d", progress=False)

    if data.empty or len(data) < 60:
        continue

    close = data["Close"]

    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()

    if ema20.iloc[-2] < ema50.iloc[-2] and ema20.iloc[-1] > ema50.iloc[-1]:
        alerts.append(f"📈 شراء: {name}")
    elif ema20.iloc[-2] > ema50.iloc[-2] and ema20.iloc[-1] < ema50.iloc[-1]:
        alerts.append(f"📉 بيع: {name}")

# =====================
# Send result
# =====================
if alerts:
    send_telegram("🚨 تنبيهات EGX:\n\n" + "\n".join(alerts))
else:
    send_telegram("ℹ️ لا توجد إشارات اليوم")
