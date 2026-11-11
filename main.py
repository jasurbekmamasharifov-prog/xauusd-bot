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
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")  # Render Environment dan olinadi

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

# 3. GEMINI AI BILAN BOG'LANISH (Kutubxonasiz, to'g'ridan-to'g'ri HTTP orqali)
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
        print(f"AI So'rov xatosi: {e}")
    
    return True, "AI ulanishida vaqtinchalik xato, texnik filtr o'tdi."

# 4. TELEGRAM BUYRUQLARI
@bot.message_handler(commands=['stats'])
def send_statistics(message):
    try:
        text = (
            f"📊 **IA-ENHANCED SIGNAL STATISTIKASI** 📊\n\n"
            f"📌 Jami signallar: **{stats_data['total_signals']}** ta\n"
            f"🟢 TP: **{stats_data['tp_count']}** ta\n"
            f"🔴 SL: **{stats_data['sl_count']}** ta"
        )
        bot.reply_to(message, text, parse_mode="Markdown")
    except Exception as e:
        print(f"Statistika xatosi: {e}")

@bot.message_handler(commands=['ping'])
def send_ping(message):
    try:
        ai_status = "Faol va Ulangan 🤖" if GEMINI_API_KEY else "Kutilmoqda (API Key qo'shilmagan) ⚠️"
        bot.reply_to(message, f"🟢 **Bot faol!**\n💎 Strategiya: 10/20 punkt\n🧠 Gemini AI: {ai_status}")
    except Exception as e:
        print(f"Ping xatosi: {e}")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    save_user(chat_id)
    bot.reply_to(message, "👋 Assalamu alaykum! XAUUSD Sun'iy Intellekt Boshqaruvidagi Risk-Menedjment Botimiz ishga tushdi.")

@bot.message_handler(commands=['test'])
def send_test_signal(message):
    try:
        current_price = get_gold_price_safely()
        if not current_price:
            current_price = 4048.0

        sl_price = round(current_price - 10.0, 2)
        tp_price = round(current_price + 20.0, 2)

        signal_msg = (
            f"🧪 **TEST SIGNAL (GEMINI AI + $100)** 🧪\n\n"
            f"📊 **Savdo turi:** 🟢 ULTRA BUY (Test)\n"
            f"🎯 **Kirish narxi:** {current_price}\n"
            f"🛑 **Stop Loss (SL):** {sl_price} (-10.0 punkt)\n"
            f"🎯 **Take Profit (TP):** {tp_price} (+20.0 punkt)\n"
            f"🧠 **IA Tahlili:** 90%+ ehtimollik bilan tasdiqlandi\n"
            f"📈 **Holat:** Xavfsiz rejimda sinovdan o'tkazilmoqda..."
        )
        sent_map = send_signal_to_all_and_get_ids(signal_msg)
        bot.reply_to(message, "✅ IA test signali muvaffaqiyatli yuborildi!")
    except Exception as e:
        bot.reply_to(message, f"Test yuborishda xatolik: {e}")

def send_signal_to_all_and_get_ids(msg):
    users = load_users()
    sent_message_map = {}
    for chat_id in users:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"}
        try:
            res = requests.post(url, data=payload, timeout=15)
            if res.status_code == 200:
                sent_message_map[chat_id] = res.json()['result']['message_id']
        except Exception as e:
            print(f"Yuborishda xatolik ({chat_id}): {e}")
    return sent_message_map

def edit_message_for_all(sent_map, new_msg):
    for chat_id, msg_id in sent_map.items():
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
        payload = {"chat_id": chat_id, "message_id": msg_id, "text": new_msg, "parse_mode": "Markdown"}
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
            edit_message_for_all(sent_map, f"✅ **{t_type}**\n🎯 **TAKE PROFIT (TP) GA YETDI!**\nKirish: {entry}\nNatija: Muvaffaqiyatli foyda 🟢")
        elif hit_sl:
            stats_data["sl_count"] += 1
            edit_message_for_all(sent_map, f"❌ **{t_type}**\n🛑 **STOP LOSS (SL) GA TEGISHLI BO'LDI!**\nKirish: {entry}\nNatija: Zarar kesildi 🔴")
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
        raw_trade_type = "🟢 ULTRA BUY (Trend + RSI + MACD)"
        sl_price = round(current_price - 10.0, 2)
        tp_price = round(current_price + 20.0, 2)
    elif current_price < ema_long and rsi > 62 and macd < 0:
        raw_trade_type = "🔴 ULTRA SELL (Trend + RSI + MACD)"
        sl_price = round(current_price + 10.0, 2)
        tp_price = round(current_price - 20.0, 2)

    if raw_trade_type and can_send_signal():
        # IA orqali tekshiruvdan o'tkazamiz
        is_confirmed, ai_note = verify_signal_with_ai(raw_trade_type, current_price, rsi, macd, ema_short, ema_long)

        if is_confirmed:
            daily_signal_count += 1
            stats_data["total_signals"] += 1
            last_signal_time = datetime.now()

            signal_msg = (
                f"💎 **XAUUSD IA-VERIFIED SIGNAL ($100)** 💎\n\n"
                f"📊 **Savdo turi:** {raw_trade_type}\n"
                f"🎯 **Kirish narxi:** {current_price}\n"
                f"🛑 **Stop Loss (SL):** {sl_price} (-10.0 punkt)\n"
                f"🎯 **Take Profit (TP):** {tp_price} (+20.0 punkt)\n"
                f"🧠 **Gemini AI Xulosasi:** {ai_note}\n"
                f"📈 **RSI:** {round(rsi, 1)}"
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
        else:
            print(f"Signal AI tomonidan rad etildi: {ai_note}")

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
    print("IA Bilan Ishlaydigan Bot Boshlanmoqda...")
    while True:
        try:
            bot.remove_webhook()
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"Polling xatosi: {e}")
            time.sleep(5)
