import requests
import time
from datetime import datetime, timezone, timedelta

# ── CONFIG ──────────────────────────────────────────
TELEGRAM_TOKEN = "8210009776:AAHC3we-Jxu6p7UVrIf6SPrQLrVYqOA_yR8"
CHAT_ID = "6311790109"

COINS = [
   "BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT",
"LINKUSDT", "ARUSDT", "RENDERUSDT", "NEARUSDT",
"FETUSDT", "SUIUSDT", "DCRUSDT", "VIRTUALUSDT",
"TAOUSDT", "TIAUSDT", "XRPUSDT", "WCTUSDT",
"WLDUSDT", "ZROUSDT", "PYTHUSDT", "CLOREUSDT",
"FILUSDT", "KASUSDT", "SAGAUSDT", "ACTUSDT",
"AIXBTUSDT", "IMXUSDT", "OPUSDT", "STXUSDT",
"ONGUSDT", "ALICEUSDT", "COREUSDT",
"CFXUSDT", "MINAUSDT", "FIDAUSDT", "ZILUSDT",
"POPCATUSDT", "VANAUSDT", "WIFUSDT", "TRXUSDT",
"RSRUSDT", "RAREUSDT", "XECUSDT", "DEAIUSDT",
"ENSUSDT", "API3USDT", "MANAUSDT",
"IOTAUSDT", "BICOUSDT", "POLUSDT", "NOTUSDT",
"APEUSDT", "AVAAIUSDT", "BIDUSDT",
"AUSDT", "PENGUUSDT", "ATHUSDT", "LPTUSDT",
"ZECUSDT", "HBARUSDT", "RIVERUSDT", "KITEUSDT",
"ICPUSDT", "QNTUSDT", "APTUSDT", "JASMYUSDT",
"SEIUSDT", "DOTUSDT", "ATOMUSDT"
]

# ── EST TIMEZONE ──────────────────────────────────────
EST = timezone(timedelta(hours=-5))

# ── TELEGRAM ─────────────────────────────────────────
def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"})
    except Exception as e:
        print(f"Telegram error: {e}")

# ── CANDLES ───────────────────────────────────────────
def get_candles(symbol, interval, limit=200):
    try:
        interval_map = {"1d": "1d", "4h": "4h", "1h": "60m", "15m": "15m", "5m": "5m"}
        url = "https://api.mexc.com/api/v3/klines"
        params = {"symbol": symbol, "interval": interval_map[interval], "limit": limit}
        res = requests.get(url, params=params, timeout=15)
        data = res.json()
        if not isinstance(data, list):
            print(f"MEXC error {symbol}: {data}")
            return []
        return data
    except Exception as e:
        print(f"Fetch error {symbol} {interval}: {e}")
        return []

def get_closes(symbol, interval, limit=200):
    data = get_candles(symbol, interval, limit)
    return [float(c[4]) for c in data]

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

# ── SWING LOWS ────────────────────────────────────────
def find_swing_lows(closes, rsis, window=3):
    swing_lows = []
    for i in range(window, len(closes) - window):
        is_low = all(closes[i] <= closes[i-j] for j in range(1, window+1)) and \
                 all(closes[i] <= closes[i+j] for j in range(1, window+1))
        if is_low:
            rsi_idx = i - (len(closes) - len(rsis))
            rsi_val = rsis[rsi_idx] if 0 <= rsi_idx < len(rsis) else None
            swing_lows.append((i, closes[i], rsi_val))
    return swing_lows

# ── DIVERGENCE ────────────────────────────────────────
def detect_divergence(closes, rsis, lookback=40):
    try:
        if len(closes) < lookback or len(rsis) < lookback:
            return False, False

        p = closes[-lookback:]
        r = rsis[-lookback:]

        swings = find_swing_lows(p, r, window=3)

        if len(swings) < 2:
            return False, False

        prev = swings[-2]
        curr = swings[-1]

        prev_p, prev_r = prev[1], prev[2]
        curr_p, curr_r = curr[1], curr[2]

        if prev_r is None or curr_r is None:
            return False, False

        margin_p = prev_p * 0.005
        margin_r = 1.0

        regular = (curr_p < prev_p - margin_p) and (curr_r > prev_r + margin_r)
        hidden = (curr_p > prev_p + margin_p) and (curr_r < prev_r - margin_r)

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

