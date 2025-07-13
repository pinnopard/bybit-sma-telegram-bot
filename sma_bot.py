import requests
import time
import pandas as pd
import logging
from flask import Flask
from threading import Thread

# Logging
logging.basicConfig(level=logging.INFO, format="%(message)s")

# Telegram configuration
TELEGRAM_TOKEN = "7976237011:AAHmAfze2QIMKqex5rLDJFhNVarblcQu8f4"
TELEGRAM_CHAT_ID = "5452580709"

# Interval in seconds
INTERVAL = 300  # 5 minutes

# Top 50 valid crypto pairs on Bybit
SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT",
    "AVAXUSDT", "DOGEUSDT", "DOTUSDT", "LINKUSDT", "MATICUSDT",
    "XLMUSDT", "LTCUSDT", "BCHUSDT", "TONUSDT", "UNIUSDT",
    "OPUSDT", "APTUSDT", "ARBUSDT", "NEARUSDT", "ATOMUSDT",
    "PEPEUSDT", "INJUSDT", "FILUSDT", "SUIUSDT", "RNDRUSDT",
    "IMXUSDT", "GRTUSDT", "FTMUSDT", "AAVEUSDT", "ETCUSDT",
    "STXUSDT", "CHZUSDT", "CRVUSDT", "EGLDUSDT", "MKRUSDT",
    "DYDXUSDT", "FLOWUSDT", "SNXUSDT", "MINAUSDT", "GMXUSDT",
    "RUNEUSDT", "KLAYUSDT", "BATUSDT", "ZILUSDT", "SKLUSDT",
    "CELOUSDT", "ENJUSDT", "1INCHUSDT", "TWTUSDT", "ICXUSDT"
]

# SMA settings
SMA_PERIOD = 20
TIMEFRAME = "5"  # 5-minute candles

app = Flask(__name__)

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            logging.error(f"Telegram error: {response.text}")
    except Exception as e:
        logging.error(f"Telegram send failed: {e}")

def fetch_candles(symbol):
    url = f"https://api.bybit.com/v5/market/kline?category=linear&symbol={symbol}&interval={TIMEFRAME}&limit=100"
    response = requests.get(url)
    data = response.json()

    if data["retCode"] != 0 or "result" not in data:
        logging.warning(f"❌ Invalid data structure for {symbol}: {data}")
        return None

    try:
        df = pd.DataFrame(data["result"]["list"], columns=[
            "timestamp", "open", "high", "low", "close", "volume", "turnover"])
        df["close"] = pd.to_numeric(df["close"])
        return df
    except Exception as e:
        logging.warning(f"❌ Failed to parse candles for {symbol}: {e}")
        return None

def check_signals():
    for symbol in SYMBOLS:
        logging.info(f"🔍 Checking {symbol}")
        df = fetch_candles(symbol)
        if df is None or df.empty:
            logging.warning(f"❌ Failed to fetch data for {symbol}")
            continue

        df["sma"] = df["close"].rolling(SMA_PERIOD).mean()

        latest_close = df["close"].iloc[-1]
        latest_sma = df["sma"].iloc[-1]

        if pd.isna(latest_sma):
            logging.info(f"⚠️ Not enough data to compute SMA for {symbol}")
            continue

        if latest_close > latest_sma:
            message = f"📈 {symbol}: Price crossed **above** SMA{SMA_PERIOD}"
            send_telegram_message(message)
        elif latest_close < latest_sma:
            message = f"📉 {symbol}: Price crossed **below** SMA{SMA_PERIOD}"
            send_telegram_message(message)
        else:
            logging.info(f"No signal on {symbol}")

    logging.info("✅ Cycle complete. Sleeping for 300 seconds.")

def run_bot():
    logging.info("SMA bot started.")
    send_telegram_message("✅ SMA Bot deployed and started. Monitoring 50 pairs...")
    while True:
        check_signals()
        time.sleep(INTERVAL)

@app.route("/", methods=["GET", "HEAD"])
def home():
    return "SMA bot running"

def start_bot():
    bot_thread = Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()

if __name__ == "__main__":
    start_bot()
    app.run(host="0.0.0.0", port=8080)
