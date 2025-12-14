import requests

BOT_TOKEN = "8072038057:AAG76HusATaqMFZwZOPUbo2NCHKr0TYngGU"  # Misol: 123456:ABC-DEF
WEBHOOK_URL = "https://botuchun-production.up.railway.app"  # Deploy qilingan URL

# Webhookni o'rnatish
response = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={WEBHOOK_URL}/{BOT_TOKEN}")
print(response.json())
response = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo")
print(response.json())
