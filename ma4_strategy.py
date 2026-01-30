print("EGX ALERTS - MA TEST MODE (SHOW ALL STATES)")

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
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": text}, timeout=10)
    except:
        pass

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
# Helpers
# =====================
def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

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
        return df
    except:
        return None

# =====================
# Main Logic
# =====================
alerts = []

for name, ticker in symbols.items():
    df = fetch_data(ticker)
    if df is None or len(df) < 30:
        continue

    close = df["Close"]

    df["EMA4"]  = ema(close, 4)
    df["EMA9"]  = ema(close, 9)
    df["EMA25"] = ema(close, 25)

    last = df.iloc[-1]

    if (
    df["EMA4"].iloc[-1] > df["EMA9"].iloc[-1]
    and df["Close"].iloc[-1] > df["EMA25"].iloc[-1]
    )
        state = "🟢 BUY"
    else:
        state = "🔴 SELL"

    alerts.append(
        f"{state} | {name}\n"
        f"Price: {last['Close']:.2f}\n"
        f"Date: {df.index[-1].date()}"
    )

# =====================
# Telegram output
# =====================
send_telegram(
    "🧪 TEST MODE – ALL STOCK STATES\n\n" +
    "\n\n".join(alerts)
)
