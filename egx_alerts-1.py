print("EGX ALERTS - EMA120 Pullback Strategy")

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
        print("Telegram credentials not set")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(
            url,
            data={"chat_id": CHAT_ID, "text": text},
            timeout=10
        )
    except Exception as e:
        print("Telegram send failed:", e)

# =====================
# EGX symbols
# =====================
symbols = {
    "OFH":"OFH.CA","OLFI":"OLFI.CA","EMFD":"EMFD.CA","ETEL":"ETEL.CA",
    "EAST":"EAST.CA","EFIH":"EFIH.CA","ABUK":"ABUK.CA","OIH":"OIH.CA",
    "SWDY":"SWDY.CA","ISPH":"ISPH.CA","ATQA":"ATQA.CA","MTIE":"MTIE.CA",
    "ELEC":"ELEC.CA","HRHO":"HRHO.CA","ORWE":"ORWE.CA","JUFO":"JUFO.CA",
    "DSCW":"DSCW.CA","SUGR":"SUGR.CA","ELSH":"ELSH.CA","RMDA":"RMDA.CA",
    "RAYA":"RAYA.CA","EEII":"EEII.CA","MPCO":"MPCO.CA","GBCO":"GBCO.CA",
    "TMGH":"TMGH.CA","ORHD":"ORHD.CA","AMOC":"AMOC.CA","FWRY":"FWRY.CA",
    "COMI":"COMI.CA","ADIB":"ADIB.CA","PHDC":"PHDC.CA",
    "MCQE":"MCQE.CA","SKPC":"SKPC.CA","EGAL":"EGAL.CA"
}

# =====================
# Load last signals
# =====================
SIGNALS_FILE = "last_signals.json"

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
# Fetch Data
# =====================
def fetch_data(ticker):
    try:
        df = yf.download(
            ticker,
            period="6mo",
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=False
        )
        if df is None or df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except Exception as e:
        print("Data error:", ticker, e)
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
# Main Scan
# =====================
for name, ticker in symbols.items():
    time.sleep(0.8)
    df = fetch_data(ticker)
    if df is None or len(df) < 120:
        data_failures.append(name)
        continue

    last_candle_date = df.index[-1].date()
    close = df["Close"]
    low = df["Low"]

    # =====================
    # Indicators
    # =====================
    df["EMA120"] = close.ewm(span=120, adjust=False).mean()
    df["RSI14"] = rsi(close, 14)
    last = df.iloc[-1]
    prev_state = last_signals.get(name)

    # =====================
    # Strategy Conditions (UPDATED)
    # =====================
    ema_up = df["EMA120"].iloc[-1] > df["EMA120"].iloc[-15]
    price_ok = last["Close"] <= last["EMA120"] * 1.08
    trend_ok = (last["Close"] - last["EMA120"]) / last["EMA120"] > 0.03
    rsi_buy = 45 <= last["RSI14"] <= 60

    # تحسين الستوب (7 شموع)
    stop_loss = low.iloc[-8:-1].min()

    # ========================================
    # BUY لن يظهر إذا السعر أقل من الستوب لوس
    # ========================================
    buy_signal = ema_up and trend_ok and price_ok and rsi_buy and last["Close"] > stop_loss

    partial_sell = last["RSI14"] > 72
    full_sell = last["RSI14"] > 80
    stoploss_hit = last["Close"] < stop_loss
    in_trade = prev_state in ["BUY", "PARTIAL"]

    # =====================
    # Determine state
    # =====================
    if full_sell and in_trade:
        state = "SELL"
    elif partial_sell and in_trade:
        state = "PARTIAL"
    elif stoploss_hit and in_trade:
        state = "SELL"
    elif buy_signal:
        state = "BUY"
    else:
        continue

    # =====================
    # Prevent repeat signals
    # =====================
    if state != prev_state:
        if stoploss_hit and in_trade:
            break_pct = ((last["Close"] - stop_loss) / stop_loss) * 100
            alerts.append(
                f"🚨 STOP LOSS | {name}\n"
                f"Close: {last['Close']:.2f}\n"
                f"Stop Level: {stop_loss:.2f}\n"
                f"Break: {break_pct:.2f}%\n"
                f"RSI: {last['RSI14']:.1f}\n"
                f"Date: {last_candle_date}"
            )
        elif state == "BUY":
            alerts.append(
                f"🟢 BUY | {name}\n"
                f"Price: {last['Close']:.2f}\n"
                f"Stop: {stop_loss:.2f}\n"
                f"RSI: {last['RSI14']:.1f}\n"
                f"Date: {last_candle_date}"
            )
        elif state == "PARTIAL":
            alerts.append(
                f"🟡 PARTIAL SELL | {name}\n"
                f"Price: {last['Close']:.2f}\n"
                f"RSI: {last['RSI14']:.1f}\n"
                f"Date: {last_candle_date}"
            )
        elif state == "SELL":
            alerts.append(
                f"🔴 FULL SELL | {name}\n"
                f"Price: {last['Close']:.2f}\n"
                f"RSI: {last['RSI14']:.1f}\n"
                f"Date: {last_candle_date}"
            )
        new_signals[name] = state

# =====================
# Save Signals
# =====================
with open(SIGNALS_FILE, "w") as f:
    json.dump(new_signals, f)

# =====================
# Telegram Output
# =====================
if alerts:
    send_telegram(
        "📊 EGX EMA120 Pullback Signals\n\n" +
        "\n\n".join(alerts)
    )
else:
    send_telegram(
        f"ℹ️ No new signals\nLast candle: {last_candle_date}"
    )

if data_failures:
    send_telegram(
        "⚠️ Failed to fetch data:\n" +
        ", ".join(data_failures)
    )
