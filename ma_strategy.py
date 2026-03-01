print("🚦 EGX Alerts – Full Strategy (Stable Version)")

import yfinance as yf
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime
import requests

# =====================
# SETTINGS
# =====================
SYMBOLS = [
    "OFH.CA","OLFI.CA","EMFD.CA","ETEL.CA","EAST.CA","EFIH.CA",
    "ABUK.CA","OIH.CA","SWDY.CA","ISPH.CA","ATQA.CA","MTIE.CA",
    "ELEC.CA","HRHO.CA","ORWE.CA","JUFO.CA","DSCW.CA","SUGR.CA",
    "ELSH.CA","RMDA.CA","RAYA.CA","EEII.CA","MPCO.CA","GBCO.CA",
    "TMGH.CA","ORHD.CA","AMOC.CA","FWRY.CA","COMI.CA","ADIB.CA",
    "PHDC.CA","MCQE.CA","SKPC.CA","EGAL.CA"
]

LOOKBACK = 50   # عدد الشموع
DEPTH = 8       # عمق تحديد القمم والقيعان
SIDEWAYS_THRESHOLD = 0.04
RANGE_ENTRY_PERCENT = 0.05
STATE_FILE = "signals_state.json"

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# =====================
# TELEGRAM
# =====================
def send_telegram(text):
    if not TOKEN or not CHAT_ID:
        print("Telegram credentials not set")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": text}, timeout=10)
    except Exception as e:
        print("Telegram send failed:", e)

# =====================
# LOAD STATE
# =====================
if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r") as f:
        state = json.load(f)
else:
    state = {}

# =====================
# DATA FUNCTIONS
# =====================
def get_data(symbol):
    try:
        df = yf.download(symbol, period="6mo", interval="1d", progress=False)
        if df.empty or len(df) < LOOKBACK:
            return None
        return df.tail(LOOKBACK).copy()
    except:
        return None

def calculate_indicators(df):
    df["EMA8"] = df["Close"].ewm(span=8).mean()
    df["EMA15"] = df["Close"].ewm(span=15).mean()

    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss
    df["RSI"] = 100 - (100 / (1 + rs))
    return df

def find_swings(close):
    highs = []
    lows = []
    close_array = np.array(close).flatten()  # ضمان 1D
    for i in range(DEPTH, len(close_array)-DEPTH):
        window = close_array[i-DEPTH:i+DEPTH+1]
        if close_array[i] == np.max(window):
            highs.append((i, close_array[i].item()))
        if close_array[i] == np.min(window):
            lows.append((i, close_array[i].item()))
    return highs, lows

def classify_trend(highs, lows):
    if len(highs) < 2 or len(lows) < 2:
        return "SIDEWAYS"

    last_high, prev_high = highs[-1][1], highs[-2][1]
    last_low, prev_low = lows[-1][1], lows[-2][1]

    if last_high > prev_high and last_low > prev_low:
        return "UP"
    if last_high < prev_high and last_low < prev_low:
        return "DOWN"

    high_diff = abs(last_high - prev_high) / prev_high
    low_diff = abs(last_low - prev_low) / prev_low

    if high_diff <= SIDEWAYS_THRESHOLD and low_diff <= SIDEWAYS_THRESHOLD:
        return "SIDEWAYS"

    return "SIDEWAYS"

def detect_signal(df, trend, highs, lows):
    last = df.iloc[-1]
    prev = df.iloc[-2]
    close = float(last["Close"])
    signal = None
    stop = None

    if trend == "UP":
        if float(prev["EMA8"]) < float(prev["EMA15"]) and float(last["EMA8"]) > float(last["EMA15"]):
            signal = "BUY"
        elif float(prev["EMA8"]) > float(prev["EMA15"]) and float(last["EMA8"]) < float(last["EMA15"]):
            signal = "SELL"
        elif last["RSI"] >= 80:
            signal = "SELL"
        if lows:
            stop = min([l[1] for l in lows[-DEPTH:]])

    elif trend == "SIDEWAYS":
        support = float(df["Close"].min())
        resistance = float(df["Close"].max())
        dist_support = (close - support) / support
        dist_resist = (resistance - close) / resistance

        if dist_support <= RANGE_ENTRY_PERCENT:
            signal = "BUY"
            stop = support
        elif dist_resist <= RANGE_ENTRY_PERCENT:
            signal = "SELL"
            stop = resistance

    elif trend == "DOWN":
        signal = None

    return signal, stop

# =====================
# MAIN LOOP
# =====================
messages = []
today = str(datetime.today().date())

for symbol in SYMBOLS:
    df = get_data(symbol)
    if df is None:
        messages.append(f"⚠️ {symbol} data failure")
        continue

    df = calculate_indicators(df)
    highs, lows = find_swings(df["Close"])
    trend = classify_trend(highs, lows)

    previous_trend = state.get(symbol, {}).get("trend", "")

    # 🚧 أي تغيير اتجاه
    if previous_trend and previous_trend != trend:
        price = round(df["Close"].iloc[-1], 2)
        messages.append(f"🚧 {symbol} | Trend: {previous_trend} → {trend} | {price}")

    signal, stop = detect_signal(df, trend, highs, lows)

    # بناء الرسالة المتفق عليها
    if signal:
        price = round(df["Close"].iloc[-1], 2)
        stop_text = f" | 🚨 Stop: {round(stop,2)}" if stop else ""
        if signal == "BUY":
            messages.append(f"🟢 {symbol} | {price} | {today}{stop_text}")
        elif signal == "SELL":
            messages.append(f"🔴 {symbol} | {price} | {today}{stop_text}")

    # تحديث الحالة لتجنب تكرار الإشارات
    state[symbol] = {"trend": trend, "date": today}

# =====================
# SEND TELEGRAM
# =====================
if messages:
    text = f"🚦 EGX Alerts (Compact) – {today}\n\n" + "\n".join(messages)
    send_telegram(text)

# =====================
# SAVE STATE
# =====================
with open(STATE_FILE, "w") as f:
    json.dump(state, f, indent=4)
