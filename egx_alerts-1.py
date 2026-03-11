import yfinance as yf
import requests
import os
import json
import pandas as pd
from datetime import datetime, timedelta

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
# Signals file
# =====================
SIGNALS_FILE = "last_signals.json"
try:
    with open(SIGNALS_FILE, "r") as f:
        last_signals = json.load(f)
except:
    last_signals = {}

new_signals = {}
data_failures = []

# =====================
# Strategy parameters for experiment
# =====================
EMA_PERIOD = 20      # لتجربة أسرع
RSI_PERIOD = 14
RSI_BUY_LOW = 40     # وسعنا منطقة الشراء
RSI_BUY_HIGH = 60
PRICE_ABOVE_EMA_MAX = 0.20  # السماح للسعر أعلى EMA

# =====================
# Functions
# =====================
def EMA(series, period):
    return series.ewm(span=period, adjust=False).mean()

def RSI(series, period):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# =====================
# Main loop – check last 5 days for experiment
# =====================
for symbol, ticker in symbols.items():
    try:
        data = yf.download(ticker, period="6mo", interval="1d")
        if data.empty:
            data_failures.append(symbol)
            continue
        
        data['EMA'] = EMA(data['Close'], EMA_PERIOD)
        data['RSI'] = RSI(data['Close'], RSI_PERIOD)
        
        for i in range(-5, 0):  # آخر 5 أيام
            price = data['Close'].iloc[i]
            rsi_now = data['RSI'].iloc[i]
            stop_loss = data['Close'].iloc[i-5:i].min()  # أقل قاع 5 أيام
            
            if RSI_BUY_LOW <= rsi_now <= RSI_BUY_HIGH:
                if symbol not in last_signals or last_signals[symbol]['date'] != str(data.index[i].date()):
                    new_signals[symbol] = {
                        "price": round(price,2),
                        "stop_loss": round(stop_loss,2),
                        "date": str(data.index[i].date())
                    }
                    break  # إشارة واحدة كافية لكل سهم

    except Exception as e:
        data_failures.append(symbol)
        print(f"Failed for {symbol}: {e}")

# =====================
# Prepare Telegram message
# =====================
if new_signals:
    msg_lines = []
    for sym, info in new_signals.items():
        line = f"🟢 {sym} | {info['price']} | {info['date']}  🚨 StopLoss: {info['stop_loss']}"
        msg_lines.append(line)
    message = "\n".join(msg_lines)
else:
    message = f"No new signal – last 5 days checked"

send_telegram(message)

# =====================
# Save last signals
# =====================
last_signals.update(new_signals)
with open(SIGNALS_FILE, "w") as f:
    json.dump(last_signals, f, indent=2)

# =====================
# Data failures report
# =====================
if data_failures:
    print("Data fetch failed for:", ", ".join(data_failures))
