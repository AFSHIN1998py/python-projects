import requests
import telebot
from datetime import datetime

# تنظیمات اولیه
TOKEN = "----------------------------"  # جایگزینی با توکن ربات شما
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = """
    🚀 به ربات گزارش قیمت ارزهای دیجیتال خوش آمدید!
    
    دستورات:
    /price - دریافت قیمت لحظه‌ای
    /help - راهنمایی
    """
    bot.reply_to(message, welcome_text)

@bot.message_handler(commands=['price'])
def send_crypto_prices(message):
    try:
        # دریافت داده‌های قیمت از API
        response = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd")
        data = response.json()
        
        # استخراج قیمت‌ها
        btc_price = data['bitcoin']['usd']
        eth_price = data['ethereum']['usd']
        
        # ساخت پاسخ
        report = f"""
        🕒 زمان: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        ---------------
        ₿ بیت‌کوین: ${btc_price:,.2f}
        Ξ اتریوم: ${eth_price:,.2f}
        ---------------
        """
        bot.reply_to(message, report)
        
    except Exception as e:
        bot.reply_to(message, f"خطا در دریافت داده‌ها: {str(e)}")

@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = "با استفاده از /price قیمت‌های لحظه‌ای را دریافت کنید"
    bot.reply_to(message, help_text)

# اجرای ربات
if __name__ == "__main__":
    print("ربات فعال شد...")
    bot.polling()