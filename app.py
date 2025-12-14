import os
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from datetime import datetime

BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]
ADMIN_CHAT_ID = int(os.environ["ADMIN_CHAT_ID"])
CHANNEL_ID = os.environ["CHANNEL_ID"]

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
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = user.username or str(user.id)
    if username not in users_data:
        users_data[username] = {"orders": []}

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Open 🌐", url=WEBHOOK_URL)]])
    await update.message.reply_text(
        f"Salom {user.first_name}!\nDasturimiz ishga tushdi!\nBuyruqlar: /profile, /buy",
        reply_markup=keyboard
    )

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = user.username or str(user.id)
    orders = users_data.get(username, {"orders": []})["orders"]

    text = "👤 Profilingiz:\n\n🛒 Buyurtmalar tarixi:\n"
    if orders:
        for o in orders:
            text += (
                f"{o['purchase_id']} - {o['gift']}\n"
                f"   Kim uchun: {o['for_user']}\n"
                f"   Summasi: {o['amount']} so'm\n"
                f"   Sana: {o['date']}\n"
                f"   Holati: {o.get('status','kutmoqda')}\n\n"
            )
    else:
        text += "Siz hali hech narsa sotib olmadingiz."
    await update.message.reply_text(text, reply_markup=get_keyboard())

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Xarid jarayoni bekor qilindi.", reply_markup=get_keyboard())

async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    await update.message.reply_text(
        f"Buyurtma yaratildi! ID: {purchase_id}\nPastdagi tugma orqali saytingizni oching va chek yuboring.",
        reply_markup=keyboard
    )

# --- Chek rasmini qabul qilish ---
async def upload_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = user.username or str(user.id)

    if not update.message.photo:
        await update.message.reply_text("Iltimos, chek rasmini yuboring.")
        return

    if username not in users_data or not users_data[username]["orders"]:
        await update.message.reply_text("Sizda buyurtma topilmadi. Avval /buy bering.")
        return

    order = users_data[username]["orders"][-1]
    photo_file = await update.message.photo[-1].get_file()
    os.makedirs("receipts", exist_ok=True)
    file_path = f"receipts/{order['purchase_id']}.jpg"
    await photo_file.download_to_drive(file_path)
    order["receipt"] = file_path

    # Admin va kanalga yuborish
    admin_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_{username}_{order['purchase_id']}")],
        [InlineKeyboardButton("❌ Rad etish", callback_data=f"deny_{username}_{order['purchase_id']}")],
        [InlineKeyboardButton(f"ℹ️ {order['purchase_id']}", callback_data=f"info_{username}_{order['purchase_id']}")]
    ])

    await context.bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=open(order['receipt'], "rb"),
                   caption=f"@{username} tomonidan yuborilgan xarid:\nGift: {order['gift']}\nKim uchun: {order['for_user']}\nSummasi: {order['amount']} so'm\nID: {order['purchase_id']}",
                   reply_markup=admin_keyboard)

    msg = await context.bot.send_photo(chat_id=CHANNEL_ID, photo=open(order['receipt'], "rb"),
                         caption=f"📦 @{username} tomonidan yuborilgan xarid\nGift: {order['gift']}\nKim uchun: {order['for_user']}\nSummasi: {order['amount']} so'm\nStatus: {order['status']}\nID: {order['purchase_id']}",
                         reply_markup=admin_keyboard)
    order["channel_msg_id"] = msg.message_id

    await update.message.reply_text("Chek adminga yuborildi, tasdiqlanishini kuting.", reply_markup=get_keyboard(show_cancel=True))

# --- Admin callback ---
async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data.split("_")
    action, username, purchase_id = data[0], data[1], data[2]

    if user_id != ADMIN_CHAT_ID:
        await query.answer("Siz admin emassiz", show_alert=True)
        return

    order = next((o for o in users_data.get(username, {}).get("orders", []) if o["purchase_id"] == purchase_id), None)
    if not order:
        await query.answer("Xarid topilmadi", show_alert=True)
        return

    if action == "approve":
        order["status"] = "tasdiqlangan"
    elif action == "deny":
        order["status"] = "bekor qilingan"
    elif action == "info":
        await query.answer(f"Xarid ID: {order['purchase_id']}\nGift: {order['gift']}\nKim uchun: {order['for_user']}\nSummasi: {order['amount']} so'm\nSana: {order['date']}\nStatus: {order['status']}", show_alert=True)
        return

    if not order.get("notified", False):
        await context.bot.send_message(chat_id=order["user_id"], text=f"Xaridingiz status o‘zgardi:\nGift: {order['gift']}\nKim uchun: {order['for_user']}\nStatus: {order['status']}", reply_markup=get_keyboard())
        order["notified"] = True

    if order.get("channel_msg_id"):
        await context.bot.edit_message_caption(chat_id=CHANNEL_ID, message_id=order["channel_msg_id"],
                                 caption=f"📦 @{username} tomonidan yuborilgan xarid\nGift: {order['gift']}\nKim uchun: {order['for_user']}\nSummasi: {order['amount']} so'm\nStatus: {order['status']}\nID: {order['purchase_id']}")

    await query.edit_message_caption(f"{query.message.caption}\n\nStatus: {order['status']}")

# --- Application ---
app_builder = ApplicationBuilder().token(BOT_TOKEN).build()
app_builder.add_handler(CommandHandler("start", start_command))
app_builder.add_handler(CommandHandler("profile", profile_command))
app_builder.add_handler(CommandHandler("buy", buy_command))
app_builder.add_handler(CommandHandler("cancel", cancel_command))
app_builder.add_handler(MessageHandler(filters.PHOTO, upload_receipt))
app_builder.add_handler(CallbackQueryHandler(admin_callback))

# --- Flask webhook ---
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def telegram_webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, app_builder.bot)
    app_builder.update_queue.put(update)
    return "OK", 200

@app.route("/")
def home():
    return "Bot ishga tushdi", 200

@app.before_first_request
def set_webhook():
    app_builder.bot.set_webhook(f"{WEBHOOK_URL}/{BOT_TOKEN}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