# ── STRATEGY 2 — DAILY HIGH BREAK & RETEST ───────────
def get_daily_prev_high(symbol):
    try:
        # EST midnight → UTC timestamp
        now_est = datetime.now(EST)
        today_midnight_est = now_est.replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        today_midnight_utc = today_midnight_est.astimezone(timezone.utc)
        end_ts = int(today_midnight_utc.timestamp() * 1000)

        url = "https://api.mexc.com/api/v3/klines"
        params = {
            "symbol": symbol,
            "interval": "1d",
            "endTime": end_ts,
            "limit": 3
        }
        res = requests.get(url, params=params, timeout=15)
        data = res.json()

        if not isinstance(data, list) or len(data) < 1:
            return None

        # Previous completed daily candle EST
        prev_high = float(data[-1][2])
        print(f"📅 {symbol} Daily High (EST): ${prev_high:,.4f}")
        return prev_high

    except Exception as e:
        print(f"Daily high error {symbol}: {e}")
        return None

def check_15m_break(symbol, daily_high):
    try:
        data = get_candles(symbol, "15m", 10)
        if not data:
            return False
        last_close = float(data[-1][4])
        return last_close > daily_high
    except:
        return False

def check_5m_retest_and_candle(symbol, daily_high):
    try:
        data = get_candles(symbol, "5m", 20)
        if len(data) < 3:
            return False, False, None

        zone_low = daily_high * 0.99
        zone_high = daily_high * 1.01

        retest_found = False
        for candle in data[-5:]:
            low = float(candle[3])
            high = float(candle[2])
            if low <= zone_high and high >= zone_low:
                retest_found = True
                break

        if not retest_found:
            return False, False, None

        last = data[-1]
        prev = data[-2]

        o = float(last[1])
        h = float(last[2])
        l = float(last[3])
        c = float(last[4])

        prev_o = float(prev[1])
        prev_c = float(prev[4])

        body = abs(c - o)

        bullish_engulfing = (
            c > o and
            prev_c < prev_o and
            c > prev_o and
            o < prev_c
        )

        lower_wick = o - l if c > o else c - l
        upper_wick = h - c if c > o else h - o
        hammer = (
            c > o and
            lower_wick >= body * 2 and
            upper_wick <= body * 0.5
        )

        candle_confirmed = bullish_engulfing or hammer
        candle_type = "Bullish Engulfing" if bullish_engulfing else "Hammer" if hammer else None

        return retest_found, candle_confirmed, candle_type

    except Exception as e:
        print(f"Retest error {symbol}: {e}")
        return False, False, None

def scan_strategy2(coin):
    try:
        daily_high = get_daily_prev_high(coin)
        if not daily_high:
            return

        broke = check_15m_break(coin, daily_high)
        if not broke:
            print(f"➖ [S2] {coin} | No 15M Break")
            return

        retest, candle_ok, candle_type = check_5m_retest_and_candle(coin, daily_high)

        if retest and candle_ok:
            closes_5m = get_closes(coin, "5m", 20)
            msg = (
                f"🔥 <b>STRATEGY 2 SIGNAL!</b>\n\n"
                f"🪙 <b>{coin}</b>\n"
                f"━━━━━━━━━━━━━━\n"
                f"✅ Daily Prev High (EST): ${daily_high:,.4f}\n"
                f"✅ 15M Break Confirmed\n"
                f"✅ 5M Retest Zone (±1%)\n"
                f"✅ {candle_type}\n"
                f"━━━━━━━━━━━━━━\n"
                f"💰 Price: ${closes_5m[-1]:,.4f}\n"
                f"📊 Zone: ${daily_high*0.99:,.4f} — ${daily_high*1.01:,.4f}\n"
                f"⏰ {datetime.now(EST).strftime('%Y-%m-%d %H:%M EST')}"
            )
            send_telegram(msg)
            print(f"✅ [S2] Signal: {coin} | {candle_type}")
        elif retest and not candle_ok:
            print(f"➖ [S2] {coin} | Retest helay lkn candle waayay")
        else:
            print(f"➖ [S2] {coin} | Break helay lkn retest waayay")

    except Exception as e:
        print(f"Error [S2] {coin}: {e}")

