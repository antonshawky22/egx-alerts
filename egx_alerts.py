print("EGX ALERTS - Moving Average Reversal Strategy (DAILY)")

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
    "TMGH": "TMGH.CA","ORHD": "ORHD.CA","AMOC": "AMOC.CA","FWRY": "FWRY.CA"
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
    if df is None or len(df) < 80:
        data_failures.append(name)
        continue

    close = df["Close"]

    # حساب EMA المختلفة
    df["EMA4"] = ema(close, 4)
    df["EMA9"] = ema(close, 9)
    df["EMA20"] = ema(close, 20)
    df["EMA50"] = ema(close, 50)
    df["EMA75"] = ema(close, 75)

    last = df.iloc[-1]
    prev = df.iloc[-2]

    prev_state = last_signals.get(name)

    # =====================
    # شروط BUY/SELL مع فلتر الفرق 1% لتقليل إشارات الاتجاه العرضي
    # =====================
    range_filter_buy = abs(last["EMA4"] - last["EMA9"]) / last["Close"] > 0.01
    range_filter_sell = abs(last["EMA4"] - last["EMA9"]) / last["Close"] > 0.01

    # 🟢 BUY: EMA4 تقطع EMA9 لأعلى مع فلتر 1% + فوق EMA75 كفلتر اتجاه صاعد
    buy_signal = last["EMA4"] > last["EMA9"] and prev["EMA4"] <= prev["EMA9"] and last["Close"] > last["EMA75"] and range_filter_buy

    # 🔴 SELL: أي تقاطع هابط من EMA4 و EMA9 أو EMA4 و EMA20 أو كسر EMA75
    sell_signal = (
        (last["EMA4"] < last["EMA9"] and prev["EMA4"] >= prev["EMA9"]) or
        (last["EMA4"] < last["EMA20"] and prev["EMA4"] >= prev["EMA20"]) or
        (last["Close"] < last["EMA75"])
    ) and range_filter_sell

    if buy_signal:
        curr_state = "BUY"
    elif sell_signal:
        curr_state = "SELL"
    else:
        continue

    # إضافة الرسالة فقط إذا تغيرت الحالة عن آخر إشارة
    if curr_state != prev_state:
        alerts.append(
            f"{'🟢 BUY' if curr_state == 'BUY' else '🔴 SELL'} | {name}\n"
            f"Price: {last['Close']:.2f}\n"
            f"Date: {df.index[-1].date()}"
        )
        new_signals[name] = curr_state

# =====================
# حفظ آخر الإشارات
# =====================
with open(SIGNALS_FILE, "w") as f:
    json.dump(new_signals, f)

# =====================
# إرسال الإشارات عبر تليجرام
# =====================
if alerts:
    send_telegram("\n\n".join(alerts))
else:
    send_telegram("ℹ️ لا توجد إشارات جديدة")
