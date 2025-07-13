import requests
import time
import pandas as pd
from flask import Flask
import threading
import os

# Telegram bot info — replace with your actual token and chat ID
TELEGRAM_BOT_TOKEN = "7976237011:AAHmAfze2QIMKqex5rLDJFhNVarblcQu8f4"
TELEGRAM_CHAT_ID = "5452580709"

# List of top 50 crypto pairs on Bybit (adjusted to valid symbols)
PAIRS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT",
    "AVAXUSDT", "DOGEUSDT", "DOTUSDT", "LINKUSDT", "MATICUSDT",
    "XLMUSDT", "LTCUSDT", "BCHUSDT", "TONUSDT", "UNIUSDT",
    "OPUSDT", "APTUSDT", "ARBUSDT", "NEARUSDT", "ATOMUSDT",
    "EOSUSDT", "FTMUSDT", "ALGOUSDT", "VETUSDT", "TRXUSDT",
    "THETAUSDT", "XMRUSDT", "ZECUSDT", "CHZUSDT", "GRTUSDT",
    "CAKEUSDT", "SANDUSDT", "MANAUSDT", "KSMUSDT", "CRVUSDT",
    "LDOUSDT", "1INCHUSDT", "QNTUSDT", "GLMRUSDT", "AXSUSDT",
    "RUNEUSDT", "EGLDUSDT", "DASHUSDT", "ZILUSDT", "HNTUSDT",
    "BTTUSDT", "STXUSDT", "XEMUSDT", "ZRXUSDT", "KAVAUSDT"
]

# Bybit API endpoint for kline data
BYBIT_KLINE_URL = "https://api.bybit.com/public/linear/kline"

# Telegram API URL
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

# Flask app for Render
app = Flask(__name__)

def send_telegram_message(message):
    try:
        resp = requests.post(TELEGRAM_API_URL, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        })
        if not resp.ok:
            print(f"Telegram error: {resp.json()}")
    except Exception as e:
        print(f"Error sending telegram message: {e}")

def fetch_candles(symbol, interval="60", limit=100):
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }
    try:
        response = requests.get(BYBIT_KLINE_URL, params=params)
        data = response.json()
        if data["retCode"] != 0 or "result" not in data or not data["result"]:
            print(f"❌ Invalid data structure for {symbol}: {data}")
            return None
        return data["result"]
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        return None

def calculate_sma(df, period):
    return df['close'].rolling(window=period).mean()

def check_strategy(df):
    # We want to see if sma7 crossed sma20 upwards or downwards, and both sma7 & sma20 above or below sma60
    # We'll check the last two candles to detect cross

    sma7 = calculate_sma(df, 7)
    sma20 = calculate_sma(df, 20)
    sma60 = calculate_sma(df, 60)

    # We need at least 61 candles to calculate sma60 for last point
    if len(df) < 61 or sma7.isnull().any() or sma20.isnull().any() or sma60.isnull().any():
        return None

    # Last two indices
    i = -1
    i_prev = -2

    # Cross upward: sma7 crosses above sma20
    cross_up = (sma7[i_prev] < sma20[i_prev]) and (sma7[i] > sma20[i])
    # Cross downward: sma7 crosses below sma20
    cross_down = (sma7[i_prev] > sma20[i_prev]) and (sma7[i] < sma20[i])

    # Both sma7 and sma20 above sma60 at last candle
    above_sma60 = (sma7[i] > sma60[i]) and (sma20[i] > sma60[i])
    # Both sma7 and sma20 below sma60 at last candle
    below_sma60 = (sma7[i] < sma60[i]) and (sma20[i] < sma60[i])

    if cross_up and above_sma60:
        return "BUY"
    elif cross_down and below_sma60:
        return "SELL"
    else:
        return None

def run_bot():
    send_telegram_message("🚀 *SMA Bot deployed and running!* Checking top 50 crypto pairs on 1-hour timeframe every 5 mins.")
    while True:
        for symbol in PAIRS:
            print(f"🔍 Checking {symbol}")
            candles = fetch_candles(symbol)
            if candles is None:
                print(f"❌ Failed to fetch data for {symbol}")
                continue

            # Create DataFrame
            df = pd.DataFrame(candles)
            # Convert prices to float
            df['close'] = df['close'].astype(float)

            signal = check_strategy(df)
            if signal:
                latest_close = df['close'].iloc[-1]
                message = (
                    f"📊 *{symbol}*\n"
                    f"SMA7 crossed SMA20 *{signal}*\n"
                    f"Both SMA7 & SMA20 {'above' if signal == 'BUY' else 'below'} SMA60\n"
                    f"Latest Close Price: {latest_close}\n"
                    f"Timeframe: 1-hour candles\n"
                    f"Checked every 5 minutes\n"
                    f"---\n"
                    f"Stay tuned for next signals!"
                )
                send_telegram_message(message)
                print(f"⚡ Signal on {symbol}: {signal}")
            else:
                print(f"No signal on {symbol}")

        print("✅ Cycle complete. Sleeping for 300 seconds.")
        time.sleep(300)  # 5 minutes

@app.route("/")
def home():
    return "SMA Bot is running!"

if __name__ == "__main__":
    # Run the bot in a separate thread so Flask app can run concurrently
    threading.Thread(target=run_bot, daemon=True).start()
    # Bind to the port Render sets, default to 8080 if not set
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