# ── MAIN SCAN ─────────────────────────────────────────
def scan():
    print(f"\n🔍 Scan bilaabanaya — {datetime.now(EST).strftime('%H:%M:%S EST')}")

    for coin in COINS:
        try:
            # ════ STRATEGY 1: RSI DIVERGENCE ════
            closes_4h = get_closes(coin, "4h", 200)
            if len(closes_4h) < 50:
                print(f"❌ No 4H data: {coin}")
                continue
            rsis_4h = get_rsi_series(closes_4h)
            _, hidden_4h = detect_divergence(closes_4h[-40:], rsis_4h[-40:])

            if hidden_4h:
                closes_1h = get_closes(coin, "1h", 200)
                if len(closes_1h) < 50: continue
                rsis_1h = get_rsi_series(closes_1h)
                regular_1h, _ = detect_divergence(closes_1h[-40:], rsis_1h[-40:])
                candle_1h = candle_confirmation(closes_1h)

                if regular_1h and candle_1h:
                    msg = (f"⚡ <b>SIGNAL HELAY!</b>\n\n🪙 <b>{coin}</b>\n━━━━━━━━━━━━━━\n✅ 4H Hidden Bullish Div\n✅ 1H Regular Bullish Div\n✅ 1H Candle Confirmation\n━━━━━━━━━━━━━━\n💰 Price: ${closes_4h[-1]:,.4f}\n📊 RSI 4H: {rsis_4h[-1]:.1f}\n📊 RSI 1H: {rsis_1h[-1]:.1f}\n⏰ {datetime.now(EST).strftime('%Y-%m-%d %H:%M EST')}")
                    send_telegram(msg)
                    print(f"✅ [S1] 4H Hidden + 1H Regular: {coin}")
                    time.sleep(1)
                    continue

                closes_15m = get_closes(coin, "15m", 200)
                if len(closes_15m) < 50: continue
                rsis_15m = get_rsi_series(closes_15m)
                regular_15m, _ = detect_divergence(closes_15m[-40:], rsis_15m[-40:])
                candle_15m = candle_confirmation(closes_15m)

                if regular_15m and candle_15m:
                    msg = (f"⚡ <b>SIGNAL HELAY!</b>\n\n🪙 <b>{coin}</b>\n━━━━━━━━━━━━━━\n✅ 4H Hidden Bullish Div\n✅ 15M Regular Bullish Div\n✅ 15M Candle Confirmation\n━━━━━━━━━━━━━━\n💰 Price: ${closes_4h[-1]:,.4f}\n📊 RSI 4H: {rsis_4h[-1]:.1f}\n📊 RSI 15M: {rsis_15m[-1]:.1f}\n⏰ {datetime.now(EST).strftime('%Y-%m-%d %H:%M EST')}")
                    send_telegram(msg)
                    print(f"✅ [S1] 4H Hidden + 15M Regular: {coin}")
                    time.sleep(1)
                    continue

            else:
                closes_1h = get_closes(coin, "1h", 200)
                if len(closes_1h) < 50: continue
                rsis_1h = get_rsi_series(closes_1h)
                regular_1h, hidden_1h = detect_divergence(closes_1h[-40:], rsis_1h[-40:])

                if hidden_1h:
                    closes_15m = get_closes(coin, "15m", 200)
                    if len(closes_15m) < 50: continue
                    rsis_15m = get_rsi_series(closes_15m)
                    regular_15m, _ = detect_divergence(closes_15m[-40:], rsis_15m[-40:])
                    candle_15m = candle_confirmation(closes_15m)

                    if regular_15m and candle_15m:
                        msg = (f"⚡ <b>SIGNAL HELAY!</b>\n\n🪙 <b>{coin}</b>\n━━━━━━━━━━━━━━\n✅ 1H Hidden Bullish Div\n✅ 15M Regular Bullish Div\n✅ 15M Candle Confirmation\n━━━━━━━━━━━━━━\n💰 Price: ${closes_1h[-1]:,.4f}\n📊 RSI 1H: {rsis_1h[-1]:.1f}\n📊 RSI 15M: {rsis_15m[-1]:.1f}\n⏰ {datetime.now(EST).strftime('%Y-%m-%d %H:%M EST')}")
                        send_telegram(msg)
                        print(f"✅ [S1] 1H Hidden + 15M Regular: {coin}")
                        time.sleep(1)
                        continue

                    closes_5m = get_closes(coin, "5m", 200)
                    if len(closes_5m) < 50: continue
                    rsis_5m = get_rsi_series(closes_5m)
                    regular_5m, _ = detect_divergence(closes_5m[-40:], rsis_5m[-40:])
                    candle_5m = candle_confirmation(closes_5m)

                    if regular_5m and candle_5m:
                        msg = (f"⚡ <b>SIGNAL HELAY!</b>\n\n🪙 <b>{coin}</b>\n━━━━━━━━━━━━━━\n✅ 1H Hidden Bullish Div\n✅ 5M Regular Bullish Div\n✅ 5M Candle Confirmation\n━━━━━━━━━━━━━━\n💰 Price: ${closes_1h[-1]:,.4f}\n📊 RSI 1H: {rsis_1h[-1]:.1f}\n📊 RSI 5M: {rsis_5m[-1]:.1f}\n⏰ {datetime.now(EST).strftime('%Y-%m-%d %H:%M EST')}")
                        send_telegram(msg)
                        print(f"✅ [S1] 1H Hidden + 5M Regular: {coin}")
                        time.sleep(1)
                        continue

                else:
                    closes_15m = get_closes(coin, "15m", 200)
                    if len(closes_15m) < 50: continue
                    rsis_15m = get_rsi_series(closes_15m)
                    regular_15m, hidden_15m = detect_divergence(closes_15m[-40:], rsis_15m[-40:])

                    if hidden_15m:
                        closes_5m = get_closes(coin, "5m", 200)
                        if len(closes_5m) < 50: continue
                        rsis_5m = get_rsi_series(closes_5m)
                        regular_5m, _ = detect_divergence(closes_5m[-40:], rsis_5m[-40:])
                        candle_5m = candle_confirmation(closes_5m)

                        if regular_5m and candle_5m:
                            msg = (f"⚡ <b>SIGNAL HELAY!</b>\n\n🪙 <b>{coin}</b>\n━━━━━━━━━━━━━━\n✅ 15M Hidden Bullish Div\n✅ 5M Regular Bullish Div\n✅ 5M Candle Confirmation\n━━━━━━━━━━━━━━\n💰 Price: ${closes_15m[-1]:,.4f}\n📊 RSI 15M: {rsis_15m[-1]:.1f}\n📊 RSI 5M: {rsis_5m[-1]:.1f}\n⏰ {datetime.now(EST).strftime('%Y-%m-%d %H:%M EST')}")
                            send_telegram(msg)
                            print(f"✅ [S1] 15M Hidden + 5M Regular: {coin}")
                        else:
                            print(f"➖ {coin} | 15M Hidden lkn 5M Regular waayay")
                    else:
                        print(f"➖ {coin} | Signal ma jiro")

            # ════ STRATEGY 2: DAILY HIGH BREAK & RETEST ════
            scan_strategy2(coin)

            time.sleep(1)

        except Exception as e:
            print(f"Error {coin}: {e}")

# ── RUN ───────────────────────────────────────────────
if __name__ == "__main__":
    send_telegram("🤖 <b>Signal Bot Started!</b>\nScanning coins...")
    while True:
        scan()
        print("⏳ 5 daqiiqo sugaya...")
        time.sleep(300)
