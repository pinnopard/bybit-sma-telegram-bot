import os
import time
import requests
import threading
from flask import Flask
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
import pandas as pd

app = Flask(__name__)

@app.route("/")
def index():
    return "SMA Bot is running"

# Symbols list - top 20 crypto and top 10 forex + XAUUSD
SYMBOLS = [
    'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT', 'AVAXUSDT', 'DOGEUSDT', 'DOTUSDT', 'LINKUSDT', 'MATICUSDT',
    'XLMUSDT', 'LTCUSDT', 'BCHUSDT', 'TONUSDT', 'UNIUSDT', 'OPUSDT', 'APTUSDT', 'ARBUSDT', 'NEARUSDT', 'ATOMUSDT',
    'XAUUSD', 'USDJPY', 'EURUSD', 'GBPUSD', 'AUDUSD', 'USDCAD', 'USDCHF', 'NZDUSD', 'EURJPY', 'GBPJPY'
]
INTERVAL = '60'  # 1 hour candles
LIMIT = 100
CHECK_INTERVAL = 300  # 5 minutes

def get_klines(symbol):
    url = f"https://api.bybit.com/v5/market/kline?category=linear&symbol={symbol}&interval={INTERVAL}&limit={LIMIT}"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if "result" not in data or "list" not in data["result"]:
            print(f"❌ Invalid data structure for {symbol}: {data}", flush=True)
            return None
        df = pd.DataFrame(data["result"]["list"], columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'
        ])
        df['close'] = pd.to_numeric(df['close'])
        return df
    except Exception as e:
        print(f"❌ Exception fetching klines for {symbol}: {e}", flush=True)
        return None

def check_signal(df):
    df['sma1'] = df['close'].rolling(window=7).mean()
    df['sma2'] = df['close'].rolling(window=20).mean()
    df['sma3'] = df['close'].rolling(window=60).mean()

    if len(df) < 61:
        return None

    prev = df.iloc[-2]
    last = df.iloc[-1]

    # Buy signal
    if (
        prev['sma1'] < prev['sma2'] and
        last['sma1'] > last['sma2'] and
        last['sma1'] > last['sma3'] and
        last['sma2'] > last['sma3']
    ):
        return "BUY"

    # Sell signal
    if (
        prev['sma1'] > prev['sma2'] and
        last['sma1'] < last['sma2'] and
        last['sma1'] < last['sma3'] and
        last['sma2'] < last['sma3']
    ):
        return "SELL"

    return None

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code != 200:
            print(f"❌ Telegram API error: {resp.text}", flush=True)
    except Exception as e:
        print(f"❌ Failed to send Telegram message: {e}", flush=True)

def run_bot():
    print("SMA bot started running in thread.", flush=True)
    # Startup test message
    send_telegram_message("✅ SMA Bot is now live on Render and monitoring symbols.")

    while True:
        for symbol in SYMBOLS:
            try:
                print(f"Checking {symbol}", flush=True)
                df = get_klines(symbol)
                if df is None:
                    print(f"Failed to fetch data for {symbol}", flush=True)
                    continue

                signal = check_signal(df)
                if signal:
                    msg = f"{signal} signal on {symbol} (1H timeframe)"
                    send_telegram_message(msg)
                    print(f"Sent alert: {msg}", flush=True)
                else:
                    print(f"No signal on {symbol}", flush=True)

            except Exception as e:
                print(f"⚠️ Error with {symbol}: {e}", flush=True)

        print(f"Cycle complete. Sleeping {CHECK_INTERVAL}s\n", flush=True)
        time.sleep(CHECK_INTERVAL)

def start_bot_thread():
    thread = threading.Thread(target=run_bot)
    thread.daemon = True
    thread.start()

if __name__ == "__main__":
    start_bot_thread()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
