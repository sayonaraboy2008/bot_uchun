from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from datetime import datetime
import os

# --- TOKEN va chat ID lar ---
BOT_TOKEN = "8072038057:AAG76HusATaqMFZwZOPUbo2NCHKr0TYngGU"
ADMIN_CHAT_ID = 8101156971  # Admin Telegram ID
CHANNEL_ID = "-1003402792259"  # Kanal ID
WEB_APP_URL = "https://hadyaland.vercel.app/"

# --- Ma'lumotlar ---
users_data = {}  # {"username": {"orders": []}}
purchase_counter = 0  # Xaridlar uchun ID hisoblagichi

# --- Klaviatura ---
base_keyboard = [
    [KeyboardButton("/start")],
    [KeyboardButton("/profile")],
    [KeyboardButton("/buy")],
    [KeyboardButton("/cancel")]
]

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

# --- /start ---
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

# --- /profile ---
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

# --- /cancel ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Xarid jarayoni bekor qilindi.", reply_markup=get_keyboard())

# --- /buy ---
async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = user.username or str(user.id)
    if username not in users_data:
        users_data[username] = {"orders": []}

    # Yangi buyurtma yaratish
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
    await send_to_admin_and_channel(order, username, context)
    await update.message.reply_text("Chek adminga yuborildi, tasdiqlanishini kuting.", reply_markup=get_keyboard(show_cancel=True))

# --- Admin va kanalga yuborish ---
async def send_to_admin_and_channel(order, username, context):
    admin_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_{username}_{order['purchase_id']}")],
        [InlineKeyboardButton("❌ Rad etish", callback_data=f"deny_{username}_{order['purchase_id']}")],
        [InlineKeyboardButton(f"ℹ️ {order['purchase_id']}", callback_data=f"info_{username}_{order['purchase_id']}")]
    ])

    # Admin chat
    await context.bot.send_photo(
        chat_id=ADMIN_CHAT_ID,
        photo=open(order['receipt'], "rb"),
        caption=f"@{username} tomonidan yuborilgan xarid:\nGift: {order['gift']}\nKim uchun: {order['for_user']}\nSummasi: {order['amount']} so'm\nID: {order['purchase_id']}",
        reply_markup=admin_keyboard
    )

    # Kanal
    msg = await context.bot.send_photo(
        chat_id=CHANNEL_ID,
        photo=open(order['receipt'], "rb"),
        caption=f"📦 @{username} tomonidan yuborilgan xarid\nGift: {order['gift']}\nKim uchun: {order['for_user']}\nSummasi: {order['amount']} so'm\nStatus: {order['status']}\nID: {order['purchase_id']}",
        reply_markup=admin_keyboard
    )
    order["channel_msg_id"] = msg.message_id

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
        await query.answer(
            f"Xarid ID: {order['purchase_id']}\nGift: {order['gift']}\nKim uchun: {order['for_user']}\nSummasi: {order['amount']} so'm\nSana: {order['date']}\nStatus: {order['status']}",
            show_alert=True
        )
        return

    if not order.get("notified", False):
        await context.bot.send_message(
            chat_id=order["user_id"],
            text=f"Xaridingiz status o‘zgardi:\nGift: {order['gift']}\nKim uchun: {order['for_user']}\nStatus: {order['status']}",
            reply_markup=get_keyboard(show_cancel=False)
        )
        order["notified"] = True

    if order.get("channel_msg_id"):
        await context.bot.edit_message_caption(
            chat_id=CHANNEL_ID,
            message_id=order["channel_msg_id"],
            caption=f"📦 @{username} tomonidan yuborilgan xarid\nGift: {order['gift']}\nKim uchun: {order['for_user']}\nSummasi: {order['amount']} so'm\nStatus: {order['status']}\nID: {order['purchase_id']}"
        )

    await query.edit_message_caption(f"{query.message.caption}\n\nStatus: {order['status']}")

# --- MAIN ---
if __name__ == "__main__":
    os.makedirs("receipts", exist_ok=True)
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("buy", buy))
    app.add_handler(MessageHandler(filters.PHOTO, upload_receipt))
    app.add_handler(CallbackQueryHandler(admin_callback))

    print("Bot ishga tushdi...")
    app.run_polling()
