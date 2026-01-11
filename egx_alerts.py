import os
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime

# =============================
# Telegram settings (ثابتة)
# =============================
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }
    r = requests.post(url, json=payload)
    return r.text

# =============================
# EGX symbols (30 سهم)
# =============================
SYMBOLS = [
    "COMI.CA", "ETEL.CA", "EFIH.CA", "SWDY.CA", "ORAS.CA",
    "TALA.CA", "PHDC.CA", "HRHO.CA", "EAST.CA", "ESRS.CA",
    "AMOC.CA", "ARCC.CA", "CIB.CA", "POUL.CA", "MCSR.CA",
    "CCAP.CA", "ISPH.CA", "MFPC.CA", "TMGH.CA", "SKPC.CA",
    "DCRC.CA", "FWRY.CA", "BTFH.CA", "ACGC.CA", "SUGR.CA",
    "HELI.CA", "RAYA.CA", "AUTO.CA", "NCCW.CA", "KABO.CA"
]

# =============================
# Indicator functions
# =============================
def calculate_ema(series, period):
    return round(series.ewm(span=period, adjust=False).mean().iloc[-1], 2)

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return round(rsi.iloc[-1], 2)

# =============================
# Main logic
# =============================
alerts = []

for symbol in SYMBOLS:
    try:
        df = yf.download(
            symbol,
            period="3mo",
            interval="1d",
            progress=False
        )

        if df.empty or "Close" not in df:
            continue

        close = df["Close"]

        ema20 = calculate_ema(close, 20)
        ema50 = calculate_ema(close, 50)
        rsi14 = calculate_rsi(close, 14)
        price = round(close.iloc[-1], 2)

        # =============================
        # Alert condition
        # =============================
        if price > ema20 and ema20 > ema50 and rsi14 < 30:
            alerts.append(
                f"📈 فرصة محتملة\n"
                f"السهم: {symbol}\n"
                f"السعر: {price}\n"
                f"EMA20: {ema20}\n"
                f"EMA50: {ema50}\n"
                f"RSI: {rsi14}\n"
                f"-------------------"
            )

    except Exception as e:
        print(f"Error in {symbol}: {e}")

# =============================
# Send result
# =============================
if alerts:
    message = "🔔 تنبيهات EGX\n\n" + "\n".join(alerts)
else:
    message = "✅ لا توجد فرص مطابقة اليوم"

send_telegram(message)
