import os
import requests
import yfinance as yf
import pandas as pd

# =========================
# EGX Tickers (30 Stocks)
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
# Telegram Credentials
# =========================
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TOKEN or not CHAT_ID:
    raise Exception("Missing Telegram credentials")

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

# =========================
# Message Header
# =========================
message = "📊 EGX Alerts (30 Stocks)\n\n"

# =========================
# Main Loop
# =========================
for ticker in EGX_TICKERS:
    try:
        data = yf.Ticker(ticker).history(period="60d")

        if data.empty:
            message += f"{ticker.replace('.CA','')}: N/A\n"
            continue

        close = data["Close"]

        # ===== EMA =====
        ema20 = close.ewm(span=20).mean().iloc[-1]
        ema50 = close.ewm(span=50).mean().iloc[-1]

        # ===== RSI =====
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs.iloc[-1]))

        close_price = close.iloc[-1]

        # ===== Conditions =====
        alert = ""
        if close_price > ema20 > ema50 and rsi < 70:
            alert = " 🟢 BUY"
        elif close_price < ema20 < ema50 and rsi > 30:
            alert = " 🔴 SELL"

        # ===== Message Line =====
        message += (
            f"{ticker.replace('.CA','')}: {round(close_price,2)} | "
            f"EMA20:{round(ema20,2)} EMA50:{round(ema50,2)} "
            f"RSI:{round(rsi,2)}{alert}\n"
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

response = requests.post(url, json=payload)
print(response.text)
