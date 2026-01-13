print("EGX ALERTS - DAILY SWING TRADING (MULTI-DAY MODE)")

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
        print("Telegram ENV missing")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": text})

# =====================
# EGX symbols
# =====================
symbols = {
    "OFH": "OFH.CA","OLFI": "OLFI.CA","EMFD": "EMFD.CA","ETEL": "ETEL.CA",
    "EAST": "EAST.CA","OIH": "OIH.CA","HRHO": "HRHO.CA","ORWE": "ORWE.CA",
    "JUFO": "JUFO.CA","DSCW": "DSCW.CA","SUGR": "SUGR.CA",
    "ELSH": "ELSH.CA","RMDA": "RMDA.CA","FWRY": "FWRY.CA"
}

alerts = []
data_failures = []

# =====================
# PRICE FETCH
# =====================
def fetch_yfinance(ticker):
    try:
        df = yf.download(ticker, period="6mo", interval="1d", progress=False)
        if df is None or df.empty or "Close" not in df:
            return None
        return df
    except Exception:
        return None

def fetch_stooq(ticker):
    try:
        symbol = ticker.replace(".CA", "")
        url = f"https://stooq.com/q/d/l/?s={symbol}&i=d"
        df = pd.read_csv(url)
        if df is None or df.empty or "Close" not in df:
            return None
        df["Date"] = pd.to_datetime(df["Date"])
        df.set_index("Date", inplace=True)
        return df
    except Exception:
        return None

def get_price_data(ticker):
    df = fetch_yfinance(ticker)
    if df is not None:
        return df
    return fetch_stooq(ticker)

# =====================
# Logic (SWING TRADING)
# =====================
for name, ticker in symbols.items():
    data = get_price_data(ticker)

    if data is None or len(data) < 60:
        data_failures.append(name)
        continue

    close = data["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    close = close.astype(float)

    # EMA
    ema10 = close.ewm(span=10, adjust=False).mean()
    ema20 = close.ewm(span=20, adjust=False).mean()

    # RSI Wilder + light smoothing
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.ewm(span=3, adjust=False).mean()

    # Last values
    price_last = float(close.iloc[-1])
    rsi_last = float(rsi.iloc[-1])
    ema10_last = float(ema10.iloc[-1])
    ema20_last = float(ema20.iloc[-1])

    # =====================
    # 🟢 BUY (Swing Entry)
    # =====================
    if (
        32 <= rsi_last <= 42 and
        price_last >= ema10_last * 0.99 and
        ema10_last <= ema20_last * 1.02
    ):
        alerts.append(
            f"🟢 شراء سوينج: {name} | RSI={round(rsi_last,1)}"
        )

    # =====================
    # 📉 SELL (Swing Exit)
    # =====================
    if (
        rsi_last >= 60 or
        price_last < ema20_last
    ):
        alerts.append(
            f"📉 بيع سوينج: {name} | RSI={round(rsi_last,1)}"
        )

# =====================
# Send alerts
# =====================
if alerts:
    send_telegram("🚨 تنبيهات سوينج (عدة أيام):\n\n" + "\n".join(alerts))
else:
    send_telegram("ℹ️ لا توجد فرص سوينج حالياً")

if data_failures:
    send_telegram(
        "⚠️ تحذير مصدر أسعار:\nفشل جلب البيانات للأسهم:\n" +
        ", ".join(data_failures)
    )
