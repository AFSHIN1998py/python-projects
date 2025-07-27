import logging
import sqlite3
import os
from datetime import datetime, timedelta
from pytube import YouTube
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# توکن ربات - جایگزین کن!
TOKEN = "7712117169:AAHWz3EERrE5KdWi3s-aQX93-AXXU9tueac"

# تنظیمات دیتابیس
DB_NAME = "bot_database.db"
ADMIN_ID = 98598535  # جایگزین کن با ایدی عددی خودت در تلگرام

# تنظیمات دانلود
MAX_DAILY_DOWNLOADS = 3  # حداکثر دانلود روزانه برای هر کاربر
DOWNLOAD_PATH = "downloads"

# --- راه‌اندازی دیتابیس ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # جدول کاربران
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY, 
                  user_id INTEGER UNIQUE, 
                  first_name TEXT, 
                  username TEXT, 
                  join_date TIMESTAMP,
                  last_download TIMESTAMP)''')
    
    # جدول نظرسنجی با محدودیت هر کاربر یک رأی
    c.execute('''CREATE TABLE IF NOT EXISTS polls
                 (id INTEGER PRIMARY KEY,
                  user_id INTEGER UNIQUE,
                  vote TEXT,
                  vote_time TIMESTAMP)''')
    
    # جدول دانلودها
    c.execute('''CREATE TABLE IF NOT EXISTS downloads
                 (id INTEGER PRIMARY KEY,
                  user_id INTEGER,
                  video_url TEXT,
                  video_title TEXT,
                  download_time TIMESTAMP)''')
    
    conn.commit()
    conn.close()

# --- توابع اصلی ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /start"""
    user = update.effective_user
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # ذخیره کاربر در دیتابیس
    try:
        c.execute("INSERT INTO users (user_id, first_name, username, join_date) VALUES (?, ?, ?, ?)",
                  (user.id, user.first_name, user.username, datetime.now()))
        conn.commit()
    except sqlite3.IntegrityError:
        # کاربر از قبل وجود دارد
        pass
    
    conn.close()
    
    # ساخت منوی اصلی
    keyboard = [
        [InlineKeyboardButton("کانال ما", url="https://t.me/@AFSHIN77AM")],
        [InlineKeyboardButton("راهنما", callback_data="help")],
        [InlineKeyboardButton("نظرسنجی", callback_data="poll_menu")],
        [InlineKeyboardButton("دانلود ویدیو", callback_data="download_menu")],
        [InlineKeyboardButton("پنل ادمین", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_html(
        f"سلام {user.mention_html()}! به ربات پیشرفته خوش آمدید 🤖\n\n"
        "از منوی زیر می‌تونی انتخاب کنی:",
        reply_markup=reply_markup
    )

async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش دکمه راهنما"""
    query = update.callback_query
    await query.answer()
    
    help_text = (
        "📚 راهنمای ربات:\n\n"
        "• /start - نمایش منوی اصلی\n"
        "• /poll - ایجاد نظرسنجی جدید\n"
        "• /admin - پنل مدیریت (فقط ادمین)\n\n"
        "قابلیت‌های ویژه:\n"
        "- سیستم نظرسنجی حرفه‌ای (هر کاربر یک رأی)\n"
        "- دانلودر یوتیوب پیشرفته\n"
        "- پنل مدیریت ادمین\n"
        "- محدودیت دانلود روزانه\n"
        f"📥 حداکثر {MAX_DAILY_DOWNLOADS} دانلود در روز"
    )
    
    keyboard = [
        [InlineKeyboardButton("آموزش ویدیویی", url="https://youtube.com/yourchannel")],
        [InlineKeyboardButton("بازگشت ↩️", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=help_text,
        reply_markup=reply_markup
    )

async def create_poll_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """منوی نظرسنجی"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("پایتون 🐍", callback_data="vote_python")],
        [InlineKeyboardButton("جاوا اسکریپت 🌐", callback_data="vote_js")],
        [InlineKeyboardButton("سی پلاس پلاس ➕", callback_data="vote_cpp")],
        [InlineKeyboardButton("نتایج نظرسنجی 📊", callback_data="poll_results")],
        [InlineKeyboardButton("بازگشت ↩️", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "به نظر شما کدام زبان برنامه‌نویسی بهتره؟",
        reply_markup=reply_markup
    )

async def handle_vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش رأی کاربر با قابلیت تغییر رأی"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user = query.from_user
    language_code = data.split("_")[1]
    
    language_names = {
        "python": "پایتون",
        "js": "جاوا اسکریپت",
        "cpp": "سی پلاس پلاس"
    }
    language_name = language_names.get(language_code, language_code)
    
    # ذخیره یا به‌روزرسانی رأی در دیتابیس
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # بررسی رأی قبلی کاربر
    c.execute("SELECT vote FROM polls WHERE user_id = ?", (user.id,))
    previous_vote = c.fetchone()
    
    # ذخیره یا به‌روزرسانی رأی
    c.execute('''INSERT INTO polls (user_id, vote, vote_time) 
                 VALUES (?, ?, ?)
                 ON CONFLICT(user_id) DO UPDATE SET 
                 vote = excluded.vote, 
                 vote_time = excluded.vote_time''',
              (user.id, language_code, datetime.now()))
    
    conn.commit()
    conn.close()
    
    keyboard = [[InlineKeyboardButton("بازگشت ↩️", callback_data="poll_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if previous_vote:
        # اگر کاربر قبلاً رأی داده بود
        previous_name = language_names.get(previous_vote[0], previous_vote[0])
        message = (
            f"✅ رأی شما به‌روزرسانی شد!\n"
            f"تغییر از {previous_name} به {language_name}"
        )
    else:
        # اولین رأی کاربر
        message = f"ممنون {user.first_name}! رأی تو برای {language_name} ثبت شد ✅"
    
    await query.edit_message_text(
        message,
        reply_markup=reply_markup
    )

async def show_poll_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش نتایج نظرسنجی با محاسبه درصد"""
    query = update.callback_query
    await query.answer()
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # دریافت نتایج از دیتابیس
    c.execute("SELECT vote, COUNT(*) FROM polls GROUP BY vote")
    results = c.fetchall()
    
    # دریافت کل آراء
    c.execute("SELECT COUNT(*) FROM polls")
    total_votes = c.fetchone()[0]
    
    conn.close()
    
    if not results or total_votes == 0:
        response = "هنوز رأیی ثبت نشده است!"
    else:
        response = "نتایج نظرسنجی:\n\n"
        
        # محاسبه درصدها
        for vote, count in results:
            percentage = (count / total_votes) * 100
            response += f"{vote.upper()}: {count} رأی ({percentage:.1f}%)\n"
        
        response += f"\n🔹 کل آراء: {total_votes}"
    
    keyboard = [
        [InlineKeyboardButton("رأی دادن", callback_data="poll_menu")],
        [InlineKeyboardButton("بازگشت ↩️", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        response,
        reply_markup=reply_markup
    )

async def download_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """منوی دانلود"""
    query = update.callback_query
    await query.answer()
    
    # بررسی تعداد دانلودهای باقیمانده
    remaining_downloads = await get_remaining_downloads(query.from_user.id)
    
    keyboard = [
        [InlineKeyboardButton("دانلود از یوتیوب", callback_data="download_yt")],
        [InlineKeyboardButton("دانلود از اینستاگرام", callback_data="download_ig")],
        [InlineKeyboardButton("بازگشت ↩️", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"لطفاً نوع دانلود را انتخاب کنید:\n\n"
        f"📥 دانلودهای باقیمانده امروز: {remaining_downloads}/{MAX_DAILY_DOWNLOADS}",
        reply_markup=reply_markup
    )

async def get_remaining_downloads(user_id):
    """محاسبه تعداد دانلودهای باقیمانده کاربر"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # دریافت تعداد دانلودهای امروز
    today = datetime.now().date()
    c.execute("SELECT COUNT(*) FROM downloads WHERE user_id = ? AND DATE(download_time) = ?", 
              (user_id, today))
    today_downloads = c.fetchone()[0]
    
    conn.close()
    return max(0, MAX_DAILY_DOWNLOADS - today_downloads)

async def handle_download_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت لینک دانلود"""
    query = update.callback_query
    await query.answer()
    
    # بررسی تعداد دانلودهای باقیمانده
    remaining = await get_remaining_downloads(query.from_user.id)
    if remaining <= 0:
        await query.edit_message_text(
            f"❌ سقف دانلود روزانه شما تکمیل شده!\n"
            f"امروز نمی‌توانید بیشتر از {MAX_DAILY_DOWNLOADS} ویدیو دانلود کنید."
        )
        return
    
    context.user_data['download_type'] = query.data
    context.user_data['awaiting_url'] = True
    
    await query.edit_message_text(
        "لطفاً لینک ویدیو را ارسال کنید:"
    )

async def download_youtube_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دانلود واقعی ویدیو از یوتیوب"""
    if 'awaiting_url' not in context.user_data:
        return
    
    url = update.message.text
    user = update.effective_user
    
    # بررسی تعداد دانلودهای باقیمانده
    remaining = await get_remaining_downloads(user.id)
    if remaining <= 0:
        await update.message.reply_text(
            f"❌ سقف دانلود روزانه شما تکمیل شده!\n"
            f"امروز نمی‌توانید بیشتر از {MAX_DAILY_DOWNLOADS} ویدیو دانلود کنید."
        )
        del context.user_data['awaiting_url']
        return
    
    try:
        # ایجاد پوشه دانلود
        user_download_path = os.path.join(DOWNLOAD_PATH, str(user.id))
        os.makedirs(user_download_path, exist_ok=True)
        
        # دریافت اطلاعات ویدیو
        yt = YouTube(url)
        stream = yt.streams.filter(progressive=True, file_extension='mp4').get_highest_resolution()
        
        # اطلاع شروع دانلود
        await update.message.reply_text(
            f"⏳ در حال دانلود:\n{yt.title}\n\n"
            f"🕓 مدت: {yt.length // 60}:{yt.length % 60:02d}\n"
            f"💾 حجم: {stream.filesize_mb:.1f} MB"
        )
        
        # دانلود واقعی ویدیو
        file_path = stream.download(output_path=user_download_path)
        
        # ارسال ویدیو
        await update.message.reply_video(
            video=open(file_path, 'rb'),
            caption=f"✅ {yt.title}\n"
                    f"🕓 مدت: {yt.length//60}:{yt.length%60:02d}\n"
                    f"💾 حجم: {stream.filesize_mb:.1f} MB\n"
                    f"📥 توسط: @{user.username}",
            supports_streaming=True
        )
        
        # ذخیره اطلاعات دانلود در دیتابیس
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("INSERT INTO downloads (user_id, video_url, video_title, download_time) VALUES (?, ?, ?, ?)",
                  (user.id, url, yt.title, datetime.now()))
        conn.commit()
        conn.close()
        
        # به‌روزرسانی تعداد دانلودهای باقیمانده
        remaining = await get_remaining_downloads(user.id)
        await update.message.reply_text(
            f"✅ دانلود با موفقیت انجام شد!\n"
            f"📥 دانلودهای باقیمانده امروز: {remaining}/{MAX_DAILY_DOWNLOADS}"
        )
        
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در دانلود: {str(e)}")
        logger.error(f"Download failed for {url}: {str(e)}")
        
    finally:
        if 'awaiting_url' in context.user_data:
            del context.user_data['awaiting_url']

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پنل مدیریت"""
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("❌ دسترسی فقط برای ادمین!")
        return
    
    keyboard = [
        [InlineKeyboardButton("آمار کاربران", callback_data="admin_stats")],
        [InlineKeyboardButton("نتایج نظرسنجی", callback_data="poll_results")],
        [InlineKeyboardButton("مدیریت دانلودها", callback_data="download_stats")],
        [InlineKeyboardButton("خروج", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "پنل مدیریت:",
        reply_markup=reply_markup
    )

async def show_admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش آمار به ادمین"""
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != ADMIN_ID:
        return
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # آمار کاربران
    c.execute("SELECT COUNT(*) FROM users")
    user_count = c.fetchone()[0]
    
    # جدیدترین کاربران
    c.execute("SELECT first_name, username, join_date FROM users ORDER BY join_date DESC LIMIT 5")
    recent_users = c.fetchall()
    
    # آمار نظرسنجی
    c.execute("SELECT COUNT(*) FROM polls")
    poll_count = c.fetchone()[0]
    
    # آمار دانلودها
    c.execute("SELECT COUNT(*) FROM downloads")
    download_count = c.fetchone()[0]
    
    conn.close()
    
    response = (
        f"👥 کاربران: {user_count}\n"
        f"🗳 نظرسنجی‌ها: {poll_count}\n"
        f"📥 دانلودها: {download_count}\n\n"
        "🔍 جدیدترین کاربران:\n"
    )
    
    for user in recent_users:
        response += f"- {user[0]} (@{user[1]}) - {user[2][:10]}\n"
    
    keyboard = [[InlineKeyboardButton("بازگشت ↩️", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        response,
        reply_markup=reply_markup
    )

async def download_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """آمار دانلودها"""
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != ADMIN_ID:
        return
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # پرکاربرترین‌های دانلود
    c.execute('''SELECT user_id, COUNT(*) as download_count 
                 FROM downloads 
                 GROUP BY user_id 
                 ORDER BY download_count DESC 
                 LIMIT 5''')
    top_users = c.fetchall()
    
    # آخرین دانلودها
    c.execute('''SELECT user_id, video_title, download_time 
                 FROM downloads 
                 ORDER BY download_time DESC 
                 LIMIT 5''')
    recent_downloads = c.fetchall()
    
    # آمار کلی
    c.execute("SELECT COUNT(*) FROM downloads")
    total_downloads = c.fetchone()[0]
    
    conn.close()
    
    response = f"📊 آمار دانلودها (کل: {total_downloads})\n\n"
    response += "🏆 کاربران برتر:\n"
    for user in top_users:
        response += f"- کاربر {user[0]}: {user[1]} دانلود\n"
    
    response += "\n🕒 آخرین دانلودها:\n"
    for dl in recent_downloads:
        response += f"- {dl[1][:20]}... توسط {dl[0]} در {dl[2][:16]}\n"
    
    keyboard = [[InlineKeyboardButton("بازگشت ↩️", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        response,
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش کلیک روی دکمه‌ها"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "help":
        await handle_help(update, context)
    elif data == "poll_menu":
        await create_poll_menu(update, context)
    elif data == "main_menu":
        await start_menu(update, context)
    elif data.startswith("vote_"):
        await handle_vote(update, context)
    elif data == "poll_results":
        await show_poll_results(update, context)
    elif data == "download_menu":
        await download_menu(update, context)
    elif data in ["download_yt", "download_ig"]:
        await handle_download_request(update, context)
    elif data == "admin_panel":
        await admin_panel(update, context)
    elif data == "admin_stats":
        await show_admin_stats(update, context)
    elif data == "download_stats":
        await download_stats(update, context)

async def start_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """منوی اصلی"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("کانال ما", url="https://t.me/yourchannel")],
        [InlineKeyboardButton("راهنما", callback_data="help")],
        [InlineKeyboardButton("نظرسنجی", callback_data="poll_menu")],
        [InlineKeyboardButton("دانلود ویدیو", callback_data="download_menu")],
        [InlineKeyboardButton("پنل ادمین", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "به منوی اصلی خوش آمدید! گزینه مورد نظر را انتخاب کنید:",
        reply_markup=reply_markup
    )

# --- توابع پردازش پیام ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش پیام‌های متنی"""
    text = update.message.text.lower()
    user = update.effective_user
    
    # اگر کاربر در حال ارسال لینک برای دانلود است
    if 'awaiting_url' in context.user_data:
        await download_youtube_video(update, context)
        return
    
    # پاسخ به پیام‌های متنی عادی
    if 'سلام' in text:
        await update.message.reply_text(f"سلام {user.first_name}! 😊")
    elif 'خداحافظ' in text:
        await update.message.reply_text("خداحافظ! منتظرت هستم 🤗")
    else:
        await update.message.reply_text("برای مشاهده منو از دستور /start استفاده کنید")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش عکس‌های ارسالی"""
    await update.message.reply_text("عکس قشنگیه! 😍")

async def handle_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش استیکرهای ارسالی"""
    await update.message.reply_text("استیکر باحالی بود! 😄")

# --- راه‌اندازی ربات ---
def main():
    # ایجاد پوشه دانلودها
    os.makedirs(DOWNLOAD_PATH, exist_ok=True)
    
    # مقداردهی اولیه دیتابیس
    init_db()
    
    app = Application.builder().token(TOKEN).build()
    
    # دستورات
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("poll", create_poll_menu))
    app.add_handler(CommandHandler("admin", admin_panel))
    
    # دکمه‌ها
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # پیام‌ها
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Sticker.ALL, handle_sticker))
    
    # شروع ربات
    logger.info("ربات در حال راه‌اندازی...")
    print("✅ ربات با موفقیت راه‌اندازی شد!")
    print(f"📂 مسیر دانلودها: {os.path.abspath(DOWNLOAD_PATH)}")
    app.run_polling()

if __name__ == '__main__':
    main()

    