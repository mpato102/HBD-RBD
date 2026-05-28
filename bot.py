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
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"})

# ── TRADINGVIEW DATA ──────────────────────────────────
def get_data(symbol, exchange, interval):
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
        res = requests.post(url, json=body, timeout=10)
        d = res.json()["data"][0]["d"]
        closes = list(reversed(d[0:10]))
        rsis = list(reversed(d[10:20]))
        return closes, rsis
    except:
        return None, None

# ── DIVERGENCE ────────────────────────────────────────
def detect_divergence(closes, rsis):
    if len(closes) < 10 or len(rsis) < 10:
        return False, False

    # Laba half u qaybi
    prev_closes = closes[:5]
    curr_closes = closes[5:]
    prev_rsis = rsis[:5]
    curr_rsis = rsis[5:]

    prev_low_p = min(prev_closes)
    curr_low_p = min(curr_closes)
    prev_low_r = min(prev_rsis)
    curr_low_r = min(curr_rsis)

    # Regular Bullish: price LL, RSI HL
    regular = curr_low_p < prev_low_p and curr_low_r > prev_low_r

    # Hidden Bullish: price HL, RSI LL
    hidden = curr_low_p > prev_low_p and curr_low_r < prev_low_r

    return regular, hidden

# ── CANDLE CONFIRMATION ───────────────────────────────
def candle_confirmation(closes):
    if len(closes) < 3:
        return False
    # Bullish close (last candle green)
    return closes[-1] > closes[-2]

# ── MAIN SCAN ─────────────────────────────────────────
def scan():
    print(f"\n🔍 Scan bilaabanaya — {datetime.now().strftime('%H:%M:%S')}")
    
    for coin in COINS:
        try:
            # 4H data
            closes_4h, rsis_4h = get_data(coin, EXCHANGE, "240")
            if not closes_4h:
                continue

            _, hidden_4h = detect_divergence(closes_4h, rsis_4h)

            # 1H data
            closes_1h, rsis_1h = get_data(coin, EXCHANGE, "60")
            if not closes_1h:
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
                print(f"❌ No signal: {coin}")

            time.sleep(1)

        except Exception as e:
            print(f"Error {coin}: {e}")

# ── RUN ───────────────────────────────────────────────
if __name__ == "__main__":
    send_telegram("🤖 <b>RSI Signal Bot Started!</b>\nScanning...")
    while True:
        scan()
        print("⏳ 4 saac sugaya...")
        time.sleep(14400)  # 4 saac
