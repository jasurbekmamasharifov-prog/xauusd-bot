import os
import time
import requests
from flask import Flask
import threading

# ==================== SOZLAMALAR ====================
TELEGRAM_BOT_TOKEN = "9271220348:AAFTAD+5HAi6FOFbSrgC3DYosd6n1ZNQEIU"
CHAT_ID = "638562670"

# ==================== FLASK SERVER (RENDER UCHUN) ====================
app = Flask(__name__)

@app.route('/')
def home():
    return "XAUUSD Scalping Bot ishlayapti va xavfsiz hududda! 🚀"

def run_web_server():
    app.run(host='0.0.0.0', port=10000)

web_thread = threading.Thread(target=run_web_server, daemon=True)
web_thread.start()

# ==================== TELEGRAM XABAR YUBORISH FUNKSIYASI ====================
def send_telegram_message(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Xabar yuborishda xatolik: {e}")

# ==================== ASOSIY BOT LOGIKASI ====================
def main_bot_loop():
    print("XAUUSD Scalping Bot ishga tushdi...")
    send_telegram_message("🤖 XAUUSD Scalping Bot muvaffaqiyatli ishga tushdi va 24/7 rejimga o'tdi!")
    
    while True:
        try:
            # Bu yerga o'zingizning tahlil mantiqingiz yoziladi
            time.sleep(3600)
        except Exception as e:
            print(f"Xatolik yuz berdi: {e}")
            time.sleep(60)

if __name__ == "__main__":
    bot_thread = threading.Thread(target=main_bot_loop, daemon=True)
    bot_thread.start()
    
    while True:
        time.sleep(1)
