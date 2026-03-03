print("EGX ALERTS - Pre-Breakout Strategy")

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
        print("Telegram credentials not set")
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
data_failures = []
last_candle_date = None

# =====================
# Helpers
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
# Pre-Breakout Strategy Logic
# =====================
LOOKBACK = 30
BREAKOUT_WINDOW = 20
VOLUME_MULTIPLIER = 1.2

section_buy = []
section_sell = []

for name, ticker in symbols.items():
    df = fetch_data(ticker)
    if df is None or len(df) < LOOKBACK:
        data_failures.append(name)
        continue

    last_candle_date = df.index[-1].date()
    close = df['Close']
    high = df['High']
    low = df['Low']
    volume = df['Volume']

    # =====================
    # Compute rolling levels
    # =====================
    highest_high = high.rolling(BREAKOUT_WINDOW).max()
    lowest_low = low.rolling(BREAKOUT_WINDOW).min()
    vol_avg5 = volume.rolling(5).mean()
    vol_avg20 = volume.rolling(20).mean()

    last_price = close.iloc[-1]
    last_high = highest_high.iloc[-1]
    last_low = lowest_low.iloc[-1]
    last_vol5 = vol_avg5.iloc[-1]
    last_vol20 = vol_avg20.iloc[-1]

    # =====================
    # Pre-Breakout conditions
    # =====================
    breakout_range = (last_high - last_low) / last_low < 0.10  # تذبذب أقل من 10%
    breakout_price = last_price >= 0.97 * last_high         # قرب اختراق القمة
    breakout_volume = last_vol5 > VOLUME_MULTIPLIER * last_vol20  # زيادة حجم التداول

    if breakout_range and breakout_price and breakout_volume:
        section_buy.append(f"🟢 BUY | {name} | {last_price:.2f} | {last_candle_date}")
        new_signals[name] = {"signal": "BUY", "price": float(last_price)}
    elif last_price < lowest_low.iloc[-15]:  # Stop loss / حركة هبوط
        section_sell.append(f"🔴 SELL | {name} | {last_price:.2f} | {last_candle_date}")
        new_signals[name] = {"signal": "SELL", "price": float(last_price)}

# =====================
# Compile Message
# =====================
alerts = ["🚦 EGX Pre-Breakout Signals:\n"]

if section_buy:
    alerts.append("↗️ احتمالية صعود (Pre-Breakout):")
    alerts.extend(["- " + s for s in section_buy])
if section_sell:
    alerts.append("\n🔻 هبوط:")
    alerts.extend(["- " + s for s in section_sell])

if not section_buy and not section_sell:
    alerts.append(f"ℹ️ لا توجد إشارات جديدة\nlast candle: {last_candle_date}")

if data_failures:
    alerts.append("\n⚠️ فشل تحميل البيانات:\n- " + "\n- ".join(data_failures))

# =====================
# Save & Notify
# =====================
with open(SIGNALS_FILE, "w") as f:
    json.dump(new_signals, f, indent=2, ensure_ascii=False)

send_telegram("\n".join(alerts))
