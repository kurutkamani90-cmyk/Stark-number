import asyncio
import os
from aiohttp import web
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = "8557102458:AAFcn39gwfbwf-njflJNRwX75quc-5YeS5Q"

# স্থায়ী কিবোর্ড বাটন
MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["📞 Get Number", "👤 My Account"],
        ["💵 Withdraw", "📊 Live Traffic"],
        ["👥 Refer & Earn", "⚙️ Help"]
    ],
    resize_keyboard=True
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "<b>Welcome to Stark Number Bot</b> ✅\n\n"
        "<b>Get instant OTP codes!</b> 💥\n\n"
        "👤 <b>Your OTPs:</b> 0\n"
        "💰 <b>Your Balance:</b> $0.0000\n"
        "📡 <b>Choose an option below:</b>"
    )
    inline_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📞 Get Number", callback_data="get_num"), InlineKeyboardButton("⭐ My Status", callback_data="my_status")],
        [InlineKeyboardButton("🌐 OTP Range", callback_data="otp_range"), InlineKeyboardButton("⚙️ Help", callback_data="help")]
    ])
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=MAIN_KEYBOARD)
    await update.message.reply_text("👇 Quick Options:", reply_markup=inline_kb)

async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text
    
    if msg == "📞 Get Number":
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_home")]])
        await update.message.reply_text(
            "⭐ <b>No stock available at the moment.</b>\nPlease check back later!",
            parse_mode=ParseMode.HTML,
            reply_markup=kb
        )
    elif msg == "👤 My Account":
        text = (
            "👤 <b>MY ACCOUNT</b>\n\n"
            "🔴 <b>Live Balance:</b> $0.0000\n"
            "<b>OTPs Today:</b> 0\n"
            "🚀 <b>Total OTPs:</b> 0\n"
            "💵 <b>Total Earnings:</b> $0.0000\n"
            "💰 <b>Total Withdrawn:</b> $0.0000 (0 times)\n"
            "💲 <b>Rate per OTP:</b> $0.0010\n\n"
            "🔘 <b>Referral Earnings:</b> $0.0000\n"
            "👥 <b>People Referred:</b> 0"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    elif msg == "💵 Withdraw":
        text = (
            "💲 <b>WITHDRAWAL SETUP</b>\n\n"
            "You have not set your <b>USDT BEP20</b> Wallet Address.\n\n"
            "🔄 <i>Please send your USDT BEP20 Wallet Address now:</i>"
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="cancel_withdraw")]])
        await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    elif msg == "📊 Live Traffic":
        text = (
            "★ <b>Traffic Stats (Last 10 Min HITS)</b>\n"
            "⭐ <b>Available Numbers:</b> 0\n"
            "⭐ <b>Countries Active:</b> 0\n"
            "🔄 <b>Services Active:</b> 0\n\n"
            "➡️ 💬 WhatsApp (Central African Republic) ➔ ⚡ HIGH\n"
            "➡️ 💬 WhatsApp (Nigeria) ➔ ⚡ HIGH\n"
            "➡️ 💬 WhatsApp (Togo) ➔ ⚡ MEDIUM"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    elif msg == "👥 Refer & Earn":
        bot_username = (await context.bot.get_me()).username
        user_id = update.effective_user.id
        ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
        text = (
            "👥 <b>REFER & EARN</b>\n\n"
            "🤑 <b>You earn 3% of your friends' OTP earnings!</b>\n\n"
            f"🔗 <b>Your Referral Link:</b>\n<code>{ref_link}</code>\n\n"
            "👥 <b>People Referred:</b> 0\n"
            "🔘 <b>Referral Earnings:</b> $0.0000\n\n"
            "⚠️ <i>Share this link with friends to earn commission!</i>"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    elif msg == "⚙️ Help":
        text = (
            "⚙️ <b>Help & Instructions</b>\n\n"
            "📞 <b>Get Number</b> - Get a phone number for OTP.\n"
            "⭐ <b>My Status</b> - Check active number & OTP status.\n"
            "⏳ Usually takes 30-60 seconds for OTP.\n\n"
            "⚠️ <i>Numbers auto-release after 10 minutes.</i>"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)

# রেন্ডারের পোর্ট যাচাইয়ের জন্য ডামি ওয়েব সার্ভার
async def run_web_server():
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="Bot is running!"))
    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"Server started on port {port}")

async def main():
    # ওয়েব সার্ভার শুরু
    await run_web_server()
    
    # টেলিগ্রাম বট শুরু
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))
    
    print("Bot polling started...")
    async with app:
        await app.start()
        await app.updater.start_polling()
        while True:
            await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
    
