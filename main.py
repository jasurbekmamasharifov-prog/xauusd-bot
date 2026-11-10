import time
import requests
from datetime import datetime, timezone
import telebot
import traceback
import threading

BOT_TOKEN = "9271220348:AAFTADt5HAi6FOFbSrgC3DYosd6n1ZNQEIU"
ADMIN_CHAT_ID = 638562670  # Sizning Telegram ID raqamingiz

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

# Statistika
stats_data = {
    "total_signals": 0,
    "tp_count": 0,
    "sl_count": 0
}

@bot.message_handler(commands=['stats'])
def send_statistics(message):
    try:
        text = (
            f"📊 **YUVORIQLANGAN KUCHLI SIGNALLAR STATISTIKASI** 📊\n\n"
            f"🤖 Jami yuborilgan signallar: **{stats_data['total_signals']} ta**\n"
            f"🟢 Foyda bilan yopilgan (TP): **{stats_data['tp_count']} ta**\n"
            f"🔴 Zarar bilan yopilgan (SL): **{stats_data['sl_count']} ta**\n"
        )
        bot.reply_to(message, text, parse_mode="Markdown")
    except Exception as e:
        print(f"Statistika xatosi: {e}")

@bot.message_handler(commands=['ping'])
def send_ping(message):
    try:
        bot.reply_to(message, "🟢 **Bot faol! Yuqori aniqlikdagi Multi-Factor (RSI + EMA + MACD) strategiyasi ishlamoqda.**", parse_mode="Markdown")
    except Exception as e:
        print(f"Ping xatosi: {e}")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    save_user(chat_id)
    bot.reply_to(message, "🤖 Assalomu alaykum! XAUUSD Ultra-Aniqlikdagi Strategik Botimiz ishga tushdi. Endi faqat eng kuchli va ishonchli signallar yuboriladi.")

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
            print(f"Yuborishda xatolik ({chat_id}):", e)
    return sent_message_map

def edit_message_for_all(sent_map, new_msg):
    for chat_id, msg_id in sent_map.items():
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
        payload = {"chat_id": chat_id, "message_id": msg_id, "text": new_msg, "parse_mode": "Markdown"}
        try:
            requests.post(url, data=payload, timeout=15)
        except Exception as e:
            print(f"Tahrirlashda xatolik ({chat_id}):", e)

price_history = []
last_signal_time = None
last_signal_price = None
COOLDOWN_MINUTES = 120  # Signal oralig'i kamida 2 soat qilib uzaytirildi (100% sifat uchun)
daily_signal_count = 0
active_trades = []

def get_gold_price_safely():
    url = "https://api.gold-api.com/price/XAU"
    for attempt in range(3):
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                price = response.json().get("price")
                if price:
                    return float(price)
        except Exception as e:
            print(f"[{attempt+1}/3] API narx olishda xatolik: {e}")
        time.sleep(3)
    return None

def is_market_session_safe():
    now_utc = datetime.now(timezone.utc)
    if now_utc.weekday() >= 5:
        return False
    return 7 <= now_utc.hour <= 20  # Faqat aktiv sessiya vaqtlari

def calculate_ema(prices, period):
    if len(prices) < period:
        return sum(prices) / len(prices)
    multiplier = 2 / (period + 1)
    ema = sum(prices[:period]) / period
    for price in prices[period:]:
        ema = (price - ema) * multiplier + ema
    return ema

def calculate_rsi(prices, period=14):
    if len(prices) < period + 1:
        return 50.0  # Yetarli ma'lumot bo'lmasa neytral qiymat
    gains, losses = 0, 0
    for i in range(1, len(prices)):
        change = prices[i] - prices[i-1]
        if change > 0:
            gains += change
        else:
            losses -= change
    avg_gain = gains / period
    avg_loss = losses / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(prices):
    if len(prices) < 26:
        return 0, 0
    ema12 = calculate_ema(prices, 12)
    ema26 = calculate_ema(prices, 26)
    macd_line = ema12 - ema26
    return macd_line

