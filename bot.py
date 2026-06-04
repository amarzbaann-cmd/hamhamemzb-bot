import os
import logging
import asyncio
from datetime import datetime, timedelta
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes, ConversationHandler
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pandas as pd
import io
from database import Database

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Config
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8917275443:AAFNIHMh0aeH-gXiAEjQIB3OkEkAsvDUjoc")
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", "1301441279"))
TEHRAN_TZ = pytz.timezone("Asia/Tehran")

# Conversation states
WAITING_CODE, WAITING_SIZE, WAITING_COLOR, WAITING_QUANTITY = range(4)

db = Database()


# ─────────────────────────────────────────────
# /start
# ─────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🤖 *بات مدیریت ناقصی‌ها*\n\n"
        "با این بات می‌تونی ناقصی‌های محصولات رو ثبت و آمار بگیری.\n\n"
        "📌 *دستورات:*\n"
        "➕ /add — ثبت ناقصی جدید\n"
        "📊 /report — گزارش فوری\n"
        "🔍 /search `[کد]` — جستجو بر اساس کد\n"
        "❌ /cancel — لغو عملیات جاری\n\n"
        "📎 همچنین می‌تونی *فایل اکسل* آپلود کنی تا ناقصی‌ها به صورت خودکار ثبت بشن."
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# ─────────────────────────────────────────────
# /add — Conversation flow
# ─────────────────────────────────────────────
async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "➕ *ثبت ناقصی جدید*\n\n"
        "🔢 لطفاً *کد محصول* را وارد کنید:",
        parse_mode="Markdown"
    )
    return WAITING_CODE


async def received_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["code"] = update.message.text.strip().upper()
    await update.message.reply_text(
        f"✅ کد: `{context.user_data['code']}`\n\n"
        "📏 لطفاً *سایز* را وارد کنید (مثال: S, M, L, XL, 38, 40...):",
        parse_mode="Markdown"
    )
    return WAITING_SIZE


async def received_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["size"] = update.message.text.strip().upper()
    await update.message.reply_text(
        f"✅ سایز: `{context.user_data['size']}`\n\n"
        "🎨 لطفاً *رنگ* را وارد کنید:",
        parse_mode="Markdown"
    )
    return WAITING_COLOR


async def received_color(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["color"] = update.message.text.strip()
    await update.message.reply_text(
        f"✅ رنگ: `{context.user_data['color']}`\n\n"
        "🔢 لطفاً *تعداد ناقصی* را وارد کنید (عدد):",
        parse_mode="Markdown"
    )
    return WAITING_QUANTITY


async def received_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        qty = int(update.message.text.strip())
        if qty <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ لطفاً یک عدد مثبت وارد کنید:")
        return WAITING_QUANTITY

    code = context.user_data["code"]
    size = context.user_data["size"]
    color = context.user_data["color"]
    now = datetime.now(TEHRAN_TZ)

    db.add_defect(code, size, color, qty, now)

    await update.message.reply_text(
        f"✅ *ناقصی با موفقیت ثبت شد!*\n\n"
        f"🏷️ کد: `{code}`\n"
        f"📏 سایز: `{size}`\n"
        f"🎨 رنگ: `{color}`\n"
        f"🔢 تعداد: `{qty}`\n"
        f"📅 تاریخ: `{now.strftime('%Y-%m-%d %H:%M')}`",
        parse_mode="Markdown"
    )
    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ عملیات لغو شد.")
    return ConversationHandler.END


# ─────────────────────────────────────────────
# /report
# ─────────────────────────────────────────────
async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    records = db.get_all_defects()
    if not records:
        await update.message.reply_text("📭 هیچ ناقصی‌ای ثبت نشده است.")
        return

    text = _build_report_text(records, title="📊 گزارش فوری ناقصی‌ها")
    await update.message.reply_text(text, parse_mode="Markdown")


# ─────────────────────────────────────────────
# /search [code]
# ─────────────────────────────────────────────
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "🔍 استفاده: `/search [کد محصول]`\nمثال: `/search A123`",
            parse_mode="Markdown"
        )
        return

    code = " ".join(context.args).strip().upper()
    records = db.get_defects_by_code(code)

    if not records:
        await update.message.reply_text(f"❌ هیچ ناقصی‌ای برای کد `{code}` یافت نشد.", parse_mode="Markdown")
        return

    total = sum(r["quantity"] for r in records)
    lines = [f"🔍 *نتایج جستجو برای کد:* `{code}`\n", f"📦 *مجموع ناقصی:* `{total} عدد`\n"]
    lines.append("\n```")
    lines.append(f"{'سایز':<8} {'رنگ':<12} {'تعداد':<6} {'تاریخ'}")
    lines.append("─" * 40)
    for r in records:
        date_str = r["created_at"][:10] if r["created_at"] else "—"
        lines.append(f"{r['size']:<8} {r['color']:<12} {r['quantity']:<6} {date_str}")
    lines.append("```")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ─────────────────────────────────────────────
