import asyncio
import logging
import os
import json

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (Message, InlineKeyboardButton, InlineKeyboardMarkup, 
                           ReplyKeyboardMarkup, KeyboardButton, WebAppInfo, CallbackQuery)
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext

from dotenv import load_dotenv

load_dotenv()

# --- Konfiguratsiya --- #
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
WEBAPP_URL = 'https://your-domain.com/index.html' # TODO: Veb-ilova URL manzilini sozlash kerak

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

# --- Tilni tanlash uchun inline klaviatura --- #
def language_keyboard():
    buttons = [
        [InlineKeyboardButton(text="O'zbekcha 🇺🇿", callback_data="lang_uz")],
        [InlineKeyboardButton(text="Русский 🇷🇺", callback_data="lang_ru")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# --- Asosiy menyu uchun reply klaviatura --- #
def main_menu_keyboard(lang_code):
    buttons = [
        [KeyboardButton(text=texts[lang_code]['leave_request'])],
        [KeyboardButton(text=texts[lang_code]['about_company'])],
        [KeyboardButton(text=texts[lang_code]['change_lang'])]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# --- /start buyrug'i --- #
@dp.message(CommandStart())
async def send_welcome(message: Message):
    await message.answer(texts['uz']['choose_lang'], reply_markup=language_keyboard())

# --- Til tanlovini qayta ishlash --- #
@dp.callback_query(F.data.startswith('lang_'))
async def process_language_select(callback_query: CallbackQuery, state: FSMContext):
    lang_code = callback_query.data.split('_')[1]
    await state.update_data(language=lang_code)
    
    await callback_query.message.delete() # Til tanlash xabarini o'chirish
    await callback_query.message.answer(
        texts[lang_code]['welcome'], 
        reply_markup=main_menu_keyboard(lang_code)
    )
    await callback_query.answer()

# --- Asosiy menyu tugmalarini qayta ishlash --- #
@dp.message()
async def handle_menu_buttons(message: Message, state: FSMContext):
    user_data = await state.get_data()
    lang_code = user_data.get('language', 'uz') # default 'uz'

    # Ariza qoldirish
    if message.text == texts[lang_code]['leave_request']:
        webapp_button = InlineKeyboardButton(
            text=texts[lang_code]['fill_form'],
            web_app=WebAppInfo(url=f"{WEBAPP_URL}?lang={lang_code}")
        )
        await message.answer(
            texts[lang_code]['request_prompt'],
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[webapp_button]])
        )

    # Kompaniya haqida
    elif message.text == texts[lang_code]['about_company']:
        await message.answer(texts[lang_code]['about_text'], disable_web_page_preview=True)

    # Tilni o'zgartirish
    elif message.text == texts[lang_code]['change_lang']:
        await message.answer(texts['uz']['choose_lang'], reply_markup=language_keyboard())
        
    # WebApp'dan kelgan ma'lumotni qabul qilish
    elif message.web_app_data:
        await message.answer(texts[lang_code]['request_accepted'])
        
        # Adminga xabar yuborish
        data = json.loads(message.web_app_data.data)
        admin_message = (
            f"🔔 Yangi Ariza (PaketShop Bot)\n\n"
            f"<b>Mijoz:</b> {data.get('name', 'N/A')}\n"
            f"<b>Telefon:</b> {data.get('phone', 'N/A')}\n"
            f"<b>Qiziqqan mahsuloti:</b> {data.get('product', 'N/A')}\n\n"
            f"<b>Telegram:</b> @{message.from_user.username if message.from_user.username else 'N/A'}"
        )
        await bot.send_message(ADMIN_CHAT_ID, admin_message)

# --- Botni ishga tushirish --- #
async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
