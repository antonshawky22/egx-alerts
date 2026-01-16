import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta

# =============================
# SETTINGS
# =============================

SYMBOLS = [
    "OFH", "OLFI", "EMFD", "ETEL", "EAST", "EFIH", "ABUK", "OIH",
    "SWDY", "ISPH", "ATQA", "MTIE", "ELEC", "HRHO", "ORWE",
    "JUFO", "DSCW", "SUGR", "ELSH", "RMDA", "RAYA", "EEII",
    "MPCO", "GBCO", "TMGH", "ORAS", "AMOC", "FWRY"
]

TIMEZONE_EGYPT = timezone(timedelta(hours=2))

# =============================
# INDICATORS
# =============================

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


# =============================
# STRATEGY
# =============================

def analyze_symbol(symbol):
    df = yf.download(
        symbol,
        period="6mo",
        interval="1d",
        progress=False,
        auto_adjust=True
    )

    if df.empty or len(df) < 60:
        return None

    # آخر شمعة مكتملة فقط
    df = df.iloc[:-1]

    close = df["Close"]

    ema_fast = close.ewm(span=9).mean()
    ema_slow = close.ewm(span=21).mean()
    rsi = calculate_rsi(close)

    price = float(close.iloc[-1])
    ema_fast_last = float(ema_fast.iloc[-1])
    ema_slow_last = float(ema_slow.iloc[-1])
    rsi_last = float(rsi.iloc[-1])

    candle_date = close.index[-1].date()

    # =============================
    # BUY
    # =============================
    if (
        ema_fast_last > ema_slow_last and
        40 <= rsi_last <= 55
    ):
        return {
            "type": "BUY",
            "symbol": symbol,
            "price": round(price, 2),
            "date": candle_date
        }

    # =============================
    # SELL
    # =============================
    if (
        ema_fast_last < ema_slow_last or
        rsi_last < 40
    ):
        return {
            "type": "SELL",
            "symbol": symbol,
            "price": round(price, 2),
            "date": candle_date
        }

    return None


# =============================
# MAIN
# =============================

def main():
    buy_signals = []
    sell_signals = []

    for symbol in SYMBOLS:
        try:
            signal = analyze_symbol(symbol)
            if signal:
                if signal["type"] == "BUY":
                    buy_signals.append(signal)
                else:
                    sell_signals.append(signal)
        except Exception as e:
            print(f"⚠️ خطأ في {symbol}: {e}")

    if not buy_signals and not sell_signals:
        print("ℹ️ لا توجد إشارات اليوم")
        return

    print("\nEGX ALERTS – BUY / SELL ONLY (EMA FAST + RSI | Daily Close)\n")

    for s in buy_signals:
        print(
            f"🟢 شراء | {s['symbol']}\n"
            f"📅 شمعة: {s['date']}\n"
            f"📊 سعر: {s['price']}\n"
        )

    for s in sell_signals:
        print(
            f"🔴 بيع | {s['symbol']}\n"
            f"📅 شمعة: {s['date']}\n"
            f"📊 سعر: {s['price']}\n"
        )


if __name__ == "__main__":
    main()
