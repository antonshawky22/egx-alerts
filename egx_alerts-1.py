print("EGX LADDER CYCLE SYSTEM - PRO (Smart Stop Loss)")

import yfinance as yf
import requests
import os
import json
import pandas as pd
import time

#=====================

Telegram settings

#=====================

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

#=====================

Symbols

#=====================

symbols = {
"COMI": "COMI.CA",
"HRHO": "HRHO.CA",
"FWRY": "FWRY.CA",
"EFIH": "EFIH.CA",
"TMGH": "TMGH.CA"
}

STATE_FILE = "last_signals.json"

#=====================

Load state

#=====================

try:
with open(STATE_FILE, "r") as f:
state_data = json.load(f)
except:
state_data = {}

#=====================

Fetch Data

#=====================

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

#=====================

RSI

#=====================

def rsi(series, period=14):
delta = series.diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)

avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()

rs = avg_gain / avg_loss
return 100 - (100 / (1 + rs))

#=====================

Weighted Average

#=====================

def update_avg(old_avg, old_pos, new_price, new_pos):
added_pos = new_pos - old_pos
total_cost = (old_avg * old_pos) + (new_price * added_pos)
return total_cost / new_pos

#=====================

Format Alert

#=====================

def format_alert(title, name, price, position, avg, rsi, cycle, profit):
return (
f"{title} | {name}\n\n"
f"💰 Price: {price:.2f}\n"
f"📊 Position: {position*100:.0f}%\n"
f"📉 Avg: {avg:.2f}\n\n"
f"📈 RSI: {rsi:.1f}\n"
f"🔁 Cycle: {cycle}\n"
f"💵 P/L: {profit:.2f}%"
)

#=====================

MAIN LOOP

#=====================

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

# Init state
if name not in state_data:
    state_data[name] = {
        "cycle": 1,
        "position": 0.0,
        "avg_price": 0.0,
        "peak_profit": 0.0
    }

s = state_data[name]

# Trend
ema_up = df["EMA120"].iloc[-1] > df["EMA120"].iloc[-15]

# Buy
buy1 = ema_up and rsi_val <= 55
buy2 = ema_up and rsi_val <= 45
buy3 = ema_up and rsi_val <= 40

# Sell
sell1 = rsi_val >= 65
sell2 = rsi_val >= 72
sell3 = rsi_val >= 78

action = None

# =====================
# BUY
# =====================

if s["position"] == 0 and buy1:
    s["position"] = 0.33
    s["avg_price"] = price
    s["peak_profit"] = 0
    action = "🟢 BUY L1"

elif 0.32 < s["position"] < 0.5 and buy2:
    old_pos = s["position"]
    s["position"] = 0.66
    s["avg_price"] = update_avg(s["avg_price"], old_pos, price, s["position"])
    action = "🟢 BUY L2"

elif 0.65 < s["position"] < 1 and buy3:
    old_pos = s["position"]
    s["position"] = 1.0
    s["avg_price"] = update_avg(s["avg_price"], old_pos, price, s["position"])
    action = "🟢 BUY L3"

# =====================
# PROFIT
# =====================

profit = 0
if s["avg_price"] > 0:
    profit = ((price - s["avg_price"]) / s["avg_price"]) * 100

if profit > s["peak_profit"]:
    s["peak_profit"] = profit

# =====================
# STOP + SELL (FIXED ORDER)
# =====================

if s["position"] > 0:

    stop_triggered = False

    # Loss Stop
    if s["position"] <= 0.33 and profit <= -5:
        stop_triggered = True
    elif s["position"] <= 0.66 and profit <= -4:
        stop_triggered = True
    elif s["position"] == 1.0 and profit <= -3:
        stop_triggered = True

    # Trailing Stop
    if s["peak_profit"] > 2 and (s["peak_profit"] - profit) >= 3:
        stop_triggered = True

    if stop_triggered:
        action = "🛑 STOP LOSS"
        s["position"] = 0
        s["avg_price"] = 0
        s["peak_profit"] = 0
        s["cycle"] += 1

    # ✅ البيع بالترتيب الصحيح
    elif sell3:
        action = "🚨 EXIT FULL"
        s["position"] = 0
        s["avg_price"] = 0
        s["cycle"] += 1

    elif sell2:
        sell_amount = min(0.66, s["position"])
        s["position"] -= sell_amount
        action = "🔴 SELL L2 (66%)"

    elif sell1:
        sell_amount = min(0.33, s["position"])
        s["position"] -= sell_amount
        action = "🔴 SELL L1 (33%)"

# =====================
# ALERT
# =====================

if action:
    alerts.append(
        format_alert(action, name, price, s["position"], s["avg_price"], rsi_val, s["cycle"], profit)
    )

#=====================

SAVE

#=====================

with open(STATE_FILE, "w") as f:
json.dump(state_data, f)

#=====================

SEND

#=====================

if alerts:
send_telegram("\n\n----------------------\n\n".join(alerts))
else:
send_telegram("😴 No new signals")
