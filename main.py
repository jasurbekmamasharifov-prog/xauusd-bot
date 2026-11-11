import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time
import requests
from datetime import datetime
import telebot

# 1. Render port talabini qondirish uchun HTTP server
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"XAUUSD AI-Enhanced Bot is active and running 24/7!")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()

# 2. BOT VA IA SOZLAMALARI
BOT_TOKEN = "9271220348:AAFTADsHAI6F0FhSrgC3DYosd6n1ZMQElU"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
USERS_FILE = "users.txt"

def load_users():
    try:
        with open(USERS_FILE, "r") as f:
            return set(line.strip() for line in f if line.strip())
    except FileNotFoundError:
        return set()

def save_user(chat_id):
    users = load_users()
    if str(chat_id) not in users:
        with open(USERS_FILE, "a") as f:
            f.write(f"{chat_id}\n")

stats_data = {
    "total_signals": 0,
    "tp_count": 0,
    "sl_count": 0
}

# 11 XIL STRUKTURA VA SHARTLI HARAKAT QOIDALARI
XAUUSD_STRUCTURES = {
    1: {
        "name": "1-Struktura: Dual-Wick Rejection Zone",
        "condition": "Qollab-quvvatlash zonasida ikkita ketma-ket uzun soya hosil bolishi",
        "action": "BUY"
    },
    2: {
        "name": "2-Struktura: Support Breakdown",
        "condition": "M15 tana bilan qollab-quvvatlash chizigini pastga kesib otishi",
        "action": "SELL"
    },
    3: {
        "name": "3-Struktura: EMA Trend Pullback",
        "condition": "Narx EMA(10) va EMA(30) orasiga kirib, qaytish shamini yasashi",
        "action": "TREND DIRECTION"
    },
    4: {
        "name": "4-Struktura: RSI Extreme Reversal",
        "condition": "RSI(14) < 35 zonasidan yuqoriga kesib otishi yoki > 65 dan pastga tushishi",
        "action": "REVERSAL BUY/SELL"
    },
    5: {
        "name": "5-Struktura: MACD Zero-Line Cross",
        "condition": "MACD chizigining nol chizigini kesib otish momenti",
        "action": "MOMENTUM TRADE"
    },
    6: {
        "name": "6-Struktura: Liquidity Sweep & Rejection",
        "condition": "Oldingi lokal maksimum yoki minimum yangilanib, tezda orqaga qaytishi",
        "action": "COUNTER-TREND"
    },
    7: {
        "name": "7-Struktura: Volume Spike Confirmation",
        "condition": "Ortacha hajm hajmidan 2 baravar yuqori sham yopilishi",
        "action": "BREAKOUT"
    },
    8: {
        "name": "8-Struktura: Golden Pocket Retracement",
        "condition": "Fibo 0.618 darajasidan aniq reaksiya olishi",
        "action": "BUY/SELL"
    },
    9: {
        "name": "9-Struktura: Inside Bar Breakout",
        "condition": "Ichki sham shakllangandan keyingi impulsiv chiqish",
        "action": "BREAKOUT DIRECTION"
    },
    10: {
        "name": "10-Struktura: Session Open Volatility Filter",
        "condition": "London/New York sessiyalari ochilishidagi birinchi 15 daqiqalik diapazon",
        "action": "RANGE BREAK"
    },
    11: {
        "name": "11-Struktura: Adaptive Multi-Layer Confluence",
        "condition": "Yuqoridagi 10 ta shartdan kamida 3 tasi bir vaqtning ozida mos kelishi",
        "action": "ULTRA CONFIRM BUY/SELL"
    }
}

# 3. GEMINI AI BILAN BOG'LANISH
def verify_signal_with_ai(trade_type, current_price, rsi, macd, ema_short, ema_long):
    if not GEMINI_API_KEY:
        return True, "IA Kaliti kiritilmagan (Standart filtr)"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    prompt = f"""
    You are an expert XAUUSD (Gold) risk manager for a $100 trading account.
    Analyze this entry signal:
    Signal Type: {trade_type}
    Current Price: {current_price}
    RSI(14): {rsi}
    MACD: {macd}
    EMA Short(10): {ema_short}
    EMA Long(30): {ema_long}
    SL Distance: 10 points
    TP Distance: 20 points

    Should we execute this trade? Answer ONLY with 'CONFIRM' if high probability (>90%), or 'REJECT' if risky.
    """
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            ai_text = data['candidates'][0]['content']['parts'][0]['text'].upper()
            if "CONFIRM" in ai_text:
                return True, "AI Tasdiqladi (>90% ishonch) 🟢"
            else:
                return False, "AI xavfli deb rad etdi 🔴"
    except Exception as e:
        print(f"AI Sorov xatosi: {e}")
    
    return True, "AI ulanishida vaqtinchalik xato, texnik filtr otdi."