# Excel upload handler
# ─────────────────────────────────────────────
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc.file_name.endswith((".xlsx", ".xls")):
        await update.message.reply_text("⚠️ لطفاً یک فایل اکسل (.xlsx یا .xls) آپلود کنید.")
        return

    msg = await update.message.reply_text("⏳ در حال پردازش فایل اکسل...")

    try:
        file = await doc.get_file()
        file_bytes = await file.download_as_bytearray()
        df = pd.read_excel(io.BytesIO(file_bytes))

        # Normalize column names
        df.columns = [str(c).strip().lower() for c in df.columns]

        # Map Persian/English column names
        col_map = {
            "کد": "code", "code": "code", "کد محصول": "code", "product_code": "code",
            "سایز": "size", "size": "size", "اندازه": "size",
            "رنگ": "color", "color": "color",
            "تعداد": "quantity", "quantity": "quantity", "مقدار": "quantity", "count": "quantity"
        }
        df.rename(columns=col_map, inplace=True)

        required = {"code", "size", "color", "quantity"}
        missing = required - set(df.columns)
        if missing:
            await msg.edit_text(
                f"❌ ستون‌های زیر در فایل یافت نشد:\n`{', '.join(missing)}`\n\n"
                f"ستون‌های موجود: `{', '.join(df.columns)}`",
                parse_mode="Markdown"
            )
            return

        now = datetime.now(TEHRAN_TZ)
        success = 0
        errors = 0
        for _, row in df.iterrows():
            try:
                code = str(row["code"]).strip().upper()
                size = str(row["size"]).strip().upper()
                color = str(row["color"]).strip()
                qty = int(row["quantity"])
                if not code or not size or not color or qty <= 0:
                    errors += 1
                    continue
                db.add_defect(code, size, color, qty, now)
                success += 1
            except Exception:
                errors += 1

        await msg.edit_text(
            f"✅ *پردازش فایل اکسل کامل شد!*\n\n"
            f"✔️ ثبت موفق: `{success}` رکورد\n"
            f"❌ خطا: `{errors}` رکورد",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Excel parse error: {e}")
        await msg.edit_text("❌ خطا در پردازش فایل. لطفاً فرمت فایل را بررسی کنید.")


# ─────────────────────────────────────────────
# Weekly report (every Friday)
# ─────────────────────────────────────────────
async def send_weekly_report(app: Application):
    try:
        one_week_ago = datetime.now(TEHRAN_TZ) - timedelta(days=7)
        records = db.get_defects_since(one_week_ago)

        if not records:
            text = "📊 *گزارش هفتگی*\n\n📭 در هفته گذشته هیچ ناقصی‌ای ثبت نشده است."
        else:
            text = _build_report_text(records, title="📊 گزارش هفتگی ناقصی‌ها (۷ روز گذشته)")

        await app.bot.send_message(chat_id=ADMIN_CHAT_ID, text=text, parse_mode="Markdown")
        logger.info("Weekly report sent successfully.")
    except Exception as e:
        logger.error(f"Failed to send weekly report: {e}")


# ─────────────────────────────────────────────
# Helper: build report text
# ─────────────────────────────────────────────
def _build_report_text(records: list, title: str) -> str:
    total = sum(r["quantity"] for r in records)

    # Group by code
    by_code = {}
    for r in records:
        code = r["code"]
        if code not in by_code:
            by_code[code] = {"total": 0, "details": []}
        by_code[code]["total"] += r["quantity"]
        by_code[code]["details"].append(r)

    lines = [f"*{title}*\n", f"📦 *مجموع کل ناقصی:* `{total} عدد`\n"]

    for code, data in sorted(by_code.items(), key=lambda x: -x[1]["total"]):
        lines.append(f"\n🏷️ *کد {code}* — مجموع: `{data['total']}`")
        lines.append("```")
        lines.append(f"{'سایز':<8} {'رنگ':<12} {'تعداد'}")
        lines.append("─" * 30)
        for r in data["details"]:
            lines.append(f"{r['size']:<8} {r['color']:<12} {r['quantity']}")
        lines.append("```")

    return "\n".join(lines)


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Conversation handler for /add
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("add", add_start)],
        states={
            WAITING_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_code)],
            WAITING_SIZE: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_size)],
            WAITING_COLOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_color)],
            WAITING_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_quantity)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("report", report))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    # Scheduler for weekly report (Friday 09:00 Tehran time)
    scheduler = AsyncIOScheduler(timezone=TEHRAN_TZ)
    scheduler.add_job(
        send_weekly_report,
        trigger="cron",
        day_of_week="fri",
        hour=9,
        minute=0,
        args=[app]
    )
    scheduler.start()
    logger.info("Scheduler started — weekly report every Friday 09:00 Tehran.")

    # Start polling
    logger.info("Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
