import yfinance as yf
import pandas as pd
from telegram import Bot
import time
from datetime import datetime
import csv
import os

# === CONFIG ===
BOT_TOKEN = '7372197226:AAFYC4bpve18GVUMSGun894_iJjpvURRRKA'
CHAT_ID = '1173929413'

SHORT_EMA = 22
LONG_EMA = 44
CHECK_INTERVAL = 300  # 5 minutes

TIMEFRAMES = {
    '15m': '15m',
    '30m': '30m',
    '1d': '1d'
}

LOG_FILE = "signals_log.csv"

bot = Bot(token=BOT_TOKEN)

# === Load stock symbols ===
def load_stock_symbols():
    files = ['nifty50.txt']
    symbols = set()
    for file in files:
        with open(file, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    symbols.add(line)
    return list(symbols)

STOCK_SYMBOLS = load_stock_symbols()

# === Initialize log file (once only) ===
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['timestamp', 'symbol', 'timeframe', 'signal', 'price'])

# === Log signal to CSV ===
def log_signal(symbol, tf_name, signal_type, price):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, symbol, tf_name, signal_type, round(price, 2)])
    print(f"📝 Logged: {symbol}, {tf_name}, {signal_type}, {price:.2f}")

# === Send Telegram Alert ===
def send_alert(message):
    try:
        bot.send_message(chat_id=CHAT_ID, text=message)
        print(f"✅ Alert sent: {message}")
    except Exception as e:
        print(f"⚠️ Failed to send alert: {e}")

# === Track Last Signal per Symbol + Timeframe ===
sent_signals = {}

# === Check EMA Crossover ===
def check_ema_crossover(symbol, tf_name, tf_interval):
    try:
        period_map = {'15m': '5d', '30m': '10d', '1d': '60d'}
        df = yf.download(symbol, period=period_map[tf_name], interval=tf_interval, auto_adjust=False, progress=False)
        df.dropna(inplace=True)

        df['ema_short'] = df['Close'].ewm(span=SHORT_EMA, adjust=False).mean()
        df['ema_long'] = df['Close'].ewm(span=LONG_EMA, adjust=False).mean()

        if len(df) < 2:
            print(f"⚠️ Not enough data for {symbol} [{tf_name}]")
            return

        latest = df.iloc[-1]
        previous = df.iloc[-2]

        # Convert to float values using .item()
        prev_short = previous['ema_short'].item()
        prev_long = previous['ema_long'].item()
        latest_short = latest['ema_short'].item()
        latest_long = latest['ema_long'].item()
        price = latest['Close'].item() if hasattr(latest['Close'], 'item') else latest['Close']

        current_signal = None
        if prev_short < prev_long and latest_short > latest_long:
            current_signal = 'bullish'
        elif prev_short > prev_long and latest_short < latest_long:
            current_signal = 'bearish'


        if current_signal:
            last_signal = sent_signals.get(symbol, {}).get(tf_name)

            if last_signal != current_signal:
                emoji = '📈' if current_signal == 'bullish' else '📉'
                send_alert(f"{emoji} {current_signal.capitalize()} EMA Crossover on {symbol} [{tf_name}]\nPrice: {price:.2f}")
                log_signal(symbol, tf_name, current_signal, price)

                if symbol not in sent_signals:
                    sent_signals[symbol] = {}
                sent_signals[symbol][tf_name] = current_signal

    except Exception as e:
        print(f"⚠️ Error checking {symbol} [{tf_name}]: {e}")

# === MAIN LOOP ===
if __name__ == "__main__":
    print("🚀 EMA Crossover Bot Started with Logging")
    send_alert("🧪 Test Alert: Bot started with 15m, 75m, 1d crossovers. EMA(22,44)")

    while True:
        for symbol in STOCK_SYMBOLS:
            for tf_name, tf_interval in TIMEFRAMES.items():
                check_ema_crossover(symbol, tf_name, tf_interval)
                time.sleep(1)  # Avoid rate limit
        time.sleep(CHECK_INTERVAL)