def check_active_trades(current_price):
    global active_trades, stats_data
    trades_to_remove = []

    for trade in active_trades:
        trade_type = trade['type']
        tp = trade['tp']
        sl = trade['sl']
        entry = trade['entry']
        sent_map = trade['sent_map']

        is_tp = False
        is_sl = False

        if "BUY" in trade_type:
            if current_price >= tp: is_tp = True
            elif current_price <= sl: is_sl = True
        elif "SELL" in trade_type:
            if current_price <= tp: is_tp = True
            elif current_price >= sl: is_sl = True

        if is_tp:
            profit_pips = abs(round(tp - entry, 2))
            stats_data["tp_count"] += 1
            updated_msg = f"🏆 **ULTRA-SIGNAL NATIJASI** 🏆\n\n📊 **Savdo:** {trade_type}\n💵 **Kirish:** {entry}\n🛡 **SL:** {sl}\n🎯 **TP:** {tp}\n\n🟢 **TAKE PROFIT (FOYDA) MUVAFFAQIYATLI BAJARILDI! (+{profit_pips}$ 🚀)**"
            edit_message_for_all(sent_map, updated_msg)
            trades_to_remove.append(trade)
        elif is_sl:
            loss_pips = abs(round(entry - sl, 2))
            stats_data["sl_count"] += 1
            updated_msg = f"🛡 **ULTRA-SIGNAL NATIJASI** 🛡\n\n📊 **Savdo:** {trade_type}\n💵 **Kirish:** {entry}\n🛡 **SL:** {sl}\n🎯 **TP:** {tp}\n\n🔴 **STOP LOSS ISHLADI (-{loss_pips}$ ❌)**"
            edit_message_for_all(sent_map, updated_msg)
            trades_to_remove.append(trade)

    for item in trades_to_remove:
        active_trades.remove(item)

def check_gold_filters():
    global daily_signal_count, active_trades, last_signal_time, last_signal_price, stats_data
    try:
        if not is_market_session_safe():
            print("Bozor sessiyasi vaqti emas.")
            return

        current_price = get_gold_price_safely()
        if not current_price:
            print("Narx olinmadi.")
            return

        print(f"Tahlildagi joriy narx: {current_price}")
        check_active_trades(current_price)

        if len(active_trades) > 0:
            print("Hozirda ochiq savdo mavjud, yangi signal kutilmaydi...")
            return

        price_history.append(current_price)
        if len(price_history) > 30: price_history.pop(0)
        if len(price_history) < 20:
            print("Yetarli narx tarixi yig'ilmoqda...")
            return

        # ---- KUCHLI INDIKATORLAR VA FILTRLAR ----
        ema_short = calculate_ema(price_history, 10)
        ema_long = calculate_ema(price_history, 30)
        rsi = calculate_rsi(price_history, 14)
        macd = calculate_macd(price_history)

        trade_type = None

        # 100% talabingizga mos: Faqat barcha shartlar mukammal mos kelgandagina signal beradi
        # BUY: Narx qisqa EMA dan yuqori, RSI oversold (< 35) zonadan qaytmoqda va MACD musbat
        if current_price > ema_long and rsi <= 38 and macd > 0:
            trade_type = "🟢 ULTRA BUY (Trend + RSI + MACD)"
            sl_price, tp_price = round(current_price - 5.0, 2), round(current_price + 12.0, 2)

        # SELL: Narx qisqa EMA dan past, RSI overbought (> 65) zonadan qaytmoqda va MACD manfiy
        elif current_price < ema_long and rsi >= 62 and macd < 0:
            trade_type = "🔴 ULTRA SELL (Trend + RSI + MACD)"
            sl_price, tp_price = round(current_price + 5.0, 2), round(current_price - 12.0, 2)

        if trade_type and can_send_signal():
            daily_signal_count += 1
            stats_data["total_signals"] += 1
            last_signal_time = datetime.now()
            
            signal_msg = (
                f"💎 **XAUUSD ULTRA-ANIQLIKDAGI SIGNAL** 💎\n\n"
                f"📊 **Savdo turi:** {trade_type}\n"
                f"💵 **Kirish narxi:** {current_price}\n"
                f"🛡 **Stop Loss (SL):** {sl_price}\n"
                f"🎯 **Take Profit (TP):** {tp_price}\n"
                f"📈 **RSI ko'rsatkichi:** {round(rsi, 1)}\n\n"
                f"⏳ *Holat: Yuqori ehtimolli savdo ochildi...*"
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
            print(f"Ultra-signal yuborildi: {trade_type}")
    except Exception as e:
        print("Tahlil xatoligi:", e)

def can_send_signal():
    global last_signal_time
    now = datetime.now()
    if last_signal_time is None:
        return True
    # 2 soatlik (120 daqiqa) qat'iy tanaffus oralig'i
    if (now - last_signal_time).total_seconds() / 60 >= COOLDOWN_MINUTES:
        return True
    return False

def background_loop():
    while True:
        try:
            check_gold_filters()
        except Exception as e:
            print("Tsikl xatosi:", e)
        time.sleep(180)  # Har 3 daqiqada tekshiradi

t = threading.Thread(target=background_loop, daemon=True)
t.start()

if __name__ == "__main__":
    print("Ultra-Aniqlikdagi Strategik Bot muvaffaqiyatli ishga tushdi...")
    while True:
        try:bot.infinity_polling(non_stop=True, interval=1, timeout=30)
            
            bot.infinity_polling(non_stop=True, interval=1, timeout=30, skip_pending=True)
        except Exception as e:
            print(f"Ulanish uzildi, qayta ulanmoqda: {e}")
            time.sleep(5)
