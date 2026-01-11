print("EGX BOT - STAGE 2 TEST")

import os
import requests
import yfinance as yf

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram(msg):
    if not TOKEN or not CHAT_ID:
        raise Exception("Missing Telegram ENV")
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    r = requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": msg
    })
    print("Telegram response:", r.text)

# ===== Test yfinance =====
ticker = "COMI.CA"
data = yf.download(ticker, period="5d", interval="1d", progress=False)

if data.empty:
    send_telegram("❌ yfinance test failed: no data")
else:
    last_close = data["Close"].iloc[-1]
    send_telegram(f"✅ yfinance OK\n{ticker} Close: {last_close}")
