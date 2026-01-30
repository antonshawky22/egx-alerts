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
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except:
        return None

# =====================
# Main Logic
# =====================
results = []
last_candle_date = None

for name, ticker in symbols.items():
    df = fetch_data(ticker)
    if df is None or len(df) < 30:
        results.append(f"⚠️ {name} | NO DATA")
        continue

    last_candle_date = df.index[-1].date()

    close = df["Close"]

    df["EMA4"]  = ema(close, 4)
    df["EMA9"]  = ema(close, 9)
    df["EMA25"] = ema(close, 25)

    # ===== Explicit last values (IMPORTANT) =====
    ema4  = df["EMA4"].iloc[-1]
    ema9  = df["EMA9"].iloc[-1]
    ema25 = df["EMA25"].iloc[-1]
    price = df["Close"].iloc[-1]

    # =====================
    # STATE LOGIC (TEST)
    # =====================
    if ema4 > ema9 and price > ema25:
        state = "🟢 BUY"
    elif ema4 < ema9 and price < ema25:
        state = "🔴 SELL"
    else:
        state = "⚪ HOLD"

    results.append(
        f"{state} | {name} | {price:.2f}"
    )

# =====================
# Telegram output
# =====================
send_telegram(
    "🧪 MA TEST MODE (SHOW ALL STATES)\n\n"
    + "\n".join(results)
    + f"\n\n📅 Last candle date: {last_candle_date}"
)
