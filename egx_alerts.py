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
    requests.post(url, data={"chat_id": CHAT_ID, "text": text})

# =====================
# EGX symbols
# =====================
symbols = {
    "OFH": "OFH.CA","OLFI": "OLFI.CA","EMFD": "EMFD.CA","ETEL": "ETEL.CA",
    "EAST": "EAST.CA","EFIH": "EFIH.CA","ABUK": "ABUK.CA","OIH": "OIH.CA",
    "SWDY": "SWDY.CA","ISPH": "ISPH.CA","ATQA": "ATQA.CA","MTIE": "MTIE.CA",
    "ELEC": "ELEC.CA","HRHO": "HRHO.CA","ORWE": "ORWE.CA","JUFO": "JUFO.CA",
    "DSCW": "DSCW.CA","SUGR": "SUGR.CA","ELSH": "ELSH.CA","RMDA": "RMDA.CA",
    "RAYA": "RAYA.CA","EEII": "EEII.CA","MPCO": "MPCO.CA","GBCO": "GBCO.CA","TMGH": "TMGH.CA",
    "ORAS": "ORAS.CA","AMOC": "AMOC.CA","FWRY": "FWRY.CA"
}

alerts = []
data_failures = []

# =====================
# PRICE FETCH
# =====================
def fetch_yfinance(ticker):
    try:
        df = yf.download(ticker, period="6mo", interval="1d", progress=False)
        if df is None or df.empty or "Close" not in df:
            return None
        return df
    except Exception:
        return None

def fetch_stooq(ticker):
    try:
        symbol = ticker.replace(".CA", "")
        url = f"https://stooq.com/q/d/l/?s={symbol}&i=d"
        df = pd.read_csv(url)
        if df is None or df.empty or "Close" not in df:
            return None
        df["Date"] = pd.to_datetime(df["Date"])
        df.set_index("Date", inplace=True)
        return df
    except Exception:
        return None

def get_price_data(ticker):
    df = fetch_yfinance(ticker)
    if df is not None:
        return df
    return fetch_stooq(ticker)

# =====================
# Logic
# =====================
for name, ticker in symbols.items():
    data = get_price_data(ticker)

    if data is None or len(data) < 60:
        data_failures.append(name)
        continue

    # ✅ حل جذري لمشكلة Series / DataFrame
    close = data["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    close = close.astype(float)

    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()
    ema10 = close.ewm(span=10, adjust=False).mean()
    ema30 = close.ewm(span=30, adjust=False).mean()

    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    rs = gain.rolling(14).mean() / loss.rolling(14).mean()
    rsi = 100 - (100 / (1 + rs))

    # ✅ تحويل صريح لـ float (مهم جدًا)
    ema20_prev = float(ema20.iloc[-2])
    ema20_last = float(ema20.iloc[-1])
    ema50_prev = float(ema50.iloc[-2])
    ema50_last = float(ema50.iloc[-1])
    ema10_prev = float(ema10.iloc[-2])
    ema10_last = float(ema10.iloc[-1])
    ema30_prev = float(ema30.iloc[-2])
    ema30_last = float(ema30.iloc[-1])
    rsi_last  = float(rsi.iloc[-1])

    ema_gap = abs(ema20_last - ema50_last) / ema50_last

    # 🟢 BUY مبكر (إشارات أكتر)
    if ema20_last < ema50_last and ema_gap < 0.015 and 40 <= rsi_last <= 55:
        alerts.append(f"🟢 شراء مبكر: {name} | RSI={round(rsi_last,1)}")

    # 📈 BUY مؤكد
    if ema20_prev < ema50_prev and ema20_last > ema50_last and rsi_last >= 48:
        alerts.append(f"📈 شراء: {name} | RSI={round(rsi_last,1)}")

    # 📉 SELL سريع
    if ema10_prev > ema30_prev and ema10_last < ema30_last and rsi_last <= 50:
        alerts.append(f"📉 بيع سريع: {name} | RSI={round(rsi_last,1)}")

# =====================
# Send alerts
# =====================
if alerts:
    send_telegram("🚨 تنبيهات EGX:\n\n" + "\n".join(alerts))
else:
    send_telegram("ℹ️ لا توجد إشارات اليوم")

if data_failures:
    send_telegram(
        "⚠️ تحذير مصدر أسعار:\nفشل جلب البيانات للأسهم:\n" +
        ", ".join(data_failures)
)
