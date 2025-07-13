import requests
import time
import pandas as pd
import logging
from flask import Flask
from threading import Thread
from datetime import datetime
import pytz

# Logging
logging.basicConfig(level=logging.INFO, format="%(message)s")

# Telegram configuration
TELEGRAM_TOKEN = "7976237011:AAHmAfze2QIMKqex5rLDJFhNVarblcQu8f4"
TELEGRAM_CHAT_ID = "5452580709"

# Interval in seconds (15 minutes)
INTERVAL = 900  # 15 minutes

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
SMA7_PERIOD = 7
SMA20_PERIOD = 20
SMA60_PERIOD = 60
TIMEFRAME = "60"  # 1-hour candles

app = Flask(__name__)

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
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

    if data["retCode"] != 0 or "result" not in data or "list" not in data["result"]:
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

        # Compute SMAs
        df["sma7"] = df["close"].rolling(SMA7_PERIOD).mean()
        df["sma20"] = df["close"].rolling(SMA20_PERIOD).mean()
        df["sma60"] = df["close"].rolling(SMA60_PERIOD).mean()

        latest = df.iloc[-1]

        # Check if enough data for all SMAs
        if pd.isna(latest["sma7"]) or pd.isna(latest["sma20"]) or pd.isna(latest["sma60"]):
            logging.info(f"⚠️ Not enough data to compute all SMAs for {symbol}")
            continue

        # Get previous row for cross detection
        prev = df.iloc[-2]

        # Conditions for cross of sma7 and sma20
        cross_above = (prev["sma7"] <= prev["sma20"]) and (latest["sma7"] > latest["sma20"])
        cross_below = (prev["sma7"] >= prev["sma20"]) and (latest["sma7"] < latest["sma20"])

        # Only alert if cross happens above or below sma60
        if cross_above and latest["sma7"] > latest["sma60"]:
            signal = "BUY"
        elif cross_below and latest["sma7"] < latest["sma60"]:
            signal = "SELL"
        else:
            logging.info(f"No signal on {symbol}")
            continue

        # Get Nigerian time for alert timestamp
        tz = pytz.timezone("Africa/Lagos")
        now_nigeria = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

        message = (
            f"*Symbol:* {symbol}\n"
            f"*Signal:* {signal}\n"
            f"*Trend:* {'Above SMA60' if signal == 'BUY' else 'Below SMA60'}\n"
            f"*Current Price:* {latest['close']}\n"
            f"*Time (Nigeria):* {now_nigeria}"
        )
        send_telegram_message(message)

    logging.info(f"✅ Cycle complete. Sleeping for {INTERVAL} seconds.")

def run_bot():
    logging.info("SMA bot started.")
    send_telegram_message("✅ SMA Bot deployed and started. Monitoring 50 pairs with 1-hour candles, checking every 15 minutes.")
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
