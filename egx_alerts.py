import os
import requests
import yfinance as yf
import pandas as pd

# =========================
# EGX 30 Tickers
# =========================
EGX_TICKERS = [
    "COMI.CA", "CIB.CA", "ETEL.CA", "EFG.CA", "EAST.CA",
    "SWDY.CA", "TALM.CA", "AMOC.CA", "ESRS.CA", "ORWE.CA",
    "PHDC.CA", "MNHD.CA", "HELI.CA", "SKPC.CA", "JUFO.CA",
    "ISPH.CA", "BTFH.CA", "SAUD.CA", "ARAB.CA", "CCRS.CA",
    "OLFI.CA", "AUTO.CA", "FWRY.CA", "ADIB.CA", "ABUK.CA",
    "ORAS.CA", "CLHO.CA", "HRHO.CA", "KABO.CA", "DSCW.CA"
]

# =========================
# Telegram Config
# =========================
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TOKEN or not CHAT_ID:
    raise Exception("Missing Telegram credentials")

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

# =========================
# Message Header
# =========================
message = "📊 EGX Watchlist (30 Stocks)\n\n"

# =========================
# Data Processing
# =========================
for ticker in EGX_TICKERS:
    try:
        data = yf.Ticker(ticker).history(period="60d")

        if data.empty or len(data) < 20:
            message += f"{ticker.replace('.CA','')}: N/A\n"
            continue

        close = data["Close"]

        close_price = round(close.iloc[-1], 2)

        ema20 = round(close.ewm(span=20).mean().iloc[-1], 2)
        ema50 = round(close.ewm(span=50).mean().iloc[-1], 2)

        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()

        rs = avg_gain / avg_loss
        rsi = round(100 - (100 / (1 + rs.iloc[-1])), 2)

        # Simple Alert Logic
        signal = ""
        if close_price > ema20 > ema50 and rsi < 70:
            signal = " 🟢"
        elif close_price < ema20 < ema50 and rsi > 30:
            signal = " 🔴"

        message += (
            f"{ticker.replace('.CA','')}: {close_price} | "
            f"EMA20:{ema20} EMA50:{ema50} RSI:{rsi}{signal}\n"
        )

    except Exception:
        message += f"{ticker.replace('.CA','')}: ERROR\n"

# =========================
# Send Telegram Message
# =========================
payload = {
    "chat_id": CHAT_ID,
    "text": message
}

r = requests.post(url, json=payload)
print(r.text)
