# 🤖 Video Yuklovchi Telegram Bot

Ko'plab platformalardan video yuklash imkoniyatiga ega Telegram bot.

## 📋 Imkoniyatlari

- YouTube, Instagram, TikTok, Facebook va boshqa platformalardan video yuklash
- Videolardan audio ajratib olish
- Videodagi musiqani aniqlash (ACRCloud orqali)
- Katta hajmli videolarni avtomatik siqish
- Spotify va Apple Music havolalari bilan qo'shiqlar haqida ma'lumot
- Rate limiting va foydalanuvchilarni boshqarish
- Admin boshqaruv buyruqlari

## 🚂 Railway'da Deployment Qilish

1. [Railway](https://railway.app/) platformasiga kiring va GitHub hisobingiz bilan bog'lang

2. Yangi proyekt yarating va "Deploy from GitHub repo" ni tanlang

3. Ushbu repozitoriyani tanlang

4. Environment o'zgaruvchilarini sozlang:
   ```env
   # Asosiy sozlamalar
   TELEGRAM_BOT_TOKEN=your_bot_token
   ADMIN_IDS=your_telegram_id
   PORT=8080
   LOG_LEVEL=INFO

   # ACRCloud sozlamalari
   ACRCLOUD_HOST=your_acrcloud_host
   ACRCLOUD_ACCESS_KEY=your_acrcloud_access_key
   ACRCLOUD_ACCESS_SECRET=your_acrcloud_access_secret

   # Xotira sozlamalari
   MAX_FILE_AGE_HOURS=1
   MAX_DISK_PERCENT=80
   MAX_MEMORY_PERCENT=85
   CLEANUP_INTERVAL_SECONDS=300

   # Video sozlamalari
   MAX_VIDEO_SIZE_MB=450
   TARGET_VIDEO_SIZE_MB=45
   MAX_VIDEO_HEIGHT=720

   # Audio sozlamalari
   MAX_AUDIO_SIZE_MB=50
   AUDIO_BITRATE=192

   # Rate limiting
   MAX_REQUESTS_PER_MINUTE=30
   MAX_AUDIO_REQUESTS_PER_MINUTE=20
   MAX_TOTAL_SIZE_PER_HOUR_MB=1024
   ```

5. Railway avtomatik ravishda botni deploy qiladi

### ⚙️ Railway Cheklovlari va Optimizatsiya

- Railway bepul rejasida 500MB xotira mavjud
- Yuklanayotgan videolar 450MB dan oshmasligi kerak
- Vaqtinchalik fayllar har soatda tozalanadi
- Bot ishlashini monitoring qilish uchun `/stats` buyrug'idan foydalaning
- Health check endpointi: `https://your-app-name.railway.app/health`

## 🛠 Mahalliy Muhitda O'rnatish

1. Repositoriyani klonlash:
```bash
git clone https://github.com/username/video-downloader-bot.git
cd video-downloader-bot
```

2. Virtual muhit yaratish va aktivlashtirish:
```bash
python -m venv venv
# Windows uchun
venv\Scripts\activate
# Linux/Mac uchun
source venv/bin/activate
```

3. Kerakli paketlarni o'rnatish:
```bash
pip install -r requirements.txt
```

4. FFmpeg o'rnatish:
- Windows: [FFmpeg rasmiy saytidan](https://ffmpeg.org/download.html) yuklab oling
- Linux: `sudo apt-get install ffmpeg`
- Mac: `brew install ffmpeg`

5. `.env` faylini `.env.example` asosida sozlash

## 📝 Bot Buyruqlari

### Umumiy Foydalanuvchilar Uchun
- `/start` - Botni ishga tushirish
- `/help` - Yordam xabarini ko'rish
- Video havolasini yuborish - Videoni yuklab olish

### Admin Buyruqlari
- `/stats` - Bot statistikasini ko'rish
- `/admin` - Admin boshqaruv paneli:
  - `block <user_id> [duration]` - Foydalanuvchini bloklash
  - `unblock <user_id>` - Blokdan chiqarish
  - `reset <user_id>` - Foydalanuvchi cheklovlarini qayta o'rnatish
  - `stats <user_id>` - Foydalanuvchi statistikasini ko'rish

### Rate Limiting
- Har bir foydalanuvchi uchun:
  - 30 ta so'rov minutiga
  - 20 ta audio so'rov minutiga
  - 1GB umumiy hajm soatiga
- Video hajmi: maksimum 450MB
- Audio hajmi: maksimum 50MB

## 🔧 Xatoliklarni Tuzatish

1. **FFmpeg topilmadi** xatoligi:
   - FFmpeg to'g'ri o'rnatilganini tekshiring
   - Tizim PATH'iga qo'shilganini tekshiring

2. **Token xatoligi**:
   - `.env` faylida token to'g'ri kiritilganini tekshiring
   - BotFather'dan tokenni yangilang

3. **ACRCloud xatoligi**:
   - Kredensiallar to'g'ri kiritilganini tekshiring
   - ACRCloud hisobingiz aktivligini tekshiring

4. **Railway xatoliklari**:
   - Xotira yetishmovchiligi: `/stats` buyrug'i orqali tekshiring
   - Bot javob bermasa: Health check endpoint orqali tekshiring
   - Deployment xatoligi: Railway logs'larini tekshiring

5. **Rate Limiting xatoliklari**:
   - Foydalanuvchi bloklangan: `/admin stats <user_id>` orqali tekshiring
   - So'rovlar soni oshgan: Bir necha daqiqa kutish kerak
   - Xotira limiti oshgan: Bir soat kutish kerak

## 📄 Litsenziya

MIT litsenziyasi ostida tarqatiladi. Batafsil ma'lumot uchun [LICENSE](LICENSE) fayliga qarang.

## 🤝 Hissa Qo'shish

1. Fork qiling
2. O'zgartirishlar branch'ini yarating (`git checkout -b feature/yangixususiyat`)
3. O'zgarishlarni commit qiling (`git commit -am 'Yangi xususiyat qo'shildi'`)
4. Branch'ni push qiling (`git push origin feature/yangixususiyat`)
5. Pull Request yarating