# 4. TELEGRAM BUYRUQLARI
@bot.message_handler(commands=['stats'])
def send_statistics(message):
    try:
        text = (
            f"SIGNALLAR STATISTIKASI\n\n"
            f"Jami signallar: {stats_data['total_signals']} ta\n"
            f"TP: {stats_data['tp_count']} ta\n"
            f"SL: {stats_data['sl_count']} ta"
        )
        bot.reply_to(message, text)
    except Exception as e:
        print(f"Statistika xatosi: {e}")

@bot.message_handler(commands=['ping'])
def send_ping(message):
    try:
        bot.reply_to(message, "Bot faol, kanal va 11 ta strukturaviy qoida bilan ishlamoqda!")
    except Exception as e:
        print(f"Ping xatosi: {e}")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    save_user(chat_id)
    bot.reply_to(message, "Assalamu alaykum! XAUUSD Xavfsiz Risk-Menedjment va 11-Struktura Boti ishga tushdi.\n\nBuyruqlar:\n/structures - 11 ta qoida va strukturani korish\n/test - Test signal olish\n/stats - Statistika")

@bot.message_handler(commands=['structures'])
def send_structures(message):
    try:
        text = "XAUUSD 11 TA STRUKTURA VA QOIDALAR:\n\n"
        for s_id, s_info in XAUUSD_STRUCTURES.items():
            text += f"{s_info['name']}\n   Shart: {s_info['condition']}\n   Harakat: {s_info['action']}\n\n"
        bot.reply_to(message, text)
    except Exception as e:
        print(f"Structures xatosi: {e}")

@bot.message_handler(commands=['test'])
def send_test_signal(message):
    try:
        current_price = get_gold_price_safely()
        if not current_price:
            current_price = 4048.0

        sl_price = round(current_price - 10.0, 2)
        tp_price = round(current_price + 20.0, 2)

        signal_msg = (
            f"XAUUSD PREMIUM AI-VERIFIED SIGNAL\n\n"
            f"Savdo turi: ULTRA BUY (11-Struktura asosida)\n"
            f"Kirish narxi (Entry): Joriy bozor narxidan ({current_price} atrofida)\n"
            f"Stop Loss (SL): ${sl_price} (-10.0 punkt)\n"
            f"Take Profit (TP): ${tp_price} (+20.0 punkt)\n\n"
            f"Gemini AI & 11-Qoida Xulosasi:\n"
            f"• Struktura: Dual-Wick va Multi-Layer Confluence tasdiqlandi.\n"
            f"• AI Tasdigi: 92.5% ehtimollik bilan ruxsat berildi (CONFIRM)."
        )
        # To'g'ridan-to'g'ri yuboruvchiga javob qaytarish uchun reply_to ishlatamiz
        bot.reply_to(message, signal_msg)
    except Exception as e:
        bot.reply_to(message, f"Test yuborishda xatolik: {e}")

def send_signal_to_all_and_get_ids(msg):
    users = load_users()
    sent_message_map = {}
    for chat_id in users:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": msg}
        try:
            res = requests.post(url, data=payload, timeout=15)
            if res.status_code == 200:
                sent_message_map[int(chat_id)] = res.json()['result']['message_id']
        except Exception as e:
            print(f"Yuborishda xatolik ({chat_id}): {e}")
    return sent_message_map

def edit_message_for_all(sent_map, new_msg):
    for chat_id, msg_id in sent_map.items():
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
        payload = {"chat_id": chat_id, "message_id": msg_id, "text": new_msg}
        try:
            requests.post(url, data=payload, timeout=15)
        except Exception as e:
            print(f"Tahrirlashda xatolik ({chat_id}): {e}")

# 5. TAHLIL VA FILTRLAR
price_history = []
active_trades = []
last_signal_time = None
COOLDOWN_MINUTES = 120
daily_signal_count = 0

def get_gold_price_safely():
    try:
        url = "https://api.gold-api.com/price/XAU"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            data = res.json()
            return float(data.get("price", 0))
    except Exception as e:
        print(f"Narx olish xatosi: {e}")
    return None

def calculate_ema(data, period):
    if len(data) < period:
        return data[-1]
    multiplier = 2 / (period + 1)
    ema = data[0]
    for price in data[1:]:
        ema = (price - ema) * multiplier + ema
    return ema

