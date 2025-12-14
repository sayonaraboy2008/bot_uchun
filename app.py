import os
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes
)

# =========================
#  ENV VARIABLES
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # https://xxxx.up.railway.app
PORT = int(os.environ.get("PORT", 5000))

# =========================
#  FLASK & TELEGRAM APP
# =========================
flask_app = Flask(__name__)
tg_app = Application.builder().token(BOT_TOKEN).build()

# =========================
#  /start HANDLER
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Salom! 👋\nBot Railway’da webhook orqali ishlayapti."
    )

tg_app.add_handler(CommandHandler("start", start))

# =========================
#  TELEGRAM WEBHOOK ROUTE
# =========================
@flask_app.route(f"/{BOT_TOKEN}", methods=["POST"])
async def telegram_webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, tg_app.bot)
    await tg_app.update_queue.put(update)
    return "OK", 200

# =========================
#  HEALTH CHECK
# =========================
@flask_app.route("/", methods=["GET"])
def home():
    return "Bot ishlayapti ✅", 200

# =========================
#  START APP
# =========================
if __name__ == "__main__":

    async def set_webhook():
        await tg_app.bot.set_webhook(f"{WEBHOOK_URL}/{BOT_TOKEN}")

    asyncio.run(set_webhook())

    flask_app.run(host="0.0.0.0", port=PORT)
