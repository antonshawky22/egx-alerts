print("🚦 EGX Alerts – Full Strategy (Final Stable Version)")

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

LOOKBACK = 15
DEPTH = 3
SIDEWAYS_THRESHOLD = 0.04
RANGE_ENTRY_PERCENT = 0.05
STATE_FILE = "last_signals.json"

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
    n = len(close_array)
    for i in range(DEPTH, n - DEPTH):
        window = close_array[i-DEPTH:i+DEPTH+1]
        if close_array[i] == np.max(window):
            highs.append((i, float(close_array[i])))
        if close_array[i] == np.min(window):
            lows.append((i, float(close_array[i])))
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

    close = float(last["Close"].iloc[0] if hasattr(last["Close"], 'iloc') else last["Close"].item() if hasattr(last["Close"], 'item') else last["Close"])

    signal = None
    stop = None
    dist_support = None
    dist_resist = None

    prev_ema8 = float(prev["EMA8"].iloc[0] if hasattr(prev["EMA8"], 'iloc') else prev["EMA8"].item() if hasattr(prev["EMA8"], 'item') else prev["EMA8"])
    prev_ema15 = float(prev["EMA15"].iloc[0] if hasattr(prev["EMA15"], 'iloc') else prev["EMA15"].item() if hasattr(prev["EMA15"], 'item') else prev["EMA15"])
    last_ema8 = float(last["EMA8"].iloc[0] if hasattr(last["EMA8"], 'iloc') else last["EMA8"].item() if hasattr(last["EMA8"], 'item') else last["EMA8"])
    last_ema15 = float(last["EMA15"].iloc[0] if hasattr(last["EMA15"], 'iloc') else last["EMA15"].item() if hasattr(last["EMA15"], 'item') else last["EMA15"])
    last_rsi = float(last["RSI"].iloc[0] if hasattr(last["RSI"], 'iloc') else last["RSI"].item() if hasattr(last["RSI"], 'item') else last["RSI"])

    if trend == "UP":
        if prev_ema8 < prev_ema15 and last_ema8 > last_ema15:
            signal = "BUY"
        elif prev_ema8 > prev_ema15 and last_ema8 < last_ema15:
            signal = "SELL"
        elif last_rsi >= 80:
            signal = "SELL"
        if lows:
            stop = min([l[1] for l in lows[-DEPTH:]])

    elif trend == "SIDEWAYS":
        support = float(df["Close"].min().item() if hasattr(df["Close"].min(), 'item') else df["Close"].min())
        resistance = float(df["Close"].max().item() if hasattr(df["Close"].max(), 'item') else df["Close"].max())
        dist_support = (close - support) / support * 100
        dist_resist = (resistance - close) / resistance * 100
        if dist_support <= RANGE_ENTRY_PERCENT * 100:
            signal = "BUY"
        elif dist_resist <= RANGE_ENTRY_PERCENT * 100:
            signal = "SELL"

    elif trend == "DOWN":
        signal = None

    return signal, stop, dist_support, dist_resist

# =====================
# MAIN LOOP
# =====================
messages_up = []
messages_side = []
messages_down = []
today = str(datetime.today().date())

for symbol in SYMBOLS:
    df = get_data(symbol)
    if df is None:
        messages_up.append(f"⚠️ {symbol} data failure")
        continue

    df = calculate_indicators(df)
    highs, lows = find_swings(df["Close"].values)
    trend = classify_trend(highs, lows)
    last_date = df.index[-1].date()

    signal, stop, dist_support, dist_resist = detect_signal(df, trend, highs, lows)
    price = round(float(df["Close"].iloc[-1].item() if hasattr(df["Close"].iloc[-1], 'item') else df["Close"].iloc[-1]), 2)

    # قراءة آخر إشارة محفوظة لمنع التكرار
    last_signal_state = state.get(symbol, {})
    last_signal_text = last_signal_state.get("signal_text", "")

    stop_text = f" | 🚨 Stop: {round(stop,2)}" if stop else ""
    dist_text = ""
    if dist_support is not None and dist_support <= 5:
        dist_text = f" | {round(dist_support,2)}%"
    elif dist_resist is not None and dist_resist <= 5:
        dist_text = f" | {round(dist_resist,2)}%"

    # تكوين النص الجديد
    if trend == "UP" and signal:
        new_signal_text = f"🟢 {symbol} | {price} | {last_date}{stop_text}"
    elif trend == "DOWN" and signal:
        new_signal_text = f"🔴 {symbol} | {price} | {last_date}{stop_text}"
    elif trend == "SIDEWAYS" and signal:
        new_signal_text = f"{'🟢' if signal=='BUY' else '🔴'} {symbol} | {price} | {last_date}{dist_text}"
    else:
        new_signal_text = ""

    # إذا الإشارة تغيرت فقط أضفها للرسائل
    if new_signal_text and new_signal_text != last_signal_text:
        if trend == "UP":
            messages_up.append(new_signal_text)
        elif trend == "DOWN":
            messages_down.append(new_signal_text)
        elif trend == "SIDEWAYS":
            messages_side.append(new_signal_text)
        state[symbol] = {"trend": trend, "date": today, "signal_text": new_signal_text}
    else:
        state[symbol] = {"trend": trend, "date": today, "signal_text": last_signal_text}

# =====================
# SEND TELEGRAM
# =====================
messages = []
if messages_up:
    messages.append("↗️ صاعد (شراء/بيع):")
    messages.extend([f"- {m}" for m in messages_up])
if messages_side:
    messages.append("🔛 عرضي (قمم/قيعان):")
    messages.extend([f"- {m}" for m in messages_side])
if messages_down:
    messages.append("🔻 هابط:")
    messages.extend([f"- {m}" for m in messages_down])

if messages:
    text = f"🚦 EGX Alerts – {today}\n\n" + "\n".join(messages)
else:
    # لا توجد إشارات جديدة
    text = f"Egx-1 ℹ️ No new signal\n\nlast candle date:\n📅 {last_date}"

send_telegram(text)

# =====================
# SAVE STATE
# =====================
with open(STATE_FILE, "w") as f:
    json.dump(state, f, indent=4)
