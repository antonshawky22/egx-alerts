print("EGX ALERTS - EMA120 Pullback Strategy")

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
# Main Scan
# =====================
for name, ticker in symbols.items():

    df = fetch_data(ticker)

    if df is None or len(df) < 150:
        data_failures.append(name)
        continue

    last_candle_date = df.index[-1].date()

    close = df["Close"]
    low = df["Low"]

    df["EMA120"] = ema(close, 120)
    df["RSI14"] = rsi(close, 14)

    last = df.iloc[-1]

    prev_state = last_signals.get(name)

    # =====================
    # Trend condition
    # =====================
    ema_slope_up = last["EMA120"] > df["EMA120"].iloc[-6]

    # =====================
    # Price not far from EMA
    # =====================
    price_not_far = last["Close"] <= last["EMA120"] * 1.12

    # =====================
    # RSI buy zone
    # =====================
    rsi_buy_zone = 27 <= last["RSI14"] <= 40

    # =====================
    # BUY
    # =====================
    buy_signal = (
        ema_slope_up and
        price_not_far and
        rsi_buy_zone
    )

    # =====================
    # SELL PARTIAL
    # =====================
    sell_partial = last["RSI14"] > 70

    # =====================
    # SELL FULL
    # =====================
    sell_full = last["RSI14"] > 83

    # =====================
    # Stop loss
    # =====================
    stop_loss = low.iloc[-6:-1].min()

    if buy_signal:
        curr_state = "BUY"

    elif sell_full:
        curr_state = "SELL"

    elif sell_partial:
        curr_state = "PARTIAL"

    else:
        continue

    if curr_state != prev_state:

        if curr_state == "BUY":

            alerts.append(
                f"🟢 BUY | {name}\n"
                f"Price: {last['Close']:.2f}\n"
                f"Stop: {stop_loss:.2f}\n"
                f"RSI: {last['RSI14']:.1f}\n"
                f"Date: {last_candle_date}"
            )

        elif curr_state == "PARTIAL":

            alerts.append(
                f"🟡 PARTIAL SELL | {name}\n"
                f": {last['Close']:.2f}\n"
                f": {last['RSI14']:.1f}\n"
                f": {last_candle_date}"
            )

        elif curr_state == "SELL":

            alerts.append(
                f"🔴 FULL SELL | {name}\n"
                f": {last['Close']:.2f}\n"
                f"RSI: {last['RSI14']:.1f}\n"
                f": {last_candle_date}"
            )

        new_signals[name] = curr_state


# =====================
# Data failure alert
# =====================
if data_failures:
    send_telegram(
        "⚠️ Failed to load data:\n" + ", ".join(data_failures)
    )

# =====================
# Save signals
# =====================
with open(SIGNALS_FILE, "w") as f:
    json.dump(new_signals, f)

# =====================
# Telegram output
# =====================
if alerts:

    send_telegram(
        "🚨 EGX EMA120 Pullback Signals\n\n" +
        "\n\n".join(alerts)
    )

else:

    send_telegram(
        "ℹ️ No new signals\n\n"
        f"Last candle:\n📅 {last_candle_date}"
    )
