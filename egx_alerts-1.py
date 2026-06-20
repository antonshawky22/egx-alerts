print("EGX LADDER CYCLE SYSTEM")

import yfinance as yf
import requests
import os
import json
import pandas as pd
import time

# =====================
# Telegram settings
# =====================
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram(text):
    if not TOKEN or not CHAT_ID:
        print(text)
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
    "COMI": "COMI.CA",
    "HRHO": "HRHO.CA",
    "FWRY": "FWRY.CA",
    "EFIH": "EFIH.CA",
    "TMGH": "TMGH.CA"
}

STATE_FILE = "last_signals.json"

# =====================
# Load state
# =====================
try:
    with open(STATE_FILE, "r") as f:
        state_data = json.load(f)
except:
    state_data = {}

# =====================
# Fetch Data
# =====================
def fetch_data(ticker):
    try:
        df = yf.download(ticker, period="6mo", interval="1d", auto_adjust=True, progress=False)
        if df is None or df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except:
        return None

# =====================
# RSI
# =====================
def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# =====================
# MAIN LOOP
# =====================
alerts = []

for name, ticker in symbols.items():

    time.sleep(0.5)

    df = fetch_data(ticker)
    if df is None or len(df) < 120:
        continue

    close = df["Close"]

    df["EMA120"] = close.ewm(span=120, adjust=False).mean()
    df["RSI"] = rsi(close)

    last = df.iloc[-1]
    price = last["Close"]
    rsi_val = last["RSI"]

    # =====================
    # Init state
    # =====================
    if name not in state_data:
        state_data[name] = {
            "cycle": 1,
            "stage": 0,
            "position": 0.0,
            "avg_price": 0.0,
            "levels": {"buy": [], "sell": []}
        }

    s = state_data[name]

    # =====================
    # Trend filter
    # =====================
    ema_up = df["EMA120"].iloc[-1] > df["EMA120"].iloc[-15]

    # =====================
    # BUY CONDITIONS (3 levels)
    # =====================
    buy1 = ema_up and rsi_val <= 55
    buy2 = ema_up and rsi_val <= 45
    buy3 = ema_up and rsi_val <= 40

    # =====================
    # SELL CONDITIONS (3 levels)
    # =====================
    sell1 = rsi_val >= 65
    sell2 = rsi_val >= 72
    sell3 = rsi_val >= 78

    action = None

    # =====================
    # BUY LOGIC
    # =====================
    if s["stage"] == 0 and buy1:
        s["stage"] = 1
        s["position"] = 0.33
        s["avg_price"] = price
        s["levels"]["buy"].append(price)
        action = "BUY 33%"

    elif s["stage"] == 1 and buy2:
        s["stage"] = 2
        s["position"] = 0.66
        s["avg_price"] = (s["avg_price"] + price) / 2
        s["levels"]["buy"].append(price)
        action = "BUY 66%"

    elif s["stage"] == 2 and buy3:
        s["stage"] = 3
        s["position"] = 1.0
        s["avg_price"] = (s["avg_price"] + price) / 2
        s["levels"]["buy"].append(price)
        action = "BUY 100%"

    # =====================
    # SELL LOGIC
    # =====================
    elif s["stage"] == 3 and sell1:
        s["stage"] = -1
        s["position"] = 0.66
        s["levels"]["sell"].append(price)
        action = "SELL 33%"

    elif s["stage"] == -1 and sell2:
        s["stage"] = -2
        s["position"] = 0.33
        s["levels"]["sell"].append(price)
        action = "SELL 66%"

    elif s["stage"] == -2 and sell3:
        s["stage"] = 0
        s["position"] = 0.0
        s["avg_price"] = 0.0
        s["levels"] = {"buy": [], "sell": []}
        s["cycle"] += 1
        action = "SELL 100% (CYCLE RESET)"

    # =====================
    # PROFIT
    # =====================
    profit = 0
    if s["avg_price"] > 0:
        profit = ((price - s["avg_price"]) / s["avg_price"]) * 100

    # =====================
    # ALERT
    # =====================
    if action:
        alerts.append(
            f"{action} | {name}\n"
            f"Price: {price:.2f}\n"
            f"Position: {s['position']*100:.0f}%\n"
            f"Avg: {s['avg_price']:.2f}\n"
            f"RSI: {rsi_val:.1f}\n"
            f"Cycle: {s['cycle']}\n"
            f"P/L: {profit:.2f}%"
        )

# =====================
# SAVE STATE
# =====================
with open(STATE_FILE, "w") as f:
    json.dump(state_data, f)

# =====================
# SEND ALERTS
# =====================
if alerts:
    send_telegram("\n\n".join(alerts))
else:
    send_telegram("No new ladder signals")
