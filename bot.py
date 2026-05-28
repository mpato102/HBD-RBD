import requests
import time
from datetime import datetime

# ── CONFIG ──────────────────────────────────────────
TELEGRAM_TOKEN = "8210009776:AAHC3we-Jxu6p7UVrIf6SPrQLrVYqOA_yR8"
CHAT_ID = "6311790109"

COINS = [
    "SOLUSDT", "RENDERUSDT", "BTCUSDT", "ETHUSDT",
    "AVAXUSDT", "LINKUSDT", "INJUSDT", "ARBUSDT",
    "OPUSDT", "MATICUSDT"
]

EXCHANGE = "BINANCE"

# ── TELEGRAM ─────────────────────────────────────────
def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"})
    except Exception as e:
        print(f"Telegram error: {e}")

# ── TRADINGVIEW DATA ──────────────────────────────────
def get_data(symbol, exchange):
    url = "https://scanner.tradingview.com/crypto/scan"
    columns = [
        "close", "close[1]", "close[2]", "close[3]", "close[4]",
        "close[5]", "close[6]", "close[7]", "close[8]", "close[9]",
        "RSI", "RSI[1]", "RSI[2]", "RSI[3]", "RSI[4]",
        "RSI[5]", "RSI[6]", "RSI[7]", "RSI[8]", "RSI[9]",
    ]
    body = {
        "symbols": {"tickers": [f"{exchange}:{symbol}"], "query": {"types": []}},
        "columns": columns
    }
    try:
        res = requests.post(url, json=body, timeout=15)
        d = res.json()["data"][0]["d"]
        closes = [x for x in reversed(d[0:10]) if x is not None]
        rsis = [x for x in reversed(d[10:20]) if x is not None]
        if len(closes) < 6 or len(rsis) < 6:
            return [], []
        return closes, rsis
    except Exception as e:
        print(f"Fetch error {symbol}: {e}")
        return [], []

# ── DIVERGENCE ────────────────────────────────────────
def detect_divergence(closes, rsis):
    try:
        if len(closes) < 6 or len(rsis) < 6:
            return False, False

        half = len(closes) // 2
        prev_closes = closes[:half]
        curr_closes = closes[half:]
        prev_rsis = rsis[:half]
        curr_rsis = rsis[half:]

        prev_low_p = min(prev_closes)
        curr_low_p = min(curr_closes)
        prev_low_r = min(prev_rsis)
        curr_low_r = min(curr_rsis)

        # Regular Bullish: price LL, RSI HL
        regular = curr_low_p < prev_low_p and curr_low_r > prev_low_r

        # Hidden Bullish: price HL, RSI LL
        hidden = curr_low_p > prev_low_p and curr_low_r < prev_low_r

        return regular, hidden
    except Exception as e:
        print(f"Divergence error: {e}")
        return False, False

# ── CANDLE CONFIRMATION ───────────────────────────────
def candle_confirmation(closes):
    try:
        if len(closes) < 2:
            return False
        return closes[-1] > closes[-2]
    except:
        return False

# ── MAIN SCAN ─────────────────────────────────────────
def scan():
    print(f"\n🔍 Scan bilaabanaya — {datetime.now().strftime('%H:%M:%S')}")

    for coin in COINS:
        try:
            # 4H data
            closes_4h, rsis_4h = get_data(coin, EXCHANGE)
            if not closes_4h:
                print(f"❌ No 4H data: {coin}")
                continue

            _, hidden_4h = detect_divergence(closes_4h, rsis_4h)

            # 1H data
            closes_1h, rsis_1h = get_data(coin, EXCHANGE)
            if not closes_1h:
                print(f"❌ No 1H data: {coin}")
                continue

            regular_1h, _ = detect_divergence(closes_1h, rsis_1h)
            candle_1h = candle_confirmation(closes_1h)

            # Strategy check
            if hidden_4h and regular_1h and candle_1h:
                msg = (
                    f"⚡ <b>SIGNAL HELAY!</b>\n\n"
                    f"🪙 <b>{coin}</b>\n"
                    f"━━━━━━━━━━━━━━\n"
                    f"✅ 4H Hidden Bullish Div\n"
                    f"✅ 1H Regular Bullish Div\n"
                    f"✅ Candle Confirmation\n"
                    f"━━━━━━━━━━━━━━\n"
                    f"💰 Price: ${closes_4h[-1]:,.4f}\n"
                    f"📊 RSI 4H: {rsis_4h[-1]:.1f}\n"
                    f"📊 RSI 1H: {rsis_1h[-1]:.1f}\n"
                    f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                )
                send_telegram(msg)
                print(f"✅ Signal: {coin}")
            else:
                print(f"➖ No signal: {coin} | Hidden4H={hidden_4h} | Regular1H={regular_1h} | Candle={candle_1h}")

            time.sleep(1)

        except Exception as e:
            print(f"Error {coin}: {e}")

# ── RUN ───────────────────────────────────────────────
if __name__ == "__main__":
    send_telegram("🤖 <b>RSI Signal Bot Started!</b>\nScanning coins...")
    while True:
        scan()
        print("⏳ 4 saac sugaya...")
        time.sleep(14400)
