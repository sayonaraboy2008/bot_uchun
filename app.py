# app.py
import os
from flask import Flask, request
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from datetime import datetime
import asyncio

# =======================
#  SOZLAMALAR
# =======================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", "8101156971"))
CHANNEL_ID = os.environ.get("CHANNEL_ID", "-100xxxxxxxxxx")
WEB_APP_URL = os.environ.get("WEB_APP_URL", "https://sizning-app.railway.app")

bot = Bot(token=BOT_TOKEN)
app = Flask(__name__)

users_data = {}
purchase_counter = 0

# =======================
#  KLAVIATURA
# =======================
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

# =======================
#  HANDLERLAR
# =======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = user.username or str(user.id)
    if username not in users_data:
        users_data[username] = {"orders": []}

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Open 🌐", url=WEB_APP_URL)]])
    await update.message.reply_text(
        f"Salom {user.first_name}!\n\nDasturimizni ishga tushirish uchun pastdagi tugmani bosing.\n\nBuyruqlar paneli: /profile, /buy",
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

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Xarid jarayoni bekor qilindi.", reply_markup=get_keyboard())

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
        f"Buyurtma yaratildi! ID: {purchase_id}\n\nPastdagi tugma orqali saytingizni oching va chek yuboring.",
        reply_markup=keyboard
    )

# =======================
#  FLASK ROUTE
# =======================
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, bot)
    asyncio.run(dispatcher.process_update(update))
    return "ok", 200

@app.route("/")
def home():
    return "Bot ishlayapti!", 200

# =======================
#  Telegram dispatcher
# =======================
dispatcher = ApplicationBuilder().token(BOT_TOKEN).build()
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("profile", profile))
dispatcher.add_handler(CommandHandler("cancel", cancel))
dispatcher.add_handler(CommandHandler("buy", buy))

# =======================
#  APP ISHGA TUSHIRISH
# =======================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