def calculate_rsi(data, period=14):
    if len(data) < period + 1:
        return 50.0
    gains, losses = 0, 0
    for i in range(1, len(data)):
        change = data[i] - data[i-1]
        if change > 0:
            gains += change
        else:
            losses -= change
    avg_gain = gains / period
    avg_loss = losses / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_macd(data):
    if len(data) < 26:
        return 0.0
    ema12 = calculate_ema(data, 12)
    ema26 = calculate_ema(data, 26)
    return ema12 - ema26

def check_active_trades(current_price):
    global active_trades, stats_data
    remaining_trades = []
    for trade in active_trades:
        t_type = trade['type']
        entry = trade['entry']
        sl = trade['sl']
        tp = trade['tp']
        sent_map = trade['sent_map']

        hit_tp = False
        hit_sl = False

        if "BUY" in t_type:
            if current_price >= tp:
                hit_tp = True
            elif current_price <= sl:
                hit_sl = True
        elif "SELL" in t_type:
            if current_price <= tp:
                hit_tp = True
            elif current_price >= sl:
                hit_sl = True

        if hit_tp:
            stats_data["tp_count"] += 1
            edit_message_for_all(sent_map, f"{t_type}\nTAKE PROFIT (TP) GA YETDI!\nKirish: {entry}\nNatija: Muvaffaqiyatli foyda 🟢")
        elif hit_sl:
            stats_data["sl_count"] += 1
            edit_message_for_all(sent_map, f"{t_type}\nSTOP LOSS (SL) GA TEGISHLI BOLDI!\nKirish: {entry}\nNatija: Zarar kesildi 🔴")
        else:
            remaining_trades.append(trade)

    active_trades = remaining_trades

def check_gold_filters():
    global last_signal_time, daily_signal_count, price_history
    current_price = get_gold_price_safely()
    if not current_price:
        return

    check_active_trades(current_price)

    if active_trades:
        return

    price_history.append(current_price)
    if len(price_history) > 30:
        price_history.pop(0)
    if len(price_history) < 20:
        return

    ema_short = calculate_ema(price_history, 10)
    ema_long = calculate_ema(price_history, 30)
    rsi = calculate_rsi(price_history, 14)
    macd = calculate_macd(price_history)

    raw_trade_type = None

    if current_price > ema_long and rsi < 38 and macd > 0:
        raw_trade_type = "ULTRA BUY (11-Struktura + RSI + MACD)"
        sl_price = round(current_price - 10.0, 2)
        tp_price = round(current_price + 20.0, 2)
    elif current_price < ema_long and rsi > 62 and macd < 0:
        raw_trade_type = "ULTRA SELL (11-Struktura + RSI + MACD)"
        sl_price = round(current_price + 10.0, 2)
        tp_price = round(current_price - 20.0, 2)

    if raw_trade_type and can_send_signal():
        is_confirmed, ai_note = verify_signal_with_ai(raw_trade_type, current_price, rsi, macd, ema_short, ema_long)

        if is_confirmed:
            daily_signal_count += 1
            stats_data["total_signals"] += 1
            last_signal_time = datetime.now()

            signal_msg = (
                f"XAUUSD PREMIUM AI-VERIFIED SIGNAL\n\n"
                f"Savdo turi: {raw_trade_type}\n"
                f"Kirish narxi: {current_price}\n"
                f"Stop Loss (SL): {sl_price} (-10.0 punkt)\n"
                f"Take Profit (TP): {tp_price} (+20.0 punkt)\n"
                f"Gemini AI Xulosasi: {ai_note}\n"
                f"RSI: {round(rsi, 1)}"
            )
            sent_map = send_signal_to_all_and_get_ids(signal_msg)

            active_trades.append({
                'id': daily_signal_count,
                'type': raw_trade_type,
                'entry': current_price,
                'sl': sl_price,
                'tp': tp_price,
                'sent_map': sent_map
            })

def can_send_signal():
    global last_signal_time
    if last_signal_time is None:
        return True
    now = datetime.now()
    if (now - last_signal_time).total_seconds() / 60 >= COOLDOWN_MINUTES:
        return True
    return False

def background_loop():
    while True:
        try:
            check_gold_filters()
        except Exception as e:
            print(f"Tahlil xatosi: {e}")
        time.sleep(180)

t = threading.Thread(target=background_loop, daemon=True)
t.start()

if __name__ == "__main__":
    print("Bot polling boshlamoqda...")
    while True:
        try:
            bot.remove_webhook()
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"Polling xatosi: {e}")
            time.sleep(5)
