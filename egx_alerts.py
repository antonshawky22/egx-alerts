print("EGX ALERTS - RSI Reversal Strategy (DAILY)")

import yfinance as yf
import requests
import os
import json
import numpy as np
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
    requests.post(url, data={"chat_id": CHAT_ID, "text": text}, timeout=10)

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

def rsi(series, period=6):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

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

    df["EMA6"]  = ema(close, 6)
    df["EMA10"] = ema(close, 10)
    df["EMA75"] = ema(close, 75)
    df["RSI6"]  = rsi(close, 6)

    last = df.iloc[-1]
    prev = df.iloc[-2]

    prev_state = last_signals.get(name)

    # 🟢 BUY
    buy_signal = (
        last["RSI6"] <= 50 and
        last["Close"] > last["EMA75"]
    )

    # 🔴 SELL
    sell_signal = (
        (prev["EMA6"] >= prev["EMA10"] and last["EMA6"] < last["EMA10"]) or
        (prev["RSI6"] >= 50 and last["RSI6"] < 50) or
        (prev["Close"] >= prev["EMA75"] and last["Close"] < last["EMA75"])
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
            f"RSI6: {last['RSI6']:.1f}\n"
            f"Date: {df.index[-1].date()}"
        )
        new_signals[name] = curr_state

# =====================
# Save signals
# =====================
with open(SIGNALS_FILE, "w") as f:
    json.dump(new_signals, f)

# =====================
# Telegram
# =====================
if alerts:
    send_telegram("🚨 EGX Reversal Signals:\n\n" + "\n\n".join(alerts))
else:
    send_telegram("ℹ️ لا توجد إشارات جديدة")

send_telegram(
    f"✅ Bot Running\n"
    f"📅 {datetime.utcnow().date()}\n"
    f"📊 Signals: {len(alerts)}\n"
    f"⚠️ Data Errors: {len(data_failures)}"
    )
