print("EGX ALERTS - LuxAlgo Moving Average Converging (TRADINGVIEW MATCH)")

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
# LuxAlgo settings
# =====================
LENGTH = 80
INCR   = 12
FAST   = 12
K      = 1 / INCR

# =====================
# Load last signals (SAFE)
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
# Fetch data (ROBUST)
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

        # Fix MultiIndex columns (yfinance bug)
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

    if df is None or len(df) < LENGTH + 5:
        data_failures.append(name)
        continue

    close = df["Close"].astype(float).to_numpy()
    high  = df["High"].astype(float).to_numpy()
    low   = df["Low"].astype(float).to_numpy()

    ma  = np.zeros(len(close))
    fma = np.zeros(len(close))
    alpha = np.zeros(len(close))

    # Rolling extremes (TradingView behavior)
    upper = np.maximum.accumulate(high)
    lower = np.minimum.accumulate(low)

    init_ma = np.full(len(close), np.nan)
    for i in range(LENGTH - 1, len(close)):
        init_ma[i] = np.mean(close[i - LENGTH + 1:i + 1])

    for i in range(len(close)):
        if i == 0 or np.isnan(init_ma[i]):
            ma[i] = close[i]
            fma[i] = close[i]
            alpha[i] = 0
            continue

        cross = (
            (close[i-1] <= ma[i-1] and close[i] > ma[i-1]) or
            (close[i-1] >= ma[i-1] and close[i] < ma[i-1])
        )

        if cross:
            alpha[i] = 2 / (LENGTH + 1)
        elif close[i] > ma[i-1] and upper[i] > upper[i-1]:
            alpha[i] = alpha[i-1] + K
        elif close[i] < ma[i-1] and lower[i] < lower[i-1]:
            alpha[i] = alpha[i-1] + K
        else:
            alpha[i] = alpha[i-1]

        ma[i] = ma[i-1] + alpha[i-1] * (close[i] - ma[i-1])

        if cross:
            fma[i] = (close[i] + fma[i-1]) / 2
        elif close[i] > ma[i]:
            fma[i] = max(close[i], fma[i-1]) + (close[i] - fma[i-1]) / FAST
        else:
            fma[i] = min(close[i], fma[i-1]) + (close[i] - fma[i-1]) / FAST

    # =====================
    # Signal logic (EXACT TV)
    # =====================
    prev_state = last_signals.get(name)
    curr_state = "BUY" if fma[-1] > ma[-1] else "SELL"

    if curr_state != prev_state:
        alerts.append(
            f"{'🟢 BUY' if curr_state == 'BUY' else '🔴 SELL'} | {name}\n"
            f"Price: {close[-1]:.2f}\n"
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
    send_telegram("🚨 EGX LuxAlgo Signals:\n\n" + "\n\n".join(alerts))
else:
    send_telegram("ℹ️ لا توجد إشارات جديدة – الترند مستمر")

send_telegram(
    f"✅ Bot Running\n"
    f"📅 {datetime.utcnow().date()}\n"
    f"📊 Signals: {len(alerts)}\n"
    f"⚠️ Data Errors: {len(data_failures)}"
)
