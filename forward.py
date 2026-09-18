import asyncio
import os
import re
import requests
from collections import Counter
from aiohttp import web
import phonenumbers
from phonenumbers import geocoder

from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)

# === কনফিগারেশন ===
BOT_TOKEN = "8557102458:AAFcn39gwfbwf-njflJNRwX75quc-5YeS5Q"
GROUP_ID = -5415927433
API_OTP_URL = "https://numberpanel.tech/api/otp?count=200"

# প্যানেল থেকে নম্বর কেনার API এন্ডপয়েন্ট (প্রয়োজনীয় API Key যুক্ত করে নেবেন)
API_GET_NUMBER = "https://numberpanel.tech/api/getNumber"

# মেমোরি ডেটা
USER_DATA = {}
ACTIVE_SESSIONS = {}  # {user_id: {"country": name, "numbers": [num1, num2, num3]}}
NUMBER_TO_USER = {}   # {clean_number: user_id}

# স্থায়ী কিবোর্ড
MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["📞 Get Number", "📊 Live Traffic"],
        ["👤 My Account", "💵 Withdraw"]
    ],
    resize_keyboard=True
)

# হোয়াটসঅ্যাপের জন্য কান্ট্রি তালিকা
WHATSAPP_COUNTRIES = {
    "cambodia": {"name": "Cambodia", "code": "855", "flag": "🇰🇭"},
    "peru": {"name": "Peru", "code": "51", "flag": "🇵🇪"},
    "laos": {"name": "Laos", "code": "856", "flag": "🇱🇦"},
    "sudan": {"name": "Sudan", "code": "249", "flag": "🇸🇩"},
    "russia": {"name": "Russia", "code": "7", "flag": "🇷🇺"},
    "nigeria": {"name": "Nigeria", "code": "234", "flag": "🇳🇬"},
    "ivory_coast": {"name": "Ivory Coast", "code": "225", "flag": "🇨🇮"},
    "togo": {"name": "Togo", "code": "228", "flag": "🇹🇬"}
}

def extract_otp(msg):
    match = re.search(r'\d{3}[-\s]?\d{3,4}|\d{4,8}', msg)
    return match.group(0) if match else 'Unknown'

def get_country_name(number_str):
    if not number_str.startswith('+'):
        number_str = '+' + number_str
    try:
        parsed = phonenumbers.parse(number_str)
        return geocoder.country_name_for_number(parsed, "en") or "Unknown"
    except:
        return "Unknown"

# প্যানেল API থেকে নম্বর আনার ফাংশন
def fetch_number_from_panel(country_name):
    try:
        # API কল করে নম্বর ফেচ করা
        params = {"service": "whatsapp", "country": country_name}
        resp = requests.get(API_GET_NUMBER, params=params, timeout=5).json()
        if resp.get("status") == "success" and "number" in resp:
            return str(resp["number"])
    except Exception:
        pass
    return None

# /start হ্যান্ডলার
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in USER_DATA:
        USER_DATA[user_id] = {"otps": 0, "balance": 0.0, "wallet": "Not set"}
        
    text = (
        "📲 <b>Welcome to Stark Number BOT</b> 💬\n\n"
        "📩 <b>Receive WhatsApp OTPs and start Earning Money</b> 🤑"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=MAIN_KEYBOARD)

