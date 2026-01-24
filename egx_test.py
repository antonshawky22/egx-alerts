import os
from datetime import datetime
import requests

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram(text):
    if not TOKEN or not CHAT_ID:
        print("Telegram not configured")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": text}, timeout=10)
        print("Message sent:", text)
    except Exception as e:
        print("Telegram send failed:", e)

# سجل الاختبار
now = datetime.utcnow()
message = f"Test EGX Alerts - {now} UTC"
send_telegram(message)

# سجل في ملف
with open("test_log.txt", "a") as f:
    f.write(f"{now} - Test executed\n")
