import os
import io
import logging
import openpyxl
from datetime import datetime, timedelta
import pytz
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database import Database

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN     = os.environ.get("BOT_TOKEN", "8917275443:AAFNIHMh0aeH-gXiAEjQIB3OkEkAsvDUjoc")
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", "1301441279"))
TEHRAN_TZ     = pytz.timezone("Asia/Tehran")

WAITING_CODE, WAITING_SIZE, WAITING_COLOR, WAITING_QUANTITY = range(4)
db = Database()


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *بات مدیریت ناقصی‌ها*\n\n"
        "📌 *دستورات:*\n"
        "➕ /add — ثبت ناقصی جدید\n"
        "📊 /report — گزارش فوری\n"
        "🔍 /search کد — جستجو\n"
        "❌ /cancel — لغو\n\n"
        "📎 فایل اکسل هم می‌تونی بفرستی!\n"
        "ستون‌ها: کد | سایز | رنگ | تعداد",
        parse_mode="Markdown")


async def add_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    await update.message.reply_text("➕ *ثبت ناقصی*\n\n🔢 کد محصول:", parse_mode="Markdown")
    return WAITING_CODE

async def received_code(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["code"] = update.message.text.strip().upper()
    await update.message.reply_text(f"✅ کد: `{ctx.user_data['code']}`\n\n📏 سایز:", parse_mode="Markdown")
    return WAITING_SIZE

async def received_size(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["size"] = update.message.text.strip().upper()
    await update.message.reply_text(f"✅ سایز: `{ctx.user_data['size']}`\n\n🎨 رنگ:", parse_mode="Markdown")
    return WAITING_COLOR

async def received_color(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["color"] = update.message.text.strip()
    await update.message.reply_text(f"✅ رنگ: `{ctx.user_data['color']}`\n\n🔢 تعداد:", parse_mode="Markdown")
    return WAITING_QUANTITY

async def received_quantity(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        qty = int(update.message.text.strip())
        if qty <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ عدد مثبت وارد کن:")
        return WAITING_QUANTITY

    code, size, color = ctx.user_data["code"], ctx.user_data["size"], ctx.user_data["color"]
    now = datetime.now(TEHRAN_TZ)
    db.add_defect(code, size, color, qty, now)
    await update.message.reply_text(
        f"✅ *ثبت شد!*\n\nکد: `{code}` | سایز: `{size}` | رنگ: `{color}` | تعداد: `{qty}`",
        parse_mode="Markdown")
    ctx.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    await update.message.reply_text("❌ لغو شد.")
    return ConversationHandler.END


async def report(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    records = db.get_all_defects()
    if not records:
        await update.message.reply_text("📭 هیچ ناقصی‌ای ثبت نشده.")
        return
    await update.message.reply_text(_build_report(records, "📊 گزارش فوری"), parse_mode="Markdown")


async def search(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("مثال: `/search A123`", parse_mode="Markdown")
        return
    code    = " ".join(ctx.args).strip().upper()
    records = db.get_defects_by_code(code)
    if not records:
        await update.message.reply_text(f"❌ ناقصی برای کد `{code}` یافت نشد.", parse_mode="Markdown")
        return
    await update.message.reply_text(_build_report(records, f"🔍 نتایج {code}"), parse_mode="Markdown")


async def handle_document(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc.file_name.endswith((".xlsx", ".xls")):
        await update.message.reply_text("⚠️ فقط فایل .xlsx قبوله.")
        return
    msg = await update.message.reply_text("⏳ در حال پردازش...")
    try:
        file       = await doc.get_file()
        file_bytes = await file.download_as_bytearray()
        wb         = openpyxl.load_workbook(io.BytesIO(file_bytes))
        ws         = wb.active
        now        = datetime.now(TEHRAN_TZ)
        ok = err   = 0
        for row in ws.iter_rows(min_row=2, values_only=True):
            try:
                code  = str(row[0]).strip().upper()
                size  = str(row[1]).strip().upper()
                color = str(row[2]).strip()
                qty   = int(row[3])
                if not code or not size or not color or qty <= 0:
                    err += 1
                    continue
                db.add_defect(code, size, color, qty, now)
                ok += 1
            except:
                err += 1
        await msg.edit_text(f"✅ ثبت شد: `{ok}` ردیف\n❌ خطا: `{err}` ردیف", parse_mode="Markdown")
    except Exception as e:
        await msg.edit_text(f"❌ خطا: {e}")


def _build_report(records, title):
    total   = sum(r["quantity"] for r in records)
    by_code = {}
    for r in records:
        c = r["code"]
        if c not in by_code:
            by_code[c] = {"total": 0, "rows": []}
        by_code[c]["total"] += r["quantity"]
        by_code[c]["rows"].append(r)

    lines = [f"*{title}*\n", f"📦 مجموع کل: `{total} عدد`\n"]
    for code, data in sorted(by_code.items(), key=lambda x: -x[1]["total"]):
        lines.append(f"\n🏷️ *کد {code}* — مجموع: `{data['total']}`")
        lines.append("```")
        lines.append(f"{'سایز':<8} {'رنگ':<12} {'تعداد'}")
        lines.append("─" * 30)
        for r in data["rows"]:
            lines.append(f"{r['size']:<8} {r['color']:<12} {r['quantity']}")
        lines.append("```")
    return "\n".join(lines)


async def _send_report(app, title, records):
    text = _build_report(records, title) if records else f"📭 {title}\n\nچیزی ثبت نشده."
    await app.bot.send_message(ADMIN_CHAT_ID, text, parse_mode="Markdown")

async def auto_daily(app):
    today = datetime.now(TEHRAN_TZ).strftime("%Y-%m-%d")
    await _send_report(app, f"📅 گزارش روزانه — {today}", db.get_defects_by_date(today))

async def auto_weekly(app):
    since = datetime.now(TEHRAN_TZ) - timedelta(days=7)
    await _send_report(app, "📆 گزارش هفتگی", db.get_defects_since(since))

async def auto_monthly(app):
    since = datetime.now(TEHRAN_TZ).replace(day=1, hour=0, minute=0, second=0)
    await _send_report(app, "🗓 گزارش ماهانه", db.get_defects_since(since))


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("add", add_start)],
        states={
            WAITING_CODE:     [MessageHandler(filters.TEXT & ~filters.COMMAND, received_code)],
            WAITING_SIZE:     [MessageHandler(filters.TEXT & ~filters.COMMAND, received_size)],
            WAITING_COLOR:    [MessageHandler(filters.TEXT & ~filters.COMMAND, received_color)],
            WAITING_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_quantity)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    ))

    app.add_handler(CommandHandler("start",  start))
    app.add_handler(CommandHandler("report", report))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    scheduler = AsyncIOScheduler(timezone=TEHRAN_TZ)
    scheduler.add_job(auto_daily,   "cron", hour=22, minute=0,          args=[app])
    scheduler.add_job(auto_weekly,  "cron", day_of_week="fri", hour=22, args=[app])
    scheduler.add_job(auto_monthly, "cron", day=1, hour=8,              args=[app])
    scheduler.start()

    logger.info("✅ بات شروع به کار کرد!")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
