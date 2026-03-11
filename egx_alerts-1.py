import yfinance as yf
import pandas as pd
import requests
import os

# =====================
# Telegram settings
# =====================
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram(message):
    if not TOKEN or not CHAT_ID:
        print("Telegram credentials not set")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": message}, timeout=10)
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
# EMA periods
# =====================
ema_periods = [120, 150, 200]

# =====================
# Function to calculate EMA
# =====================
def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

# =====================
# Collect results
# =====================
messages = []
data_failures = []

for name, ticker in symbols.items():
    try:
        df = yf.download(ticker, period="1y", interval="1d", auto_adjust=True, progress=False)
        if df is None or df.empty:
            data_failures.append(ticker)
            continue

        close = df["Close"]
        msg = f"📊 {name} ({ticker}):\n"
        for period in ema_periods:
            if len(close) < period:
                msg += f"⚠️ Not enough data for EMA{period} ({len(close)} days)\n"
            else:
                df[f"EMA{period}"] = ema(close, period)
                msg += f"✅ EMA{period}: {df[f'EMA{period}'].iloc[-1]:.2f}\n"

        messages.append(msg)

    except Exception as e:
        data_failures.append(ticker)
        messages.append(f"❌ Error fetching {ticker}: {e}")

# =====================
# Prepare Telegram message
# =====================
final_message = "🚨 EGX EMA Test Scan\n\n"

if messages:
    final_message += "\n".join(messages)

if data_failures:
    final_message += "\n⚠️ Failed to fetch data:\n" + ", ".join(data_failures)

# =====================
# Send Telegram
# =====================
send_telegram(final_message)
print(final_message)
