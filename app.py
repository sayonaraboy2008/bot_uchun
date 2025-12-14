import os
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.environ.get("PORT", 5000))

flask_app = Flask(__name__)
tg_app = Application.builder().token(BOT_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot Railway’da ishlayapti ✅")

tg_app.add_handler(CommandHandler("start", start))

@flask_app.route(f"/{BOT_TOKEN}", methods=["POST"])
async def telegram_webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, tg_app.bot)
    await tg_app.update_queue.put(update)
    return "OK", 200

@flask_app.route("/")
def home():
    return "OK", 200

if __name__ == "__main__":
    async def setup():
        await tg_app.bot.set_webhook(f"{WEBHOOK_URL}/{BOT_TOKEN}")

    asyncio.run(setup())
    flask_app.run(host="0.0.0.0", port=PORT)
