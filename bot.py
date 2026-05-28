import requests
import time
from datetime import datetime

# ── CONFIG ──────────────────────────────────────────
TELEGRAM_TOKEN = "8210009776:AAHC3we-Jxu6p7UVrIf6SPrQLrVYqOA_yR8"
CHAT_ID = "6311790109"

COINS = [
    "SOLUSDT", "RENDERUSDT", "BTCUSDT", "ETHUSDT",
    "AVAXUSDT", "LINKUSDT", "INJUSDT", "ARBUSDT",
    "OPUSDT", "POLUSDT"
]

# ── TELEGRAM ─────────────────────────────────────────
def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"})
    except Exception as e:
        print(f"Telegram error: {e}")

# ── BINANCE API ───────────────────────────────────────
def get_candles(symbol, interval, limit=50):
    try:
        # MEXC interval format
        interval_map = {"4h": "4h", "1h": "60m", "15m": "15m"}
        url = "https://api.mexc.com/api/v3/klines"
        params = {
            "symbol": symbol,
            "interval": interval_map[interval],
            "limit": limit
        }
        res = requests.get(url, params=params, timeout=15)
        data = res.json()
        if not isinstance(data, list):
            print(f"MEXC error {symbol}: {data}")
            return []
        closes = [float(c[4]) for c in data]
        return closes
    except Exception as e:
        print(f"Fetch error {symbol} {interval}: {e}")
        return []

# ── RSI ───────────────────────────────────────────────
def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i-1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    avg_g = sum(gains[:period]) / period
    avg_l = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_g = (avg_g * (period-1) + gains[i]) / period
        avg_l = (avg_l * (period-1) + losses[i]) / period
    if avg_l == 0:
        return 100
    return 100 - (100 / (1 + avg_g / avg_l))

def get_rsi_series(closes, period=14):
    rsi_list = []
    for i in range(period, len(closes)):
        rsi_list.append(calc_rsi(closes[:i+1], period))
    return rsi_list

# ── DIVERGENCE ────────────────────────────────────────
def detect_divergence(closes, rsis, lookback=10):
    try:
        if len(closes) < lookback or len(rsis) < lookback:
            return False, False

        p = closes[-lookback:]
        r = rsis[-lookback:]
        half = lookback // 2

        prev_low_p = min(p[:half])
        curr_low_p = min(p[half:])
        prev_low_r = min(r[:half])
        curr_low_r = min(r[half:])

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
            # 4H candles
            closes_4h = get_candles(coin, "4h", 100)
            if len(closes_4h) < 30:
                print(f"❌ No 4H data: {coin}")
                continue
            rsis_4h = get_rsi_series(closes_4h)
            _, hidden_4h = detect_divergence(closes_4h[-20:], rsis_4h[-20:])

            # 1H candles
            closes_1h = get_candles(coin, "1h", 100)
            if len(closes_1h) < 30:
                print(f"❌ No 1H data: {coin}")
                continue
            rsis_1h = get_rsi_series(closes_1h)
            regular_1h, _ = detect_divergence(closes_1h[-20:], rsis_1h[-20:])

            # 15M candles
            closes_15m = get_candles(coin, "15m", 100)
            if len(closes_15m) < 30:
                print(f"❌ No 15M data: {coin}")
                continue
            rsis_15m = get_rsi_series(closes_15m)
            regular_15m, _ = detect_divergence(closes_15m[-20:], rsis_15m[-20:])
            candle_15m = candle_confirmation(closes_15m)

            print(f"➖ {coin} | Hidden4H={hidden_4h} | Regular1H={regular_1h} | Regular15M={regular_15m} | Candle={candle_15m}")

            # Signal: 4H Hidden + (1H ama 15M Regular) + Candle
            if hidden_4h and (regular_1h or regular_15m) and candle_15m:
                tf_label = "1H" if regular_1h else "15M"
                msg = (
                    f"⚡ <b>SIGNAL HELAY!</b>\n\n"
                    f"🪙 <b>{coin}</b>\n"
                    f"━━━━━━━━━━━━━━\n"
                    f"✅ 4H Hidden Bullish Div\n"
                    f"✅ {tf_label} Regular Bullish Div\n"
                    f"✅ 15M Candle Confirmation\n"
                    f"━━━━━━━━━━━━━━\n"
                    f"💰 Price: ${closes_4h[-1]:,.4f}\n"
                    f"📊 RSI 4H: {rsis_4h[-1]:.1f}\n"
                    f"📊 RSI 1H: {rsis_1h[-1]:.1f}\n"
                    f"📊 RSI 15M: {rsis_15m[-1]:.1f}\n"
                    f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                )
                send_telegram(msg)
                print(f"✅ Signal: {coin}")

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
