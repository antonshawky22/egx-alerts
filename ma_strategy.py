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

LOOKBACK = 50
DEPTH = 8
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
    df["EMA8"] = df["Close"].ewm(span=8, adjust=False).mean()
    df["EMA15"] = df["Close"].ewm(span=15, adjust=False).mean()

    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss
    df["RSI"] = 100 - (100 / (1 + rs))
    return df

def find_swings(close_array):
    highs = []
    lows = []

    # تحويل كل القيم ل float لتجنب مشاكل Series / numpy scalars
    close_list = [float(x) for x in close_array]

    for i in range(DEPTH, len(close_list)-DEPTH):
        window = close_list[i-DEPTH:i+DEPTH+1]
        center_val = close_list[i]
        if center_val >= max(window):
            highs.append((i, center_val))
        if center_val <= min(window):
            lows.append((i, center_val))
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
    last_close = float(df["Close"].iloc[-1])
    signal = None
    stop = None

    if trend == "UP":
        prev_ema8 = float(df["EMA8"].iloc[-2])
        prev_ema15 = float(df["EMA15"].iloc[-2])
        last_ema8 = float(df["EMA8"].iloc[-1])
        last_ema15 = float(df["EMA15"].iloc[-1])

        if prev_ema8 < prev_ema15 and last_ema8 > last_ema15:
            signal = "BUY"
        elif prev_ema8 > prev_ema15 and last_ema8 < last_ema15:
            signal = "SELL"
        elif float(df["RSI"].iloc[-1]) >= 80:
            signal = "SELL"

        if lows:
            stop = min([l[1] for l in lows[-DEPTH:]])

    elif trend == "SIDEWAYS":
        support = float(df["Close"].min())
        resistance = float(df["Close"].max())

        dist_support = (last_close - support) / support
        dist_resist = (resistance - last_close) / resistance

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
    highs, lows = find_swings(df["Close"].values)
    trend = classify_trend(highs, lows)

    prev_state = state.get(symbol, {})
    previous_trend = prev_state.get("trend", "")
    previous_signal = prev_state.get("signal", "")
    previous_date = prev_state.get("date", "")

    # 🚧 أي تغيير اتجاه
    if previous_trend and previous_trend != trend:
        messages.append(f"🚧 {symbol} | {previous_trend} → {trend} | {round(float(df['Close'].iloc[-1]),2)}")

    signal, stop = detect_signal(df, trend, highs, lows)

    # عدم تكرار نفس الإشارة لنفس اليوم
    if signal and previous_signal != signal:
        stop_text = f" | 🚨 Stop: {round(stop,2)}" if stop else ""
        if signal == "BUY":
            messages.append(f"🟢 {symbol} | {trend} | {round(float(df['Close'].iloc[-1]),2)}{stop_text}")
        elif signal == "SELL":
            messages.append(f"🔴 {symbol} | {trend} | {round(float(df['Close'].iloc[-1]),2)}{stop_text}")

    # تحديث حالة السهم
    state[symbol] = {"trend": trend, "signal": signal, "date": today}

# =====================
# SEND TELEGRAM
# =====================
if messages:
    text = f"🚦 EGX Alerts (Compact) – {today}\n\n" + "\n".join(messages)
    send_telegram(text)
else:
    send_telegram(f"MA S ℹ️ لا توجد إشارات جديدة\n\nlast candle date:\n📅 {today}")

# =====================
# SAVE STATE
# =====================
with open(STATE_FILE, "w") as f:
    json.dump(state, f, indent=4)
