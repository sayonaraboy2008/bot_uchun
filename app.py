import os
from flask import Flask, request
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from dotenv import load_dotenv
from datetime import datetime

# .env fayldan o'qish
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))
CHANNEL_ID = os.getenv("CHANNEL_ID")

bot = Bot(BOT_TOKEN)
dispatcher = Dispatcher(bot, None, workers=0)

app = Flask(__name__)

# --- Ma'lumotlar ---
users_data = {}
purchase_counter = 0

# --- Klaviatura ---
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

# --- Buyruqlar ---
def start_command(update: Update, context):
    user = update.effective_user
    username = user.username or str(user.id)
    if username not in users_data:
        users_data[username] = {"orders": []}

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Open 🌐", url=WEBHOOK_URL)]])
    bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Salom {user.first_name}!\n\nDasturimizni ishga tushirish uchun pastdagi tugmani bosing.\nBuyruqlar paneli: /profile, /buy",
        reply_markup=keyboard
    )

def profile_command(update: Update, context):
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

    bot.send_message(chat_id=update.effective_chat.id, text=profile_text, reply_markup=get_keyboard())

def cancel_command(update: Update, context):
    bot.send_message(chat_id=update.effective_chat.id, text="Xarid jarayoni bekor qilindi.", reply_markup=get_keyboard())

def buy_command(update: Update, context):
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

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Open 🌐", url=WEBHOOK_URL)]])
    bot.send_message(chat_id=update.effective_chat.id, text=f"Buyurtma yaratildi! ID: {purchase_id}\nPastdagi tugma orqali saytingizni oching va chek yuboring.", reply_markup=keyboard)

# --- Chek rasmini qabul qilish ---
def upload_receipt(update: Update, context):
    user = update.effective_user
    username = user.username or str(user.id)

    if not update.message.photo:
        bot.send_message(chat_id=update.effective_chat.id, text="Iltimos, chek rasmini yuboring.")
        return

    if username not in users_data or not users_data[username]["orders"]:
        bot.send_message(chat_id=update.effective_chat.id, text="Sizda buyurtma topilmadi. Avval /buy bering.")
        return

    order = users_data[username]["orders"][-1]
    photo_file = update.message.photo[-1].get_file()
    os.makedirs("receipts", exist_ok=True)
    file_path = f"receipts/{order['purchase_id']}.jpg"
    photo_file.download(file_path)
    order["receipt"] = file_path

    # Admin va kanalga yuborish
    admin_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_{username}_{order['purchase_id']}")],
        [InlineKeyboardButton("❌ Rad etish", callback_data=f"deny_{username}_{order['purchase_id']}")],
        [InlineKeyboardButton(f"ℹ️ {order['purchase_id']}", callback_data=f"info_{username}_{order['purchase_id']}")]
    ])

    bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=open(order['receipt'], "rb"),
                   caption=f"@{username} tomonidan yuborilgan xarid:\nGift: {order['gift']}\nKim uchun: {order['for_user']}\nSummasi: {order['amount']} so'm\nID: {order['purchase_id']}",
                   reply_markup=admin_keyboard)

    msg = bot.send_photo(chat_id=CHANNEL_ID, photo=open(order['receipt'], "rb"),
                         caption=f"📦 @{username} tomonidan yuborilgan xarid\nGift: {order['gift']}\nKim uchun: {order['for_user']}\nSummasi: {order['amount']} so'm\nStatus: {order['status']}\nID: {order['purchase_id']}",
                         reply_markup=admin_keyboard)
    order["channel_msg_id"] = msg.message_id

    bot.send_message(chat_id=update.effective_chat.id, text="Chek adminga yuborildi, tasdiqlanishini kuting.", reply_markup=get_keyboard(show_cancel=True))

# --- Admin callback ---
def admin_callback(update: Update, context):
    query = update.callback_query
    query.answer()
    user_id = query.from_user.id
    data = query.data.split("_")
    action, username, purchase_id = data[0], data[1], data[2]

    if user_id != ADMIN_CHAT_ID:
        query.answer("Siz admin emassiz", show_alert=True)
        return

    order = next((o for o in users_data.get(username, {}).get("orders", []) if o["purchase_id"] == purchase_id), None)
    if not order:
        query.answer("Xarid topilmadi", show_alert=True)
        return

    if action == "approve":
        order["status"] = "tasdiqlangan"
    elif action == "deny":
        order["status"] = "bekor qilingan"
    elif action == "info":
        query.answer(f"Xarid ID: {order['purchase_id']}\nGift: {order['gift']}\nKim uchun: {order['for_user']}\nSummasi: {order['amount']} so'm\nSana: {order['date']}\nStatus: {order['status']}", show_alert=True)
        return

    if not order.get("notified", False):
        bot.send_message(chat_id=order["user_id"], text=f"Xaridingiz status o‘zgardi:\nGift: {order['gift']}\nKim uchun: {order['for_user']}\nStatus: {order['status']}", reply_markup=get_keyboard())
        order["notified"] = True

    if order.get("channel_msg_id"):
        bot.edit_message_caption(chat_id=CHANNEL_ID, message_id=order["channel_msg_id"],
                                 caption=f"📦 @{username} tomonidan yuborilgan xarid\nGift: {order['gift']}\nKim uchun: {order['for_user']}\nSummasi: {order['amount']} so'm\nStatus: {order['status']}\nID: {order['purchase_id']}")

    query.edit_message_caption(f"{query.message.caption}\n\nStatus: {order['status']}")

# --- Handler qo‘shish ---
dispatcher.add_handler(CommandHandler("start", start_command))
dispatcher.add_handler(CommandHandler("profile", profile_command))
dispatcher.add_handler(CommandHandler("buy", buy_command))
dispatcher.add_handler(CommandHandler("cancel", cancel_command))
dispatcher.add_handler(MessageHandler(filters.PHOTO, upload_receipt))
dispatcher.add_handler(CallbackQueryHandler(admin_callback))

# --- Webhook va Flask ---
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def telegram_webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, bot)
    dispatcher.process_update(update)
    return "OK", 200

@app.route("/")
def home():
    return "Bot ishga tushdi", 200

@app.before_first_request
def set_webhook():
    bot.set_webhook(f"{WEBHOOK_URL}/{BOT_TOKEN}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
