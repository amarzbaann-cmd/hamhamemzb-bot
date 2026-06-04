# 🤖 بات تلگرام مدیریت ناقصی‌ها — @Hamhamemzb_bot

بات مدیریت ناقصی محصولات با قابلیت ثبت دستی، آپلود اکسل، گزارش فوری و گزارش هفتگی خودکار.

---

## ✨ امکانات

| امکان | توضیح |
|-------|-------|
| ➕ ثبت دستی | ارسال کد + سایز + رنگ + تعداد از طریق چت |
| 📎 آپلود اکسل | آپلود فایل `.xlsx` و پردازش خودکار |
| 📊 گزارش فوری | `/report` — جدول کامل ناقصی‌ها |
| 🔍 جستجو | `/search [کد]` — تمام ناقصی‌های یک کد |
| 📅 گزارش هفتگی | هر جمعه ساعت ۹ صبح (به‌وقت تهران) ارسال می‌شه |
| 💚 Health Check | endpoint `/health` برای UptimeRobot |

---

## 🗂 ساختار فایل‌ها

```
telegram-bot/
├── main.py           ← نقطه شروع (health server + bot)
├── bot.py            ← منطق اصلی بات
├── database.py       ← لایه دیتابیس SQLite
├── health_server.py  ← سرور HTTP برای uptime check
├── requirements.txt  ← وابستگی‌های Python
├── render.yaml       ← تنظیمات Render
└── .github/
    └── workflows/
        └── deploy.yml ← GitHub Actions CI
```

---

## 🚀 راه‌اندازی روی Render

### مرحله ۱ — آپلود کد به GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/USERNAME/REPO_NAME.git
git push -u origin main
```

### مرحله ۲ — ساخت سرویس در Render

1. به [render.com](https://render.com) برو و وارد شو
2. روی **New +** کلیک کن → **Web Service**
3. ریپازیتوری GitHub خودت رو انتخاب کن
4. تنظیمات زیر رو وارد کن:

| فیلد | مقدار |
|------|-------|
| **Runtime** | Python 3 |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `python main.py` |
| **Plan** | Free |

5. در بخش **Environment Variables** اضافه کن:

| کلید | مقدار |
|------|-------|
| `BOT_TOKEN` | `8917275443:AAFNIHMh0aeH-gXiAEjQIB3OkEkAsvDUjoc` |
| `ADMIN_CHAT_ID` | `1301441279` |
| `PORT` | `8080` |
| `DB_PATH` | `/opt/render/project/src/defects.db` |

6. در بخش **Disks** یک disk اضافه کن:
   - Mount Path: `/opt/render/project/src`
   - Size: 1 GB

7. روی **Create Web Service** کلیک کن

### مرحله ۳ — UptimeRobot (همیشه روشن)

1. به [uptimerobot.com](https://uptimerobot.com) برو (رایگان)
2. **Add New Monitor** → HTTP(s)
3. URL رو وارد کن: `https://YOUR-APP-NAME.onrender.com/health`
4. Interval رو روی **5 minutes** بذار
5. **Create Monitor**

✅ با این کار سرویس Render هرگز به sleep نمی‌ره!

---

## 📋 فرمت فایل اکسل

برای آپلود اکسل، فایل باید ستون‌های زیر رو داشته باشه (فارسی یا انگلیسی):

| کد / code | سایز / size | رنگ / color | تعداد / quantity |
|-----------|-------------|-------------|-----------------|
| A123 | M | آبی | 5 |
| B456 | L | قرمز | 3 |

---

## 🔧 دستورات بات

| دستور | کاربرد |
|-------|--------|
| `/start` | نمایش راهنما |
| `/add` | ثبت ناقصی جدید (step by step) |
| `/report` | گزارش فوری از تمام ناقصی‌ها |
| `/search A123` | جستجو بر اساس کد محصول |
| `/cancel` | لغو عملیات جاری |

---

## 🏥 بررسی سلامت بات

```
GET https://YOUR-APP.onrender.com/health
```

پاسخ:
```
status: OK
uptime: 2:34:15
bot: @Hamhamemzb_bot
```
