import os
import requests
import yfinance as yf
EGX_TICKERS = [
    "COMI.CA", "CIB.CA", "ETEL.CA", "EFG.CA", "EAST.CA",
    "SWDY.CA", "TALM.CA", "AMOC.CA", "ESRS.CA", "ORWE.CA",
    "PHDC.CA", "MNHD.CA", "HELI.CA", "SKPC.CA", "JUFO.CA",
    "ISPH.CA", "BTFH.CA", "SAUD.CA", "ARAB.CA", "CCRS.CA",
    "OLFI.CA", "AUTO.CA", "FWRY.CA", "ADIB.CA", "ABUK.CA",
    "ORAS.CA", "CLHO.CA", "HRHO.CA", "KABO.CA", "DSCW.CA"
]
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TOKEN or not CHAT_ID:
    raise Exception("Missing Telegram credentials")

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

message += "\n📊 EGX Watchlist (30)\n\n"

for ticker in EGX_TICKERS:
    try:
        data = yf.Ticker(ticker).history(period="1d")
        if not data.empty:
            close_price = round(data["Close"].iloc[-1], 2)
            message += f"{ticker.replace('.CA','')}: {close_price}\n"
        else:
            message += f"{ticker.replace('.CA','')}: N/A\n"
    except Exception:
        message += f"{ticker.replace('.CA','')}: ERROR\n"
payload = {
    "chat_id": CHAT_ID,
    "text": message
}

r = requests.post(url, json=payload)
print(r.text)
