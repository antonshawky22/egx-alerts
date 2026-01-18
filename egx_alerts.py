print("EGX ALERTS - LuxAlgo Moving Average Converging (EXACT MATCH)")

import yfinance as yf
import requests
import os
import json
import numpy as np
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
    "RAYA": "RAYA.CA","EEII": "EEII.CA","MPCO": "MPCO.CA","GBCO": "GBCO.CA",
    "TMGH": "TMGH.CA","ORAS": "ORAS.CA","AMOC": "AMOC.CA","FWRY": "FWRY.CA"
}

# =====================
# LuxAlgo settings (FINAL)
# =====================
LENGTH = 80
INCR = 12
FAST = 12
K = 1 / INCR

# =====================
# Load last signals
# =====================
SIGNALS_FILE = "last_signals.json"
last_signals = json.load(open(SIGNALS_FILE)) if os.path.exists(SIGNALS_FILE) else {}
new_signals = last_signals.copy()

alerts = []
data_failures = []

# =====================
# Fetch data
# =====================
def fetch_data(ticker):
    try:
        df = yf.download(ticker, period="6mo", interval="1d", progress=False)
        if df is None or df.empty:
            return None
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

    close = df["Close"].astype(float)
    high  = df["High"].astype(float)
    low   = df["Low"].astype(float)

    ma    = np.zeros(len(close))
    fma   = np.zeros(len(close))
    alpha = np.zeros(len(close))

    upper   = high.rolling(LENGTH).max()
    lower   = low.rolling(LENGTH).min()
    init_ma = close.rolling(LENGTH).mean()

    for i in range(len(close)):
    init_val = float(init_ma.iloc[i])

    if i == 0 or np.isnan(init_val):
        ma[i]  = float(close.iloc[i])
        fma[i] = float(close.iloc[i])
        continue

    cross = (
        (close.iloc[i-1] <= ma[i-1] and close.iloc[i] > ma[i-1]) or
        (close.iloc[i-1] >= ma[i-1] and close.iloc[i] < ma[i-1])
    )

    if cross:
        alpha[i] = 2 / (LENGTH + 1)
    elif close.iloc[i] > ma[i-1] and upper.iloc[i] > upper.iloc[i-1]:
        alpha[i] = alpha[i-1] + K
    elif close.iloc[i] < ma[i-1] and lower.iloc[i] < lower.iloc[i-1]:
        alpha[i] = alpha[i-1] + K
    else:
        alpha[i] = alpha[i-1]

    ma[i] = ma[i-1] + alpha[i-1] * (close.iloc[i] - ma[i-1])

    if cross:
        fma[i] = (close.iloc[i] + fma[i-1]) / 2
    elif close.iloc[i] > ma[i]:
        fma[i] = max(close.iloc[i], fma[i-1]) + (close.iloc[i] - fma[i-1]) / FAST
    else:
        fma[i] = min(close.iloc[i], fma[i-1]) + (close.iloc[i] - fma[i-1]) / FAST

    # =====================
    # Signal logic (STATE CHANGE ONLY)
    # =====================
    prev_state = last_signals.get(name)
    curr_state = "BUY" if fma[-1] > ma[-1] else "SELL"

    if curr_state != prev_state:
        price = close.iloc[-1]
        candle_date = close.index[-1].date()

        alerts.append(
            f"{'🟢 BUY' if curr_state == 'BUY' else '🔴 SELL'} | {name}\n"
            f"Price: {price:.2f}\n"
            f"Date: {candle_date}"
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
