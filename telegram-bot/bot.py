import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram import F
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Kontakt so'rash uchun tugma
def get_contact_keyboard():
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Kontaktni ulashish", request_contact=True)]],
        resize_keyboard=True
    )
    return kb

# WebApp tugmasi uchun tugma
def get_webapp_keyboard():
    webapp_url = os.getenv("WEBAPP_URL", "https://your-webapp-url.com")
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Anonymous Chat", web_app=WebAppInfo(url=webapp_url))]],
        resize_keyboard=True
    )
    return kb

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        "Salom! Iltimos, kontakt raqamingizni ulashing:",
        reply_markup=get_contact_keyboard()
    )

@dp.message(F.contact)
async def contact_handler(message: types.Message):
    # Foydalanuvchi kontaktini saqlash (hozircha faylga yozamiz, keyin DB)
    user_id = message.from_user.id
    contact = message.contact.phone_number
    with open("contacts.txt", "a") as f:
        f.write(f"{user_id}: {contact}\n")
    await message.answer(
        "Rahmat! Endi Anonymous Chat uchun tugmani bosing:",
        reply_markup=get_webapp_keyboard()
    )

if __name__ == "__main__":
    import asyncio
    asyncio.run(dp.start_polling(bot))
