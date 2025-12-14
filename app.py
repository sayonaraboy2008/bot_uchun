from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from datetime import datetime
import os

# ==========================
#  SOZLAMALAR (hammasi shu yerda)
# ==========================
BOT_TOKEN = "8072038057:AAG76HusATaqMFZwZOPUbo2NCHKr0TYngGU"  # BotFather token
ADMIN_CHAT_ID = 8101156971                                     # Admin ID
CHANNEL_ID = "-1003402792259"                                   # Kanal ID
WEB_APP_URL = "https://botuchun-production.up.railway.app"                 # Frontend URL

# ==========================
#  MA'LUMOTLAR
# ==========================
users_data = {}  # Foydalanuvchilar ma'lumotlari
purchase_counter = 0  # Buyurtma ID hisoblagichi

# ==========================
#  KLAVIATURA
# ==========================
def get_keyboard(show_cancel=False):
    keyboard = [
        [KeyboardButton("/start")],
        [KeyboardButton("/profile")],
        [KeyboardButton("/buy")]
    ]
    if show_cancel:
        keyboard.append([KeyboardButton("/cancel")])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

def generate_purchase_id():
    global purchase_counter
    purchase_counter += 1
    return f"#{purchase_counter:06d}"

# ==========================
#  BOT HANDLERLAR
# ==========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = user.username or str(user.id)
    if username not in users_data:
        users_data[username] = {"orders": []}

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Open 🌐", url=WEB_APP_URL)]])
    await update.message.reply_text(
        f"Salom {user.first_name}!\nDasturimizni ishga tushirish uchun pastdagi tugmani bosing.\nBuyruqlar paneli: /profile, /buy",
        reply_markup=keyboard
    )

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = user.username or str(user.id)
    if username not in users_data:
        users_data[username] = {"orders": []}

    orders = users_data[username]["orders"]
    profile_text = f"👤 Profilingiz:\n\n🛒 Buyurtmalar tarixi:\n"
    if orders:
        for order in orders:
            profile_text += (
                f"{order['purchase_id']} - Gift: {order['gift']}\n"
                f"   Kim uchun: {order['for_user']}\n"
                f"   Summasi: {order['amount']} so'm\n"
                f"   Sana: {order['date']}\n"
                f"   Holati: {order.get('status','kutmoqda')}\n\n"
            )
    else:
        profile_text += "Siz hali hech narsa sotib olmadingiz."
    await update.message.reply_text(profile_text, reply_markup=get_keyboard())

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = user.username or str(user.id)
    if username not in users_data:
        users_data[username] = {"orders": []}

    purchase_id = generate_purchase_id()
    order = {
        "purchase_id": purchase_id,
        "gift": "Test Gift",
        "for_user": username,
        "amount": 10000,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "status": "kutmoqda",
        "user_id": user.id
    }
    users_data[username]["orders"].append(order)

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Open 🌐", url=WEB_APP_URL)]])
    await update.message.reply_text(
        f"Buyurtma yaratildi! ID: {purchase_id}\nPastdagi tugma orqali saytingizni oching va chek yuboring.",
        reply_markup=keyboard
    )

# ==========================
#  FLASK SERVER
# ==========================
app = Flask(__name__)
bot_app = ApplicationBuilder().token(BOT_TOKEN).build()

# Handlerlarni qo'shamiz
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("profile", profile))
bot_app.add_handler(CommandHandler("buy", buy))

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot_app.bot)
    bot_app.process_update(update)
    return "OK"

@app.route("/")
def home():
    return "Bot ishlayapti!", 200

# ==========================
#  SERVERNI ISHGA TUSHIRISH
# ==========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Server ishga tushdi! PORT: {port}")
    app.run(host="0.0.0.0", port=port)