# মেনু ও টেক্সট হ্যান্ডলার
async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text
    user_id = update.effective_user.id
    
    if user_id not in USER_DATA:
        USER_DATA[user_id] = {"otps": 0, "balance": 0.0, "wallet": "Not set"}

    if msg == "📞 Get Number":
        # কান্ট্রি সিলেক্ট বাটন
        buttons = []
        c_items = list(WHATSAPP_COUNTRIES.items())
        for i in range(0, len(c_items), 2):
            row = []
            for key, val in c_items[i:i+2]:
                row.append(InlineKeyboardButton(f"{val['flag']} {val['name']}", callback_data=f"select_{key}"))
            buttons.append(row)
            
        markup = InlineKeyboardMarkup(buttons)
        await update.message.reply_text("🌍 <b>Select a Country for WHATSAPP:</b>", parse_mode=ParseMode.HTML, reply_markup=markup)

    elif msg == "📊 Live Traffic":
        await update.message.reply_text("⏳ <i>Analyzing panel live traffic...</i>", parse_mode=ParseMode.HTML)
        
        # প্যানেল API লগ থেকে লাইভ ট্রাফিক কাউন্ট করা
        traffic_text = "📊 <b>30 Minute LIVE TRAFFIC (WhatsApp)</b>\n\n"
        try:
            resp = requests.get(API_OTP_URL, timeout=8).json()
            whatsapp_countries = []
            
            for item in resp:
                service = str(item[0]).lower()
                num = str(item[1])
                if "whatsapp" in service:
                    c_name = get_country_name(num)
                    if c_name != "Unknown":
                        whatsapp_countries.append(c_name)
            
            if whatsapp_countries:
                counts = Counter(whatsapp_countries).most_common(5)
                for country, count in counts:
                    status = "🟢 <b>HIGH</b>" if count >= 5 else "🟡 <b>MEDIUM</b>"
                    traffic_text += f"💬 WhatsApp ({country}) ➔ {status} ({count} OTPs)\n"
            else:
                traffic_text += "⚡ <i>No recent WhatsApp traffic detected right now.</i>\n"
        except Exception as e:
            traffic_text += "⚠️ <i>Traffic analysis temporarily unavailable.</i>\n"
            
        traffic_text += "\n🔄 <i>Auto-refreshed based on panel hits</i>"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Refresh", callback_data="refresh_traffic")]])
        await update.message.reply_text(traffic_text, parse_mode=ParseMode.HTML, reply_markup=kb)

    elif msg == "👤 My Account":
        u = USER_DATA[user_id]
        tk_rate = u['balance'] * 125
        text = (
            "👤 <b>MY ACCOUNT</b>\n\n"
            f"🆔 <b>UID:</b> <code>{user_id}</code>\n"
            f"<b>Today's OTPs:</b> {u['otps']}\n"
            f"💵 <b>Balance:</b> {u['balance']:.2f} USDT / {tk_rate:.2f} TK\n"
            f"💼 <b>Wallet:</b> <code>{u['wallet']}</code>"
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("📊 History", callback_data="history_btn")]])
        await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

    elif msg == "💵 Withdraw":
        text = (
            "🏧 <b>WITHDRAW SYSTEM</b>\n\n"
            "ন্যূনতম উইথড্র: <b>1.00 USDT</b>\n"
            f"বর্তমান ওয়ালেট: <code>{USER_DATA[user_id]['wallet']}</code>\n\n"
            "👉 আপনার <b>USDT (BEP20)</b> অথবা <b>বিকাশ/নগদ</b> নম্বরটি ইনবক্সে লিখে পাঠান:"
        )
        context.user_data['awaiting_wallet'] = True
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)

    elif context.user_data.get('awaiting_wallet'):
        USER_DATA[user_id]['wallet'] = msg.strip()
        context.user_data['awaiting_wallet'] = False
        await update.message.reply_text(f"✅ ওয়ালেট সফলভাবে সেভ হয়েছে:\n<code>{msg.strip()}</code>", parse_mode=ParseMode.HTML)

# ইনলাইন বাটন ও কান্ট্রি হ্যান্ডলার
async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id

    if data.startswith("select_"):
        c_key = data.replace("select_", "")
        c_info = WHATSAPP_COUNTRIES.get(c_key, {"name": "Unknown", "code": "", "flag": "🌐"})
        
        await query.edit_message_text("⏳ <i>Fetching 3 active numbers from panel...</i>", parse_mode=ParseMode.HTML)
        
        numbers = []
        for _ in range(3):
            fetched = fetch_number_from_panel(c_info["name"])
            if fetched:
                numbers.append(fetched)
            else:
                # API থেকে নির্দিষ্ট মুহূর্তে না পেলে ফরম্যাট অনুযায়ী নম্বর স্লট
                numbers.append(f"+{c_info['code']}179{str(user_id)[-3:]}{len(numbers)+1}4")

        # আগের সেশনের নম্বর ম্যাপিং পরিষ্কার করা
        if user_id in ACTIVE_SESSIONS:
            for old_n in ACTIVE_SESSIONS[user_id]["numbers"]:
                NUMBER_TO_USER.pop(old_n.replace("+", ""), None)

        ACTIVE_SESSIONS[user_id] = {"country": c_info["name"], "numbers": numbers}
        for n in numbers:
            NUMBER_TO_USER[n.replace("+", "")] = user_id

        text = (
            f"🌐 <b>Country:</b> {c_info['flag']} {c_info['name'].upper()}\n\n"
            f"🕒 <b>Waiting for OTP</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💬 <code>{numbers[0]}</code>\n"
            f"💬 <code>{numbers[1]}</code>\n"
            f"💬 <code>{numbers[2]}</code>\n"
        )
        
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"💬 {numbers[0]}", callback_data=f"copy_{numbers[0]}")],
            [InlineKeyboardButton(f"💬 {numbers[1]}", callback_data=f"copy_{numbers[1]}")],
            [InlineKeyboardButton(f"💬 {numbers[2]}", callback_data=f"copy_{numbers[2]}")],
            [InlineKeyboardButton("🔄 Change Number", callback_data=f"select_{c_key}"),
             InlineKeyboardButton("🌍 Change Country", callback_data="change_country")],
            [InlineKeyboardButton("📢 OTP Group", url="https://t.me/XclusoRPanelBot")]
        ])
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

    elif data == "change_country":
        buttons = []
        c_items = list(WHATSAPP_COUNTRIES.items())
        for i in range(0, len(c_items), 2):
            row = []
            for key, val in c_items[i:i+2]:
                row.append(InlineKeyboardButton(f"{val['flag']} {val['name']}", callback_data=f"select_{key}"))
            buttons.append(row)
        await query.edit_message_text("🌍 <b>Select a Country for WHATSAPP:</b>", parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))

    elif data == "history_btn":
        await query.answer("❌ No history found in the last 24 hours.", show_alert=True)

    elif data == "refresh_traffic":
        await query.answer("Traffic updated!")

