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
        support = float(df["Close"].min())
        resistance = float(df["Close"].max())
        dist_support = (close - support) / support * 100
        dist_resist = (resistance - close) / resistance * 100
        if dist_support <= RANGE_ENTRY_PERCENT * 100:
            signal = "BUY"
            stop = None
        elif dist_resist <= RANGE_ENTRY_PERCENT * 100:
            signal = "SELL"
            stop = None

    elif trend == "DOWN":
        signal = None

    return signal, stop, dist_support, dist_resist
