print("EGX ALERTS - MA Strategy (4 / 9 / 25) - RELAXED MODE + FAST SELL")

import yfinance as yf
import requests
import os
import json
import pandas as pd

# =====================
# Telegram settings
# =====================
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram(text):
    if not TOKEN or not CHAT_ID:
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
    "OFH": "OFH.CA","OLFI": "OLFI.CA","EMFD": "EMFD.CA","ETEL": "ETEL.CA",
    "EAST": "EAST.CA","EFIH": "EFIH.CA","ABUK": "ABUK.CA","OIH": "OIH.CA",
    "SWDY": "SWDY.CA","ISPH": "ISPH.CA","ATQA": "ATQA.CA","MTIE": "MTIE.CA",
    "ELEC": "ELEC.CA","HRHO": "HRHO.CA","ORWE": "ORWE.CA","JUFO": "JUFO.CA",
    "DSCW": "DSCW.CA","SUGR": "SUGR.CA","ELSH": "ELSH.CA","RMDA": "RMDA.CA",
    "RAYA": "RAYA.CA","EEII": "EEII.CA","MPCO": "MPCO.CA","GBCO": "GBCO.CA",
    "TMGH": "TMGH.CA","ORHD": "ORHD.CA","AMOC": "AMOC.CA","FWRY": "FWRY.CA",
    "COMI": "COMI.CA","ADIB": "ADIB.CA","PHDC": "PHDC.CA",
    "EGTS": "EGTS.CA","MCQE": "MCQE.CA","SKPC": "SKPC.CA",
    "EGAL": "EGAL.CA"
}

# =====================
# Load last signals
# =====================
SIGNALS_FILE = "last_signals_ma4.json"

try:
    with open(SIGNALS_FILE, "r") as f:
        last_signals = json.load(f)
except:
    last_signals = {}

new_signals = last_signals.copy()
alerts = []
data_failures = []
last_candle_date = None

# =====================
# Helpers
# =====================
def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

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
    except:
        return None

# =====================
# Main Logic
# =====================
for name, ticker in symbols.items():
    df = fetch_data(ticker)
    if df is None or len(df) < 30:
        data_failures.append(name)
        continue

    last_candle_date = df.index[-1].date()
    close = df["Close"]
    open_ = df["Open"]
    body = abs(close - open_)

    df["EMA2"]  = ema(close, 2)
    df["EMA3"]  = ema(close, 3)
    df["EMA4"]  = ema(close, 4)
    df["EMA5"]  = ema(close, 5)
    df["EMA9"]  = ema(close, 9)
    df["EMA25"] = ema(close, 25)
    df["RSI14"] = rsi(close, 14)

    last = df.iloc[-1]
    prev = df.iloc[-2]

    # ===== Large candle filter - بسيط =====
    avg_body = body.iloc[-11:-1].mean()
    large_candle = body.iloc[-1] > (3 * avg_body)  # خفيف جدا، لا يمنع الإشارة

    prev_state = last_signals.get(name)

    # =====================
    # BUY - EMA 4 & 9 & 25
    # =====================
    buy_signal = (
        last["EMA4"] > last["EMA9"] and
        prev["EMA4"] <= prev["EMA9"] and
        last["Close"] > last["EMA25"] and
        last["EMA25"] >= prev["EMA25"]
    )

    # =====================
    # SELL - FAST EMA 3 & 5 OR RSI14 ≥ 80
    # =====================
    sell_signal = (
        (last["EMA3"] < last["EMA5"] and prev["EMA3"] >= prev["EMA5"]) or
        (last["RSI14"] >= 80)
    )

    # =====================
    # Append alert فقط لو BUY أو SELL
    # =====================
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
            f"Date: {last_candle_date}"
        )
        new_signals[name] = curr_state

# =====================
# Data failure alert
# =====================
if data_failures:
    send_telegram("⚠️ فشل تحميل بيانات لبعض الأسهم:\n" + ", ".join(data_failures))

# =====================
# Save signals
# =====================
with open(SIGNALS_FILE, "w") as f:
    json.dump(new_signals, f)

# =====================
# Telegram output
# =====================
if alerts:
    send_telegram("🚨 EGX MA Strategy Signals (RELAXED + FAST SELL):\n\n" + "\n\n".join(alerts))
else:
    send_telegram(
        "ℹ️ لا توجد إشارات جديدة\n\n"
        f"last candle date:\n📅 {last_candle_date}"
    )
