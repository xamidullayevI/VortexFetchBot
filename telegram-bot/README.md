# 🤖 Video Yuklovchi Telegram Bot

Ko'plab platformalardan video yuklash imkoniyatiga ega Telegram bot.

## 📋 Imkoniyatlari

- YouTube, Instagram, TikTok, Facebook va boshqa platformalardan video yuklash
- Videolardan audio ajratib olish
- Videodagi musiqani aniqlash (ACRCloud orqali)
- Katta hajmli videolarni avtomatik siqish
- Spotify va Apple Music havolalari bilan qo'shiqlar haqida ma'lumot

## 🚂 Railway'da Deployment Qilish

1. [Railway](https://railway.app/) platformasiga kiring va GitHub hisobingiz bilan bog'lang

2. Yangi proyekt yarating va "Deploy from GitHub repo" ni tanlang

3. Ushbu repozitoriyani tanlang

4. Environment o'zgaruvchilarini sozlang:
   ```env
   TELEGRAM_BOT_TOKEN=your_bot_token
   ACRCLOUD_HOST=your_acrcloud_host
   ACRCLOUD_ACCESS_KEY=your_acrcloud_access_key
   ACRCLOUD_ACCESS_SECRET=your_acrcloud_access_secret
   ADMIN_IDS=your_telegram_id
   MAX_FILE_AGE_HOURS=1
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

5. `.env` faylini sozlash:
```env
TELEGRAM_BOT_TOKEN=your_bot_token
ACRCLOUD_HOST=your_acrcloud_host
ACRCLOUD_ACCESS_KEY=your_acrcloud_access_key
ACRCLOUD_ACCESS_SECRET=your_acrcloud_access_secret
ADMIN_IDS=your_telegram_id
```

## 🚀 Ishga Tushirish

```bash
python main.py
```

## 📝 Konfiguratsiya

### Telegram Bot Token olish
1. [@BotFather](https://t.me/BotFather) ga boring
2. `/newbot` buyrug'ini yuboring
3. Bot nomini va username'ini kiriting
4. Olingan tokenni `.env` fayliga saqlang

### ACRCloud kredensiallarini olish
1. [ACRCloud](https://www.acrcloud.com/) ga ro'yxatdan o'ting
2. Yangi proyekt yarating
3. Audio Recognition uchun kredensiallarni oling
4. Olingan ma'lumotlarni `.env` fayliga saqlang

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

## 📄 Litsenziya

MIT litsenziyasi ostida tarqatiladi. Batafsil ma'lumot uchun [LICENSE](LICENSE) fayliga qarang.

## 🤝 Hissa Qo'shish

1. Fork qiling
2. O'zgartirishlar branch'ini yarating (`git checkout -b feature/yangixususiyat`)
3. O'zgarishlarni commit qiling (`git commit -am 'Yangi xususiyat qo'shildi'`)
4. Branch'ni push qiling (`git push origin feature/yangixususiyat`)
5. Pull Request yarating
