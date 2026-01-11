print("EGX ALERTS - STABLE ENTRY + FAST EXIT + PLAN B")

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
    requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": text
    })

# =====================
# EGX symbols (مختارة بعناية)
# =====================
symbols = {
    "COMI": "COMI.CA",
    "EFG": "EFGH.CA",
    "ETEL": "ETEL.CA",
    "SWDY": "SWDY.CA",
    "HRHO": "HRHO.CA",
    "EAST": "EAST.CA",
    "ABUK": "ABUK.CA",
    "ISPH": "ISPH.CA",
    "JUFO": "JUFO.CA",
    "RAYA": "RAYA.CA",
    "ORWE": "ORWE.CA",

    # إضافات (٥ فقط)
    "EFIH": "EFIH.CA",
    "EMFD": "EMFD.CA",
    "OLFI": "OLFI.CA",
    "MTIE": "MTIE.CA",
    "ELEC": "ELEC.CA",
}

alerts = []
data_failures = []

# =====================
# PRICE FETCH (Plan A)
# =====================
def get_price_data(ticker):
    try:
        data = yf.download(ticker, period="6mo", interval="1d", progress=False)
        if data.empty or "Close" not in data:
            raise ValueError("Empty data from yfinance")
        return data
    except Exception:
        return None

# =====================
# Logic
# =====================
for name, ticker in symbols.items():
    data = get_price_data(ticker)

    if data is None or len(data) < 60:
        data_failures.append(name)
        continue

    close = data["Close"].squeeze()

    # EMA دخول
    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()

    # EMA خروج
    ema10 = close.ewm(span=10,
