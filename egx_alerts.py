print("EGX BOT TEST START")

import os
import requests

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram(msg):
    if not TOKEN or not CHAT_ID:
        raise Exception("Missing Telegram ENV")
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    r = requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": msg
    })
    print("Telegram response:", r.text)

send_telegram("✅ GitHub Actions test message")
