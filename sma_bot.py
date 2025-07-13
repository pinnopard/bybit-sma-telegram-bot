import requests
import time
import pandas as pd
import logging
from flask import Flask
from threading import Thread

# Logging
logging.basicConfig(level=logging.INFO, format="%(message)s")

# Telegram configuration (replace with your actual values)
TELEGRAM_TOKEN = "7976237011:AAHmAfze2QIMKqex5rLDJFhNVarblcQu8f4"
TELEGRAM_CHAT_ID = "5452580709"

# Interval in seconds (bot checking interval)
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

# Candle timeframe on Bybit
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
    try:
        response = requests.get(url)
        data = response.json()
        if data["retCode"] != 0 or "result" not in data:
            logging.warning(f"❌ Invalid data structure for {symbol}: {data}")
            return None

        df = pd.DataFrame(data["result"]["list"], columns=[
            "timestamp", "open", "high", "low", "close", "volume", "turnover"])
        df["close"] = pd.to_numeric(df["close"])
        return df
    except Exception as e:
        logging.warning(f"❌ Failed to fetch data for {symbol}: {e}")
        return None

def check_signals():
    for symbol in SYMBOLS:
        logging.info(f"🔍 Checking {symbol}")
        df = fetch_candles(symbol)
        if df is None or df.empty:
            logging.warning(f"❌ Failed to fetch data for {symbol}")
            continue

        df["sma7"] = df["close"].rolling(7).mean()
        df["sma20"] = df["close"].rolling(20).mean()
        df["sma60"] = df["close"].rolling(60).mean()

        if df[["sma7", "sma20", "sma60"]].isna().any().any():
            logging.info(f"⚠️ Not enough data to compute all SMAs for {symbol}")
            continue

        sma7_prev = df["sma7"].iloc[-2]
        sma20_prev = df["sma20"].iloc[-2]
        sma60_now = df["sma60"].iloc[-1]
        sma7_now = df["sma7"].iloc[-1]
        sma20_now = df["sma20"].iloc[-1]
        price_now = df["close"].iloc[-1]

        # Check for crossover
        if sma7_prev < sma20_prev and sma7_now > sma20_now and sma7_now > sma60_now and sma20_now > sma60_now:
            message = (
                f"✅ *Bullish SMA Crossover* on {symbol}\n"
                f"Price: `{price_now}`\n"
                f"SMA7 crossed *above* SMA20\n"
                f"Both are *above* SMA60\n"
                f"⏰ Timeframe: {TIMEFRAME}min"
            )
            send_telegram_message(message)
        elif sma7_prev > sma20_prev and sma7_now < sma20_now and sma7_now < sma60_now and sma20_now < sma60_now:
            message = (
                f"⚠️ *Bearish SMA Crossover* on {symbol}\n"
                f"Price: `{price_now}`\n"
                f"SMA7 crossed *below* SMA20\n"
                f"Both are *below* SMA60\n"
                f"⏰ Timeframe: {TIMEFRAME}min"
            )
            send_telegram_message(message)
        else:
            logging.info(f"No signal for {symbol}")

    logging.info(f"✅ Scan complete. Sleeping for {INTERVAL} seconds.")

def run_bot():
    logging.info("SMA bot started.")
    send_telegram_message("🚀 *SMA Bot Deployed*\nMonitoring top 50 pairs using 1-hour SMA crossover logic.")
    while True:
        check_signals()
        time.sleep(INTERVAL)

@app.route("/", methods=["GET", "HEAD"])
def home():
    return "SMA bot is running."

def start_bot():
    bot_thread = Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()

if __name__ == "__main__":
    start_bot()
    app.run(host="0.0.0.0", port=8080)