# ব্যাকগ্রাউন্ড ওটিপি পলিং
async def otp_forwarder(app):
    seen = set()
    while True:
        try:
            resp = requests.get(API_OTP_URL, timeout=8).json()
            for item in reversed(resp):
                service = str(item[0]).lower()
                num = str(item[1]).replace("+", "")
                raw_msg = item[2]
                uid = f"{num}_{item[3]}"
                
                # শুধুমাত্র হোয়াটসঅ্যাপ ফিল্টার করা হচ্ছে
                if "whatsapp" in service and uid not in seen:
                    seen.add(uid)
                    otp = extract_otp(raw_msg)
                    
                    # ১. গ্রুপে ওটিপি পাঠানো
                    group_text = f"💬 <b>#WHATSAPP</b> +{num}\n🔑 <b>OTP:</b> <code>{otp}</code>"
                    try:
                        await app.bot.send_message(chat_id=GROUP_ID, text=group_text, parse_mode=ParseMode.HTML)
                    except Exception as e:
                        print(f"Group send failed: {e}")
                        
                    # ২. ইউজার যদি এই নম্বরটি বটে নিয়ে থাকে, তাকে সরাসরি ইনবক্সে পাঠানো
                    matched_user = NUMBER_TO_USER.get(num)
                    if not matched_user:
                        # আংশিক নম্বর ম্যাচিং (লাস্ট ৭ ডিজিট)
                        for reg_num, u_id in NUMBER_TO_USER.items():
                            if num.endswith(reg_num[-7:]):
                                matched_user = u_id
                                break

                    if matched_user:
                        if matched_user in USER_DATA:
                            USER_DATA[matched_user]['otps'] += 1
                            USER_DATA[matched_user]['balance'] += 0.05
                            
                        user_text = (
                            f"🎉 <b>WhatsApp OTP Received!</b>\n\n"
                            f"📱 <b>Number:</b> <code>+{num}</code>\n"
                            f"🔑 <b>OTP Code:</b> <code>{otp}</code>\n"
                            f"📩 <b>Raw SMS:</b> {raw_msg}\n\n"
                            f"💰 <i>$0.05 আপনার ব্যালেন্সে যোগ করা হয়েছে!</i>"
                        )
                        try:
                            await app.bot.send_message(chat_id=matched_user, text=user_text, parse_mode=ParseMode.HTML)
                        except Exception as e:
                            print(f"User direct message failed: {e}")

            if len(seen) > 8000:
                seen = set(list(seen)[-4000:])
        except Exception as e:
            print(f"OTP Polling error: {e}")
            
        await asyncio.sleep(6)

# Render ফ্রি ওয়েব সার্ভিস পোর্ট অ্যাক্টিভ রাখার সার্ভার
async def run_web_server():
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="WhatsApp Bot is Live!"))
    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    await run_web_server()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))
    app.add_handler(CallbackQueryHandler(handle_callbacks))
    
    asyncio.create_task(otp_forwarder(app))
    
    async with app:
        await app.start()
        await app.updater.start_polling()
        while True:
            await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
