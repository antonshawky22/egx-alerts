print("EGX ALERTS - Moving Average Strong Filter Strategy (DAILY)")

import yfinance as yf
import requests
import os
import json
import pandas as pd
from datetime import datetime

# =====================
# Telegram settings
# =====================
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram(text):
    if not TOKEN or not CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": text}, timeout=10)
    except Exception as e:
        print("Telegram send failed:", e)

# =====================
# EGX symbols
# =====================
symbols = {
    "OFH": "OFH.CA","OLFI": "OLFI.CA","EMFD": "EMFD.CA","ETEL": "ETEL.CA",
    "EAST": "EAST.CA","EFIH": "EFIH.CA","ABUK": "ABUK.CA","OIH": "OIH.CA",
    "SWDY": "SWDY.CA","ISPH": "ISPH.CA","ATQA": "ATQA.CA","MTIE": "MTIE.CA",
    "ELEC": "ELEC.CA","HRHO": "HRHO.CA","ORWE": "ORWE.CA","JUFO": "JUFO.CA",
    "DSCW": "DSCW.CA","SUGR": "SUGR.CA","ELSH": "ELSH.CA","RMDA": "RMDA.CA",
    "RAYA": "RAYA.CA","EEII": "EEII.CA","MPCO": "MPCO.CA","GBCO": "GBCO.CA",
    "TMGH": "TMGH.CA","ORHD": "ORHD.CA","AMOC": "AMOC.CA","FWRY": "FWRY.CA",
    "COMI": "COMI.CA","ADIB": "ADIB.CA","QNBA": "QNBA.CA","PHDC": "PHDC.CA",
    "EGTS": "EGTS.CA","MCQE": "MCQE.CA","SKPC": "SKPC.CA","ESRS": "ESRS.CA",
    "EGAL": "EGAL.CA","MNHD": "MNHD.CA"
}

# =====================
# Load last signals
# =====================
SIGNALS_FILE = "last_signals.json"
try:
    with open(SIGNALS_FILE, "r") as f:
        last_signals = json.load(f)
except Exception:
    last_signals = {}

new_signals = last_signals.copy()
alerts = []
data_failures = []

last_candle_date = None  # ← أهم إضافة

# =====================
# Indicators
# =====================
def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

# =====================
# Fetch data
# =====================
def fetch_data(ticker):
    try:
        df = yf.download(
            ticker,
            period="6mo",
            interval="1d",
            auto_adjust=True,
            progress=False
        )
        if df is None or df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except Exception:
        return None

# =====================
# Main Logic
# =====================
for name, ticker in symbols.items():
    df = fetch_data(ticker)
    if df is None or len(df) < 50:
        data_failures.append(name)
        continue

    # تحديث تاريخ آخر شمعة ناجحة
    candle_date = df.index[-1].date()
    if last_candle_date is None or candle_date > last_candle_date:
        last_candle_date = candle_date

    close = df["Close"]

    df["EMA4"] = ema(close, 4)
    df["EMA9"] = ema(close, 9)
    df["EMA25"] = ema(close, 25)
    df["EMA50"] = ema(close, 50)

    last = df.iloc[-1]
    prev = df.iloc[-2]

    prev_state = last_signals.get(name)

    buy_signal = (
        last["EMA4"] > last["EMA9"] and prev["EMA4"] <= prev["EMA9"] and
        last["Close"] > last["EMA25"] and last["Close"] > last["EMA50"] and
        df["EMA25"].iloc[-1] > df["EMA50"].iloc[-1]
    )

    sell_signal = (
        (last["EMA4"] < last["EMA9"] and prev["EMA4"] >= prev["EMA9"]) or
        (last["Close"] < last["EMA25"]) or
        (df["EMA25"].iloc[-1] < df["EMA50"].iloc[-1])
    )

    if buy_signal:
        curr_state = "BUY"
    elif sell_signal:
        curr_state = "SELL"
    else:
        continue

    if curr_state != prev_state:
        alerts.append(
            f"{'🟢 BUY' if curr_state == 'BUY' else '🔴 SELL'} | {name}\n"
            f"Price: {last['Close']:.2f}\n"
            f"Date: {candle_date}"
        )
        new_signals[name] = curr_state

# =====================
# إشعار فشل البيانات
# =====================
if data_failures:
    send_telegram(f"⚠️ فشل تحميل بيانات لبعض الأسهم: {', '.join(data_failures)}")

# =====================
# حفظ الإشارات
# =====================
with open(SIGNALS_FILE, "w") as f:
    json.dump(new_signals, f)

# =====================
# Telegram output
# =====================
if alerts:
    send_telegram("\n\n".join(alerts))
else:
    if last_candle_date:
        send_telegram(
            "ℹ️ لا توجد إشارات جديدة\n\n"
            f"آخر شمعة محسوبة:\n📅 {last_candle_date}"
        )
    else:
        send_telegram("⚠️ لم يتم تحميل أي بيانات أسعار")
