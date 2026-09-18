import requests
import time
import threading
from flask import Flask

# আপনার দেওয়া তথ্যসমূহ
API_URL = "https://numberpanel.tech/api/otp?count=200"
BOT_TOKEN = "8557102458:AAFcn39gwfbwf-njflJNRwX75quc-5YeS5Q"
GROUP_CHAT_ID = "-5415927433"

sent_codes = set()
app = Flask(__name__)

def send_to_telegram(message):
    telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": GROUP_CHAT_ID, "text": message}
    try:
        requests.post(telegram_url, data=payload)
    except Exception as e:
        print(f"টেলিগ্রামে মেসেজ পাঠাতে সমস্যা হয়েছে: {e}")

def check_for_new_code():
    try:
        response = requests.get(API_URL)
        data = response.json() 

        if isinstance(data, list):
            for item in data:
                code = str(item.get("code") or item.get("otp", "")) 
                if code and code != "None" and code not in sent_codes:
                    send_to_telegram(f"নতুন হোয়াটসঅ্যাপ কোড: {code}")
                    sent_codes.add(code)
                    
        elif isinstance(data, dict):
            items = data.get("data", [])
            if isinstance(items, list):
                for item in items:
                    code = str(item.get("code") or item.get("otp", ""))
                    if code and code != "None" and code not in sent_codes:
                        send_to_telegram(f"নতুন হোয়াটসঅ্যাপ কোড: {code}")
                        sent_codes.add(code)
    except Exception as e:
        pass

# বট চালানোর ফাংশন
def run_bot():
    print("বট চালু হয়েছে...")
    while True:
        check_for_new_code()
        time.sleep(5)

# Render-এর জন্য বেসিক ওয়েব পেজ
@app.route('/')
def home():
    return "Bot is running on Render!"

if __name__ == "__main__":
    # বটটিকে আলাদা থ্রেডে চালু করা হচ্ছে যাতে ওয়েব সার্ভার ব্লক না হয়
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
    
    # ওয়েব সার্ভার চালু করা
    app.run(host='0.0.0.0', port=8080)
    
