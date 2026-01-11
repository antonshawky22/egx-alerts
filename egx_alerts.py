print("EGX ALERTS - STABLE BASE + EMA + RSI")

import yfinance as yf
import requests
import os

# =====================
# Telegram settings (DO NOT TOUCH)
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
# EGX symbols (30 stocks)
# =====================
symbols = {
    "COMI": "COMI.CA",
    "CIB": "CIB.CA",
    "EFG": "EFGH.CA",
    "ETEL": "ETEL.CA",
    "TMGH": "TMGH.CA",
    "ORAS": "ORAS.CA",
    "SWDY": "SWDY.CA",
    "HRHO": "HRHO.CA",
    "PHDC": "PHDC.CA",
    "EAST": "EAST.CA",
    "ABUK": "ABUK.CA",
    "AMOC": "AMOC.CA",
    "CCAP": "CCAP.CA",
    "SKPC": "SKPC.CA",
    "JUFO": "JUFO.CA",
    "ISPH": "ISPH.CA",
    "MFPC": "MFPC.CA",
    "POUL": "POUL.CA",
    "RAYA": "RAYA.CA",
    "ZEOT": "ZEOT.CA",
    "BTFH": "BTFH.CA",
    "ESRS": "ESRS.CA",
    "MNHD": "MNHD.CA",
    "AUTO": "AUTO.CA",
    "EGTS": "EGTS.CA",
    "HELI": "HELI.CA",
    "MPRC": "MPRC.CA",
    "CNFN": "CNFN.CA",
    "DTPP": "DTPP.CA"
}

alerts = []

# =====================
# Indicators logic (SAFE)
# =====================
for name, ticker in symbols.items():
    data = yf.download(ticker, period="6mo", interval="1d", progress=False)

    if data.empty or len(data) < 60:
        continue

    close = data["Close"]

    # EMA
    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()

    # RSI
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    # Last values
    ema20_prev = ema20.iloc[-2]
    ema50_prev = ema50.iloc[-2]
    ema20_last = ema20.iloc[-1]
    ema50_last = ema50.iloc[-1]
    rsi_last = rsi.iloc[-1]

    # Conditions
    if ema20_prev < ema50_prev and ema20_last > ema50_last and rsi_last > 50:
        alerts.append(f"📈 شراء: {name} | RSI={round(rsi_last,1)}")

    elif ema20_prev > ema50_prev and ema20_last < ema50_last and rsi_last < 50:
        alerts.append(f"📉 بيع: {name} | RSI={round(rsi_last,1)}")

# =====================
# Send result
# =====================
if alerts:
    send_telegram("🚨 تنبيهات EGX:\n\n" + "\n".join(alerts))
else:
    send_telegram("ℹ️ لا توجد إشارات اليوم")
