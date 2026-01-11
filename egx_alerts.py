print("EGX ALERTS - STABLE ENTRY + FAST EXIT")

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
# EGX symbols
# =====================
symbols = {
    "COMI": "COMI.CA","CIB": "CIB.CA","EFG": "EFGH.CA","ETEL": "ETEL.CA",
    "TMGH": "TMGH.CA","ORAS": "ORAS.CA","SWDY": "SWDY.CA","HRHO": "HRHO.CA",
    "PHDC": "PHDC.CA","EAST": "EAST.CA","ABUK": "ABUK.CA","AMOC": "AMOC.CA",
    "CCAP": "CCAP.CA","SKPC": "SKPC.CA","JUFO": "JUFO.CA","ISPH": "ISPH.CA",
    "MFPC": "MFPC.CA","POUL": "POUL.CA","RAYA": "RAYA.CA","ZEOT": "ZEOT.CA",
    "BTFH": "BTFH.CA","ESRS": "ESRS.CA","MNHD": "MNHD.CA","AUTO": "AUTO.CA",
    "EGTS": "EGTS.CA","HELI": "HELI.CA","MPRC": "MPRC.CA","CNFN": "CNFN.CA",
    "DTPP": "DTPP.CA"
}

alerts = []

# =====================
# Logic
# =====================
for name, ticker in symbols.items():
    data = yf.download(ticker, period="6mo", interval="1d", progress=False)

    if data.empty or "Close" not in data or len(data) < 60:
        continue

    # ✅ تحويل الإغلاق لسلسلة أرقام مؤكدة
    close = data["Close"].squeeze()

    # EMA دخول
    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()

    # EMA خروج
    ema10 = close.ewm(span=10, adjust=False).mean()
    ema30 = close.ewm(span=30, adjust=False).mean()

    # RSI
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    # قيم رقمية صريحة
    ema20_prev = float(ema20.iloc[-2])
    ema20_last = float(ema20.iloc[-1])
    ema50_prev = float(ema50.iloc[-2])
    ema50_last = float(ema50.iloc[-1])

    ema10_prev = float(ema10.iloc[-2])
    ema10_last = float(ema10.iloc[-1])
    ema30_prev = float(ema30.iloc[-2])
    ema30_last = float(ema30.iloc[-1])

    rsi_last = float(rsi.iloc[-1])

    # =====================
    # BUY
    # =====================
    if ema20_prev < ema50_prev and ema20_last > ema50_last and rsi_last > 50:
        alerts.append(f"📈 شراء: {name} | RSI={round(rsi_last,1)}")

    # =====================
    # SELL (سريع)
    # =====================
    elif ema10_prev > ema30_prev and ema10_last < ema30_last and rsi_last < 45:
        alerts.append(f"📉 بيع سريع: {name} | RSI={round(rsi_last,1)}")

# =====================
# Send alerts
# =====================
if alerts:
    send_telegram("🚨 تنبيهات EGX:\n\n" + "\n".join(alerts))
else:
    send_telegram("ℹ️ لا توجد إشارات اليوم")
