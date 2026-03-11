import yfinance as yf
import pandas as pd
import requests
import os

# =========================
# Telegram
# =========================
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram(msg):

    if not TOKEN or not CHAT_ID:
        print(msg)
        return

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": msg
        }
    )

# =========================
# EGX symbols (عينة)
# =========================
symbols = {
"OFH":"OFH.CA",
"ETEL":"ETEL.CA",
"EAST":"EAST.CA",
"OIH":"OIH.CA",
"SWDY":"SWDY.CA",
"RMDA":"RMDA.CA"
}

# =========================
# RSI
# =========================
def RSI(series, period=14):

    delta = series.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss

    rsi = 100 - (100 / (1 + rs))

    return rsi

signals = []

# =========================
# Scan
# =========================
for symbol,ticker in symbols.items():

    try:

        data = yf.download(
            ticker,
            period="6mo",
            interval="1d",
            progress=False
        )

        if data.empty:
            continue

        close = data["Close"]

        data["RSI"] = RSI(close)

        price = float(close.iloc[-1])
        rsi_now = float(data["RSI"].iloc[-1])

        signals.append(
            f"{symbol} | Price {price:.2f} | RSI {rsi_now:.1f}"
        )

    except Exception as e:

        signals.append(f"{symbol} ERROR")

# =========================
# Message
# =========================
message = "📊 EGX TEST SCAN\n\n"

if signals:

    message += "\n".join(signals)

else:

    message += "No data"

send_telegram(message)
