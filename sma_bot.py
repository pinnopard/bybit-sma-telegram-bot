import requests
import time
import pandas as pd

# --- Telegram config ---
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_TELEGRAM_CHAT_ID"

# --- Pairs to monitor ---
PAIRS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT",
    "AVAXUSDT", "DOGEUSDT", "DOTUSDT", "LINKUSDT", "MATICUSDT",
    "XLMUSDT", "LTCUSDT", "BCHUSDT", "TONUSDT", "UNIUSDT",
    "OPUSDT", "APTUSDT", "ARBUSDT", "NEARUSDT", "ATOMUSDT",
    "FTMUSDT", "ALGOUSDT", "CROUSDT", "VETUSDT", "ICPUSDT",
    "EGLDUSDT", "FILUSDT", "GRTUSDT", "SANDUSDT", "THETAUSDT",
    "MANAUSDT", "CAKEUSDT", "AAVEUSDT", "1INCHUSDT", "AXSUSDT",
    "ZILUSDT", "KSMUSDT", "MKRUSDT", "LRCUSDT", "ENJUSDT",
    "CHZUSDT", "BATUSDT", "CELRUSDT", "CRVUSDT", "DASHUSDT",
    "DGBUSDT", "DOGEUSDT", "EOSUSDT", "ETCUSDT", "GALAUSDT"
]

BYBIT_API_URL = "https://api.bybit.com/public/linear/kline"

# --- Helper: send Telegram message ---
def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    resp = requests.post(url, data=payload)
    if not resp.ok:
        print(f"Telegram error: {resp.text}")

# --- Helper: fetch kline data for a pair ---
def fetch_candles(symbol, interval="60", limit=100):
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }
    try:
        response = requests.get(BYBIT_API_URL, params=params, timeout=10)
        data = response.json()
        if data.get("retCode") != 0:
            print(f"❌ Bybit API error for {symbol}: {data.get('retMsg')}")
            return None
        result = data.get("result")
        if not result:
            print(f"❌ No data for {symbol}")
            return None
        return result
    except Exception as e:
        print(f"❌ Exception fetching {symbol}: {e}")
        return None

# --- Calculate SMAs and check strategy ---
def check_strategy(df):
    # Calculate SMAs
    df['close'] = df['close'].astype(float)
    df['sma7'] = df['close'].rolling(window=7).mean()
    df['sma20'] = df['close'].rolling(window=20).mean()
    df['sma60'] = df['close'].rolling(window=60).mean()

    # Use only closed candles (exclude last candle)
    df = df.iloc[:-1]

    if len(df) < 61:  # Ensure enough data for SMA60
        return None

    # Get last two rows to detect cross
    last = df.iloc[-1]
    prev = df.iloc[-2]

    # Detect upward cross sma7 crosses above sma20
    cross_up = (prev['sma7'] < prev['sma20']) and (last['sma7'] > last['sma20'])

    # Detect downward cross sma7 crosses below sma20
    cross_down = (prev['sma7'] > prev['sma20']) and (last['sma7'] < last['sma20'])

    if cross_up and (last['sma7'] > last['sma60']) and (last['sma20'] > last['sma60']):
        return "BUY"

    if cross_down and (last['sma7'] < last['sma60']) and (last['sma20'] < last['sma60']):
        return "SELL"

    return None

def main():
    print("SMA bot started. Checking pairs every 15 minutes...")

    # Send a test message on start
    send_telegram_message("✅ SMA bot started and running.")

    while True:
        try:
            for pair in PAIRS:
                print(f"🔍 Checking {pair}")
                candles = fetch_candles(pair)
                if not candles:
                    print(f"❌ Failed to fetch data for {pair}")
                    continue

                # Prepare DataFrame
                df = pd.DataFrame(candles)
                signal = check_strategy(df)

                if signal:
                    msg = (
                        f"⚡️ {signal} signal detected for {pair}\n"
                        f"Timeframe: 1h\n"
                        f"SMA7 crossed SMA20 {'upward' if signal=='BUY' else 'downward'}, "
                        f"both above/below SMA60.\n"
                        f"Last close price: {df.iloc[-2]['close']}"
                    )
                    send_telegram_message(msg)
                    print(f"📨 Sent {signal} alert for {pair}")
                else:
                    print(f"No signal on {pair}")

            print("✅ Cycle complete. Sleeping for 15 minutes.")
            time.sleep(900)

        except Exception as e:
            print(f"❌ Exception in main loop: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
