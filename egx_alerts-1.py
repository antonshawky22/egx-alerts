print("EGX LADDER CYCLE SYSTEM - PROFESSIONAL v2.0")

import yfinance as yf
import requests
import os
import json
import pandas as pd
import time

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

symbols = {
    "COMI": "COMI.CA",
    "HRHO": "HRHO.CA",
    "FWRY": "FWRY.CA",
    "EFIH": "EFIH.CA",
    "TMGH": "TMGH.CA"
}

STATE_FILE = "last_signals.json"

try:
    with open(STATE_FILE, "r") as f:
        state_data = json.load(f)
except:
    state_data = {}

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

def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def update_avg(old_avg, old_pos, new_price, new_pos):
    if new_pos <= 0:
        return 0
    added_pos = new_pos - old_pos
    if added_pos <= 0:
        return old_avg # البيع لا يغير متوسط سعر الشراء للكمية المتبقية
    total_cost = (old_avg * old_pos) + (new_price * added_pos)
    return float(total_cost / new_pos)

def format_alert(title, name, price, position, avg, rsi_val, cycle, profit):
    return (
        f"{title} | {name}\n\n"
        f"💰 Price: {price:.2f}\n"
        f"📊 Position: {position*100:.0f}%\n"
        f"📉 Avg Cost: {avg:.2f}\n\n"
        f"📈 RSI: {rsi_val:.1f}\n"
        f"🔁 Cycle: {cycle}\n"
        f"💵 P/L: {profit:.2f}%"
    )

alerts = []

for name, ticker in symbols.items():
    time.sleep(1) # زيادة المهلة لتجنب الحظر من ياهو

    df = fetch_data(ticker)
    if df is None or len(df) < 120:
        continue

    close = df["Close"].dropna()
    df["EMA120"] = close.ewm(span=120, adjust=False).mean()
    df["RSI"] = rsi(close)

    last = df.iloc[-1]
    price = float(last["Close"])
    rsi_val = float(last["RSI"])

    if pd.isna(rsi_val):
        continue

    if name not in state_data:
        state_data[name] = {
            "cycle": 1,
            "position": 0.0,
            "avg_price": 0.0,
            "peak_profit": 0.0
        }

    s = state_data[name]
    
    # تحديد الاتجاه الصاعد (إغلاق فوق المتوسط، والمؤشر يتصاعد)
    ema_up = df["EMA120"].iloc[-1] > df["EMA120"].iloc[-15] and price > df["EMA120"].iloc[-1]

    # شروط السلم المحددة والمفصولة لمنع التداخل الفوري
    buy1 = ema_up and (rsi_val <= 55)
    buy2 = ema_up and (rsi_val <= 45)
    buy3 = ema_up and (rsi_val <= 38)

    profit = 0.0
    if s["avg_price"] > 0:
        profit = ((price - s["avg_price"]) / s["avg_price"]) * 100

    sell1 = rsi_val >= 65 and profit > 2.0
    sell2 = rsi_val >= 72 and profit > 4.0
    sell3 = rsi_val >= 78 and profit > 6.0

    action = None

    # --- منطق الشراء (السلم الصاعد) ---
    if s["position"] == 0 and buy1:
        s["position"] = 0.33
        s["avg_price"] = price
        s["peak_profit"] = 0.0
        action = "🟢 BUY L1 (33%)"

    elif 0.30 <= s["position"] < 0.50 and buy2 and price < s["avg_price"]:
        # شرط إضافي: الشراء للمستوى الثاني يكون بسعر أقل من الشراء الأول لضمان التبريد
        old_pos = s["position"]
        s["position"] = 0.66
        s["avg_price"] = update_avg(s["avg_price"], old_pos, price, s["position"])
        action = "🟢 BUY L2 (66%)"

    elif 0.60 <= s["position"] < 0.90 and buy3 and price < s["avg_price"]:
        old_pos = s["position"]
        s["position"] = 1.0
        s["avg_price"] = update_avg(s["avg_price"], old_pos, price, s["position"])
        action = "🟢 BUY L3 (100%)"

    if profit > s["peak_profit"]:
        s["peak_profit"] = profit

    # --- منطق البيع وإدارة المخاطر ---
    if s["position"] > 0:
        stop_triggered = False

        # وقف خسارة مرن يعتمد على حجم المحفظة المخاطر بها
        if s["position"] <= 0.35 and profit <= -5.0:
            stop_triggered = True
        elif s["position"] <= 0.70 and profit <= -4.0:
            stop_triggered = True
        elif s["position"] > 0.70 and profit <= -3.0:
            stop_triggered = True

        # الوقف المتحرك لحماية الأرباح (Trailing Stop)
        if s["peak_profit"] > 3.0 and (s["peak_profit"] - profit) >= 2.5:
            stop_triggered = True

        if stop_triggered:
            action = "🛑 STOP LOSS"
            s["position"] = 0.0
            s["avg_price"] = 0.0
            s["peak_profit"] = 0.0
            s["cycle"] += 1

        elif sell3 or (rsi_val >= 80):
            action = "🚨 EXIT FULL"
            s["position"] = 0.0
            s["avg_price"] = 0.0
            s["peak_profit"] = 0.0
            s["cycle"] += 1

        elif sell2 and s["position"] >= 0.66:
            s["position"] -= 0.33
            # لا نغير s["avg_price"] هنا لأنه بيع جزئي
            action = "🔴 SELL L2 (33%)"

        elif sell1 and s["position"] >= 0.33:
            s["position"] -= 0.33
            action = "🔴 SELL L1 (33%)"

        s["position"] = round(s["position"], 2)
        if s["position"] == 0:
            s["avg_price"] = 0.0
            s["peak_profit"] = 0.0

    if action:
        alerts.append(
            format_alert(
                action, name, price, s["position"], s["avg_price"], rsi_val, s["cycle"], profit
            )
        )

with open(STATE_FILE, "w") as f:
    json.dump(state_data, f, indent=4)

if alerts:
    send_telegram("\n\n----------------------\n\n".join(alerts))
else:
    print("😴 No new signals")
