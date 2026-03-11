import yfinance as yf
import pandas as pd

symbols = {
"OFH":"OFH.CA",
"ETEL":"ETEL.CA",
"EAST":"EAST.CA",
"OIH":"OIH.CA"
}

def RSI(series, period=14):

    delta = series.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss

    rsi = 100 - (100 / (1 + rs))

    return rsi


for symbol,ticker in symbols.items():

    print("\n==========")
    print(symbol)

    data = yf.download(
        ticker,
        period="6mo",
        interval="1d",
        progress=False
    )

    print("Rows:",len(data))

    if data.empty:
        print("No data")
        continue

    close = data["Close"]

    data["RSI"] = RSI(close)

    print("Last price:", close.iloc[-1])
    print("Last RSI:", data["RSI"].iloc[-1])
