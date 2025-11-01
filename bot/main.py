import logging
import os
import json
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message, InlineKeyboardButton, InlineKeyboardMarkup, 
    ReplyKeyboardMarkup, KeyboardButton, WebAppInfo, CallbackQuery
)
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from fastapi import FastAPI, Request, Response
from dotenv import load_dotenv

# --- Logging sozlamalari ---
logging.basicConfig(level=logging.INFO)

# --- .env faylini yuklash ---
load_dotenv()

# --- Konfiguratsiya --- #
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
WEBAPP_URL = 'https://paket-shop-lead-generation.vercel.app/'

# Vercel bu o'zgaruvchini avtomatik tarzda o'rnatadi
VERCEL_URL = os.getenv("VERCEL_URL", "") 
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"{VERCEL_URL}{WEBHOOK_PATH}"

# --- Bot va Dispatcher --- #
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
bot = Bot(token=BOT_TOKEN, parse_mode="HTML")

# --- Matnlar (i18n) --- #
texts = {
    'uz': {
        'welcome': "Assalomu alaykum! PaketShop botiga xush kelibsiz!",
        'choose_lang': "Iltimos, tilni tanlang:",
        'main_menu': "Asosiy menyu",
        'leave_request': "✍️ Ariza qoldirish",
        'about_company': "ℹ️ Kompaniya haqida",
        'change_lang': "🇺🇿/🇷🇺 Tilni o'zgartirish",
        'about_text': "<b>PaketShop</b> - bu... (Kompaniya haqida to'liq ma'lumot shu yerda bo'ladi).\n\nBatafsil ma'lumot uchun saytimizga tashrif buyuring: <a href='https://paketshop.uz/'>paketshop.uz</a>",
        'request_prompt': "Ajoyib! Arizani to'ldirish uchun quyidagi tugmani bosing:",
        'fill_form': "📝 Arizani to'ldirish",
        'request_accepted': "Rahmat! Arizangiz qabul qilindi. Tez orada menejerimiz siz bilan bog'lanadi.",
    },
    'ru': {
        'welcome': "Здравствуйте! Добро пожаловать в бот PaketShop!",
        'choose_lang': "Пожалуйста, выберите язык:",
        'main_menu': "Главное меню",
        'leave_request': "Оставить заявку",
        'about_company': "О компании",
        'change_lang': "🇺🇿/🇷🇺 Сменить язык",
        'about_text': "<b>PaketShop</b> - это... (Полная информация о компании будет здесь).\n\nДля получения дополнительной информации посетите наш сайт: <a href='https://paketshop.uz/'>paketshop.uz</a>",
        'request_prompt': "Отлично! Нажмите на кнопку ниже, чтобы заполнить заявку:",
        'fill_form': "📝 Заполнить заявку",
        'request_accepted': "Спасибо! Ваша заявка принята. Наш менеджер скоро с вами свяжется.",
    }
}

# --- Klaviaturalar --- #
def language_keyboard():
    buttons = [
        [InlineKeyboardButton(text="O'zbekcha 🇺🇿", callback_data="lang_uz")],
        [InlineKeyboardButton(text="Русский 🇷🇺", callback_data="lang_ru")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def main_menu_keyboard(lang_code):
    buttons = [
        [KeyboardButton(text=texts[lang_code]['leave_request'])],
        [KeyboardButton(text=texts[lang_code]['about_company'])],
        [KeyboardButton(text=texts[lang_code]['change_lang'])]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# --- Handlers --- #
@dp.message(CommandStart())
async def send_welcome(message: Message, state: FSMContext):
    await message.answer(texts['uz']['choose_lang'], reply_markup=language_keyboard())

@dp.callback_query(F.data.startswith('lang_'))
async def process_language_select(callback_query: CallbackQuery, state: FSMContext):
    lang_code = callback_query.data.split('_')[1]
    await state.update_data(language=lang_code)
    await callback_query.message.delete()
    await callback_query.message.answer(
        texts[lang_code]['welcome'], 
        reply_markup=main_menu_keyboard(lang_code)
    )
    await callback_query.answer()

@dp.message(Command('get_chat_id'))
async def get_chat_id(message: Message):
    chat_id_message = f"Bu chatning ID'si: `{message.chat.id}`"
    logging.info(chat_id_message)
    await message.answer(chat_id_message)

@dp.message()
async def handle_messages(message: Message, state: FSMContext):
    user_data = await state.get_data()
    lang_code = user_data.get('language', 'uz')

    if message.web_app_data:
        logging.info("Web App ma'lumoti qabul qilindi.")
        try:
            data = json.loads(message.web_app_data.data)
            await message.answer(texts[lang_code]['request_accepted'])
            
            admin_message = (
                f"🔔 Yangi Ariza (PaketShop Bot)\n\n"
                f"<b>Mijoz:</b> {data.get('name', 'N/A')}\n"
                f"<b>Telefon:</b> {data.get('phone', 'N/A')}\n"
                f"<b>Qiziqqan mahsuloti:</b> {data.get('product', 'N/A')}\n\n"
                f"<b>Telegram:</b> @{message.from_user.username if message.from_user.username else 'N/A'}"
            )
            
            await bot.send_message(ADMIN_CHAT_ID, admin_message)
            logging.info("Xabar adminga muvaffaqiyatli yuborildi.")
        except Exception as e:
            logging.error(f"Adminga xabar yuborishda xatolik: {e}")
        return

    text = message.text
    if text == texts[lang_code]['leave_request']:
        webapp_button = InlineKeyboardButton(
            text=texts[lang_code]['fill_form'],
            web_app=WebAppInfo(url=f"{WEBAPP_URL}?lang={lang_code}")
        )
        await message.answer(
            texts[lang_code]['request_prompt'],
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[webapp_button]])
        )
    elif text == texts[lang_code]['about_company']:
        await message.answer(texts[lang_code]['about_text'], disable_web_page_preview=True)
    elif text == texts[lang_code]['change_lang']:
        await message.answer(texts['uz']['choose_lang'], reply_markup=language_keyboard())

# --- FastAPI va Webhook sozlamalari --- #
@asynccontextmanager
async def lifespan(app: FastAPI):
    if VERCEL_URL:
        logging.info(f"Setting webhook to: {WEBHOOK_URL}")
        await bot.set_webhook(url=WEBHOOK_URL, allowed_updates=dp.resolve_used_update_types())
        yield
        logging.info("Deleting webhook.")
        await bot.delete_webhook()
    else:
        logging.info("Running in local mode, skipping webhook setup.")
        yield

app = FastAPI(lifespan=lifespan)

@app.post(WEBHOOK_PATH)
async def bot_webhook(update: dict):
    try:
        telegram_update = types.Update(**update)
        await dp.feed_update(bot=bot, update=telegram_update)
    except Exception as e:
        logging.error(f"Error processing update: {e}")
    return Response(status_code=200)

@app.get("/")
async def read_root():
    return {"status": "Bot is running"}
