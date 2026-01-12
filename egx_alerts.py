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
# EGX symbols
# =====================
symbols = {
    "OFH": "OFH.CA",
    "OLFI": "OLFI.CA",
    "EMFD": "EMFD.CA",
    "ETEL": "ETEL.CA",
    "EAST": "EAST.CA",
    "EFIH": "EFIH.CA",
    "ABUK": "ABUK.CA",
    "OIH": "OIH.CA",
    "SWDY": "SWDY.CA",
    "ISPH": "ISPH.CA",
    "ATQA": "ATQA.CA",
    "MTIE": "MTIE.CA",
    "ELEC": "ELEC.CA",
    "HRHO": "HRHO.CA",
    "ORWE": "ORWE.CA",
    "JUFO": "JUFO.CA",
    "DSCW": "DSCW.CA",
    "SUGR": "SUGR.CA",
    "ELSH": "ELSH.CA",
    "RMDA": "RMDA.CA",
    "RAYA": "RAYA.CA",
    "EEII": "EEII.CA",
    "MPCO": "MPCO.CA",
    "GBCO": "GBCO.CA",

    # extra liquid
    "COMI": "COMI.CA",
    "EFG": "EFGH.CA",
    "TMGH": "TMGH.CA",
    "ORAS": "ORAS.CA",
    "AMOC": "AMOC.CA",
}

alerts = []
data_failures = []

# =====================
# PRICE FETCH
# =====================

# Plan A: yfinance
def fetch_yfinance(ticker):
    try:
        data = yf.download(ticker, period="6mo", interval="1d", progress=False)
        if data.empty or "Close" not in data:
            return None
        return data
    except Exception:
        return None

# Plan B: stooq (CSV مباشر)
def fetch_stooq(ticker):
    try:
        symbol = ticker.replace(".CA", "")
        url = f"https://stooq.com/q/d/l/?s={symbol}&i=d"
        data = pd.read_csv(url)

        if data.empty or "Close" not in data:
            return None

        data["Date"] = pd.to_datetime(data["Date"])
        data.set_index("Date", inplace=True)
        return data
    except Exception:
        return None

def get_price_data(ticker):
    data = fetch_yfinance(ticker)
    if data is not None:
        return data

    data = fetch_stooq(ticker)
    if data is not None:
        return data

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

    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()

    ema10 = close.ewm(span=10, adjust=False).mean()
    ema30 = close.ewm(span=30, adjust=False).mean()

    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    ema20_prev, ema20_last = ema20.iloc[-2], ema20.iloc[-1]
    ema50_prev, ema50_last = ema50.iloc[-2], ema50.iloc[-1]
    ema10_prev, ema10_last = ema10.iloc[-2], ema10.iloc[-1]
    ema30_prev, ema30_last = ema30.iloc[-2], ema30.iloc[-1]
    rsi_last = rsi.iloc[-1]
   # =====================
# BUY مبكر
# =====================
ema_gap = abs(ema20_last - ema50_last) / ema50_last

if (
    ema20_last < ema50_last
    and ema_gap < 0.01   # الفرق أقل من 1%
    and rsi_last >= 45
):
    alerts.append(f"🟢 شراء مبكر: {name} | RSI={round(rsi_last,1)}")
    if ema20_prev < ema50_prev and ema20_last > ema50_last and rsi_last > 50:
        alerts.append(f"📈 شراء: {name} | RSI={round(rsi_last,1)}")

    elif ema10_prev > ema30_prev and ema10_last < ema30_last and rsi_last < 45:
        alerts.append(f"📉 بيع سريع: {name} | RSI={round(rsi_last,1)}")

# =====================
# Send alerts
# =====================
if alerts:
    send_telegram("🚨 تنبيهات EGX:\n\n" + "\n".join(alerts))
else:
    send_telegram("ℹ️ لا توجد إشارات اليوم")

# =====================
# Data source warning
# =====================
if data_failures:
    send_telegram(
        "⚠️ تحذير مصدر أسعار:\n"
        "فشل جلب البيانات من كل المصادر للأسهم:\n" +
        ", ".join(data_failures)
    )
