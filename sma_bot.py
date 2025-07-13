import requests
import pandas as pd
import time
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, SYMBOLS, INTERVAL, CHECK_INTERVAL_SECONDS

BASE_URL = "https://api.bybit.com"

def get_klines(symbol, interval=INTERVAL, limit=100):
    endpoint = "/v5/market/kline"
    params = {
        "category": "linear",
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }
    response = requests.get(BASE_URL + endpoint, params=params)
    data = response.json()
    if data["retCode"] != 0:
        raise Exception(f"API error: {data['retMsg']}")
    df = pd.DataFrame(data["result"]["list"], columns=[
        "timestamp", "open", "high", "low", "close", "volume", "turnover"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit='ms')
    df = df.astype({"close": float})
    return df[["timestamp", "close"]]

def apply_triple_sma_strategy(df, sma1=7, sma2=20, sma3=60):
    df["SMA1"] = df["close"].rolling(sma1).mean()
    df["SMA2"] = df["close"].rolling(sma2).mean()
    df["SMA3"] = df["close"].rolling(sma3).mean()
    df["Signal"] = "HOLD"
    for i in range(1, len(df)):
        prev_sma1 = df.loc[i-1, "SMA1"]
        prev_sma2 = df.loc[i-1, "SMA2"]
        curr_sma1 = df.loc[i, "SMA1"]
        curr_sma2 = df.loc[i, "SMA2"]
        curr_sma3 = df.loc[i, "SMA3"]

        if (
            pd.notna(prev_sma1) and pd.notna(prev_sma2) and pd.notna(curr_sma1) and pd.notna(curr_sma2) and pd.notna(curr_sma3)
        ):
            # BUY condition
            if (
                prev_sma1 < prev_sma2 and
                curr_sma1 > curr_sma2 and
                curr_sma1 > curr_sma3 and
                curr_sma2 > curr_sma3
            ):
                df.loc[i, "Signal"] = "BUY"
            # SELL condition
            elif (
                prev_sma1 > prev_sma2 and
                curr_sma1 < curr_sma2 and
                curr_sma1 < curr_sma3 and
                curr_sma2 < curr_sma3
            ):
                df.loc[i, "Signal"] = "SELL"
    return df

def send_telegram_alert(symbol, message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": f"{symbol}: {message}"
    }
    response = requests.post(url, json=payload)
    if not response.ok:
        print("Telegram alert failed:", response.text)

def monitor(last_signal_times=None):
    if last_signal_times is None:
        last_signal_times = {symbol: None for symbol in SYMBOLS}

    for symbol in SYMBOLS:
        try:
            df = get_klines(symbol)
            df = apply_triple_sma_strategy(df)
            latest = df.iloc[-1]

            if latest["Signal"] in ["BUY", "SELL"]:
                candle_time = latest["timestamp"]
                if last_signal_times[symbol] is None or candle_time > last_signal_times[symbol]:
                    message = (
                        f"🚨 {latest['Signal']} SIGNAL 🚨\n"
                        f"Price: {latest['close']:.2f}\n"
                        f"Time: {candle_time}"
                    )
                    send_telegram_alert(symbol, message)
                    last_signal_times[symbol] = candle_time
        except Exception as e:
            print(f"Error processing {symbol}: {e}")

    return last_signal_times

if __name__ == "__main__":
    last_signal_times = None
    while True:
        last_signal_times = monitor(last_signal_times)
        time.sleep(CHECK_INTERVAL_SECONDS)
