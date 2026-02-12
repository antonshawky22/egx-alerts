print("EGX TREND CLASSIFIER - TEST MODE (15 STOCKS)")

import yfinance as yf
import requests
import os
import pandas as pd

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
# Selected 15 Stocks Only
# =====================
symbols = {
    # 🟢 From List A
    "ETEL": "ETEL.CA",
    "COMI": "COMI.CA",
    "FWRY": "FWRY.CA",
    "TMGH": "TMGH.CA",
    "SWDY": "SWDY.CA",

    # 🟡 From List B
    "EAST": "EAST.CA",
    "AMOC": "AMOC.CA",
    "OLFI": "OLFI.CA",
    "PHDC": "PHDC.CA",
    "ISPH": "ISPH.CA",

    # 🔴 From List C
    "BLTN": "BLTN.CA",
    "TAQA": "TAQA.CA",
    "CAED": "CAED.CA",
    "ACTF": "ACTF.CA",
    "ELSH": "ELSH.CA"
}

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
# Trend Classification Logic
# =====================
def classify_trend(last):
    if last["Close"] > last["EMA75"]:
        if last["EMA6"] > last["EMA10"]:
            return "🟢 UP"
        else:
            return "🟡 UP (weak)"
    elif last["Close"] < last["EMA75"]:
        if last["EMA6"] < last["EMA10"]:
            return "🔴 DOWN"
        else:
            return "🟡 DOWN (weak)"
    else:
        return "🟡 SIDEWAYS"

# =====================
# Main Execution
# =====================
report_lines = []
last_candle_date = None

for name, ticker in symbols.items():
    df = fetch_data(ticker)

    if df is None or len(df) < 100:
        report_lines.append(f"{name} ❌ Data Error")
        continue

    close = df["Close"]

    df["EMA6"] = ema(close, 6)
    df["EMA10"] = ema(close, 10)
    df["EMA75"] = ema(close, 75)
    df["RSI14"] = rsi(close, 14)

    last = df.iloc[-1]
    last_candle_date = df.index[-1].date()

    trend = classify_trend(last)

    report_lines.append(
        f"{trend} | {name}\n"
        f"Close: {last['Close']:.2f}\n"
        f"EMA6: {last['EMA6']:.2f}\n"
        f"EMA10: {last['EMA10']:.2f}\n"
        f"EMA75: {last['EMA75']:.2f}\n"
        f"RSI14: {last['RSI14']:.2f}\n"
    )

# =====================
# Send Report
# =====================
if report_lines:
    send_telegram(
        "📊 EGX Trend Classification Report\n\n"
        + "\n".join(report_lines)
        + f"\n📅 Last Candle: {last_candle_date}"
    )
else:
    send_telegram("⚠️ No Data")
