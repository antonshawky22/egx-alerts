import os, requests

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

print("TOKEN:", "OK" if TOKEN else "MISSING")
print("CHAT_ID:", "OK" if CHAT_ID else "MISSING")

url = f"https://api.telegram.org/bot{TOKEN}/getMe"
r = requests.get(url)
print(r.text)

exit()
