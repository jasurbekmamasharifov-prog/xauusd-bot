import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time
import requests
from datetime import datetime, timezone
import telebot
import traceback

# Render port talabini qondirish uchun kichik HTTP server
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"XAUUSD Bot is active and running 24/7!")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

# Serverni alohida oqimda (thread) ishga tushiramiz, shunda asosiy bot ishiga xalaqit bermaydi
server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()

BOT_TOKEN = "9271220348:AAFTADsHAI6F0FhSrgC3DYosd6n1ZMQElU"
ADMIN_CHAT_ID = 638562670

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

@bot.message_handler(commands=['stats'])
def send_statistics(message):
    try:
        text = (
            f"📊 **YUBorILGAN KUCHLI SIGNALLAR STATISTIKASI** 📊\n\n"
            f"📌 Jami yuborilgan signallar: **{stats_data['total_signals']}** ta\n"
            f"🟢 Foyda bilan yuborilgan (TP): **{stats_data['tp_count']}** ta\n"
            f"🔴 Zarar bilan yuborilgan (SL): **{stats_data['sl_count']}** ta"
        )
        bot.reply_to(message, text, parse_mode="Markdown")
    except Exception as e:
        print(f"Statistika xatosi: {e}")

@bot.message_handler(commands=['ping'])
def send_ping(message):
    try:
        bot.reply_to(message, "🟢 **Bot faol!** Yuqori aniqlikdagi Multi-Factor (RSI + EMA + MACD) strategiyasi ishlamoqda.")
    except Exception as e:
        print(f"Ping xatosi: {e}")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    save_user(chat_id)
    bot.reply_to(message, "👋 Assalamu alaykum! XAUUSD Ultra-Aniqlikdagi Strategik Botimiz ishga tushdi. Endi faqat eng kuchli signallar yuboriladi.")

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
        trade_id = trade['id']
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

    trade_type = None

    if current_price > ema_long and rsi < 38 and macd > 0:
        trade_type = "🟢 ULTRA BUY (Trend + RSI + MACD)"
        sl_price = round(current_price - 5.0, 2)
        tp_price = round(current_price + 12.0, 2)
    elif current_price < ema_long and rsi > 62 and macd < 0:
        trade_type = "🔴 ULTRA SELL (Trend + RSI + MACD)"
        sl_price = round(current_price + 5.0, 2)
        tp_price = round(current_price - 12.0, 2)

    if trade_type and can_send_signal():
        daily_signal_count += 1
        stats_data["total_signals"] += 1
        last_signal_time = datetime.now()

        signal_msg = (
            f"💎 **XAUUSD ULTRA-ANIQLIKDAGI SIGNAL** 💎\n\n"
            f"📊 **Savdo turi:** {trade_type}\n"
            f"🎯 **Kirish narxi:** {current_price}\n"
            f"🛑 **Stop Loss (SL):** {sl_price}\n"
            f"🎯 **Take Profit (TP):** {tp_price}\n"
            f"📈 **RSI ko'rsatkichi:** {round(rsi, 1)}\n"
            f"💡 **Holat:** Yuqori ehtimolli savdo ochildi..."
        )
        sent_map = send_signal_to_all_and_get_ids(signal_msg)

        active_trades.append({
            'id': daily_signal_count,
            'type': trade_type,
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
    print("Ultra-Aniqlikdagi Strategik Bot muvaffaqiyatli ishga tushdi...")
    while True:
        try:
            bot.infinity_polling(non_stop=True, interval=1, timeout=30, skip_pending=True)
        except Exception as e:
            print(f"Ulanish uzildi, qayta ulanmoqda: {e}")
            time.sleep(5)
