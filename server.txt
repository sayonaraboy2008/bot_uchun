import os
import telebot
from flask import Flask, request, jsonify

# ==========================
#  SOZLAMALAR
# ==========================

# Telegram bot tokenini va admin chat ID'ni Railway environment variables orqali oling
TOKEN = os.getenv("BOT_TOKEN")  # Masalan: 8072038057:AAG76HusATaqMFZwZOPUbo2NCHKr0TYngGU
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID","8101156971"))  # Default admin ID
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Masalan: https://web-production-d1af9.up.railway.app/

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ==========================
#  BOT BUYRUQLAR QISMI
# ==========================

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        "Assalomu alaykum! 😊\nBuyurtma berish uchun saytga o'ting:"
    )

# ==========================
#  FRONTEND → BOT API
# ==========================

@app.route("/api/buy", methods=["POST"])
def buy():
    data = request.get_json()
    product_id = data.get("productId")
    telegram_id = data.get("telegramId")

    if not product_id or not telegram_id:
        return jsonify({"ok": False, "msg": "Ma'lumot yetarli emas!"}), 400

    # ADMINga xabar yuborish
    bot.send_message(
        ADMIN_CHAT_ID,
        f"🛒 <b>Yangi buyurtma!</b>\n\n"
        f"📦 Mahsulot ID: <code>{product_id}</code>\n"
        f"👤 Foydalanuvchi: <code>{telegram_id}</code>",
        parse_mode="HTML"
    )

    return jsonify({"ok": True, "msg": "Buyurtma qabul qilindi!"})

# ==========================
#  WEBHOOK QISMI
# ==========================

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200

@app.route("/")
def home():
    return "Bot ishlayapti!", 200

# ==========================
#  APP ISHGA TUSHIRISH
# ==========================

if __name__ == "__main__":
    # Railway portni ishlatish
    port = int(os.environ.get("PORT", 5000))
    print(f"Server ishga tushdi! PORT: {port}")
    app.run(host="0.0.0.0", port=port)
