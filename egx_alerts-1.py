print("EGX ALERTS - Pre-Breakout (Final Stable State Machine)")

import yfinance as yf
import requests
import os
import json
import pandas as pd

# =====================
# Telegram
# =====================
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram(text):
    if not TOKEN or not CHAT_ID:
        print("Telegram credentials not set")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": text}, timeout=10)
    except Exception as e:
        print("Telegram error:", e)

# =====================
# FULL EGX SYMBOL LIST
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

# =====================
# Strategy parameters
# =====================
LOOKBACK = 35
BREAKOUT_WINDOW = 22
STOP_LOOKBACK = 15

section_buy = []
section_sell = []
data_failures = []
last_candle_date = None

# =====================
# Fetch data
# =====================
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

# =====================
# MAIN LOOP
# =====================
for name, ticker in symbols.items():

    df = fetch_data(ticker)
    if df is None or len(df) < LOOKBACK:
        data_failures.append(name)
        continue

    last_candle_date = df.index[-1].date()

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    last_price = close.iloc[-1]

    # ===== Indicators =====
    highest_high = high.rolling(BREAKOUT_WINDOW).max()
    lowest_low = low.rolling(BREAKOUT_WINDOW).min()

    stop_loss = low.rolling(STOP_LOOKBACK).min().iloc[-1]

    rsi14 = 100 - (100 / (1 + ((close.diff().clip(lower=0).rolling(14).mean()) /
                               (close.diff().clip(upper=0).abs().rolling(14).mean()))))

    ema3 = close.ewm(span=3, adjust=False).mean()

    last_high = highest_high.iloc[-1]
    last_low = lowest_low.iloc[-1]

    # =====================
    # Calculate CURRENT signal
    # =====================
    current_signal = None

    # ---- BUY ----
    breakout_range = (last_high - last_low) / last_low < 0.50
    breakout_price = last_price >= 0.50 * last_high

    if breakout_range and breakout_price:
        current_signal = "BUY"

    # ---- SELL ----
    rsi_val = rsi14.iloc[-1]
    ema_val = ema3.iloc[-1]

    if not pd.isna(rsi_val) and not pd.isna(ema_val):
        if (last_price <= stop_loss) or (rsi_val >= 80) or (last_price < ema_val):
            current_signal = "SELL"

    # =====================
    # Compare with previous state
    # =====================
    prev_data = last_signals.get(name, {})
    prev_signal = prev_data.get("signal")

    if current_signal == prev_signal:
        continue

    if current_signal == "BUY":
        section_buy.append(
            f"🟢 BUY | {name} | {last_price:.2f} | {last_candle_date}"
        )
        new_signals[name] = {
            "signal": "BUY",
            "price": float(last_price),
            "stop_loss": float(stop_loss)
        }

    elif current_signal == "SELL":
        section_sell.append(
            f"🔴 SELL | {name} | {last_price:.2f} | {last_candle_date}"
        )
        new_signals[name] = {
            "signal": "SELL",
            "price": float(last_price)
        }

# =====================
# Build message
# =====================
alerts = ["🚦 EGX Signals:\n"]

if section_buy:
    alerts.append("↗️ BUY:")
    alerts.extend(["- " + s for s in section_buy])

if section_sell:
    alerts.append("\n🔻 SELL:")
    alerts.extend(["- " + s for s in section_sell])

if not section_buy and not section_sell:
    alerts.append(f"ℹ️ No new signal | Last candle: {last_candle_date}")

if data_failures:
    alerts.append("\n⚠️ Failed to fetch data:")
    alerts.extend(["- " + s for s in data_failures])

# =====================
# Save state
# =====================
with open(SIGNALS_FILE, "w") as f:
    json.dump(new_signals, f, indent=2, ensure_ascii=False)

send_telegram("\n".join(alerts))
