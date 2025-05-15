# Anonymous Chat

Zamonaviy texnologiyalardan foydalangan holda Telegram WebApp uchun random anonymous chat tizimi.

## Tuzilma

```
anonymous-chat/
│
├── backend/         # FastAPI + WebSocket (Python)
│   ├── app/
│   │   ├── main.py
│   │   └── .env
│   └── requirements.txt
│
├── frontend/        # React (WebApp UI)
│   ├── public/
│   │   └── index.html
│   ├── src/
│   │   ├── App.js
│   │   └── index.js
│   └── package.json
│
├── telegram-bot/    # Telegram bot (Python)
│   ├── bot.py
│   ├── .env
│   └── requirements.txt
│
└── README.md        # Loyihani ishga tushirish uchun ko‘rsatmalar
```

## Ishga tushirish

### 1. Telegram Bot
1. `telegram-bot/requirements.txt` orqali kutubxonalarni o‘rnating.
2. `.env` faylida o‘z token va WebApp URL manzilingizni kiriting.
3. `python bot.py` bilan ishga tushiring.

### 2. Backend
1. `backend/requirements.txt` orqali kutubxonalarni o‘rnating.
2. Redis server ishga tushgan bo‘lishi kerak (`REDIS_URL` sozlang).
3. `uvicorn app.main:app --reload` bilan ishga tushiring.

### 3. Frontend
1. `npm install` orqali kutubxonalarni o‘rnating.
2. `npm start` bilan ishga tushiring.

## Tizim ishlash tartibi
- Foydalanuvchi Telegram botga /start bosadi va kontaktini ulashadi.
- Bot WebApp tugmasini yuboradi.
- WebApp ochiladi va foydalanuvchi random chatga ulanadi.

## Texnologiyalar
- Telegram Bot: Python (aiogram)
- Backend: FastAPI, Redis
- Frontend: React

---

Aloqa va muammolar bo‘yicha: @yourusername
