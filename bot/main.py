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
from aiogram.fsm.state import State, StatesGroup

from dotenv import load_dotenv

load_dotenv()

# --- Konfiguratsiya --- #
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

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
        'enter_name': "Ismingizni kiriting:",
        'enter_phone': "Telefon raqamingizni kiriting:",
        'choose_product': "Mahsulot turini tanlang:",
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
        'enter_name': "Введите ваше имя:",
        'enter_phone': "Введите ваш номер телефона:",
        'choose_product': "Выберите тип продукции:",
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

# --- Ariza qoldirish uchun holatlar (FSM) ---
class Form(StatesGroup):
    name = State()
    phone = State()
    product = State()

# --- Mahsulotlar ro'yxati uchun klaviatura ---
def products_keyboard(lang_code):
    products = {
        'uz': ["Karton qutilar", "Gofrokarton", "Kog'oz paketlar", "Yelimli paketlar (skotch)", "Boshqa"],
        'ru': ["Картонные коробки", "Гофрокартон", "Бумажные пакеты", "Клейкие ленты (скотч)", "Другое"]
    }
    buttons = [[KeyboardButton(text=p)] for p in products[lang_code]]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)

# --- Asosiy menyu tugmalarini qayta ishlash --- #
@dp.message(Command('cancel'))
@dp.message(F.text.casefold() == 'cancel')
async def cancel_handler(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        return

    await state.clear()
    user_data = await state.get_data()
    lang_code = user_data.get('language', 'uz')
    await message.answer("Bekor qilindi.", reply_markup=main_menu_keyboard(lang_code))

@dp.message(F.text.in_(texts['uz'].values()) | F.text.in_(texts['ru'].values()))
async def handle_main_menu(message: Message, state: FSMContext):
    user_data = await state.get_data()
    lang_code = user_data.get('language', 'uz')

    if message.text == texts[lang_code]['leave_request']:
        await state.set_state(Form.name)
        await message.answer(texts[lang_code]['enter_name'], reply_markup=ReplyKeyboardRemove())
    
    elif message.text == texts[lang_code]['about_company']:
        await message.answer(texts[lang_code]['about_text'], disable_web_page_preview=True)

    elif message.text == texts[lang_code]['change_lang']:
        await message.answer(texts['uz']['choose_lang'], reply_markup=language_keyboard())

# --- Ismni qabul qilish ---
@dp.message(Form.name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(Form.phone)
    user_data = await state.get_data()
    lang_code = user_data.get('language', 'uz')
    await message.answer(texts[lang_code]['enter_phone'])

# --- Telefon raqamini qabul qilish ---
@dp.message(Form.phone)
async def process_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await state.set_state(Form.product)
    user_data = await state.get_data()
    lang_code = user_data.get('language', 'uz')
    await message.answer(texts[lang_code]['choose_product'], reply_markup=products_keyboard(lang_code))

# --- Mahsulotni qabul qilish va arizani yakunlash ---
@dp.message(Form.product)
async def process_product(message: Message, state: FSMContext):
    user_data = await state.get_data()
    lang_code = user_data.get('language', 'uz')
    
    # Arizani adminga yuborish
    try:
        data = await state.get_data()
        data['product'] = message.text

        admin_message = (
            f"🔔 Yangi Ariza (PaketShop Bot)\n\n"
            f"<b>Mijoz:</b> {data.get('name', 'N/A')}\n"
            f"<b>Telefon:</b> {data.get('phone', 'N/A')}\n"
            f"<b>Qiziqqan mahsuloti:</b> {data.get('product', 'N/A')}\n\n"
            f"<b>Telegram:</b> @{message.from_user.username if message.from_user.username else 'N/A'}"
        )
        
        await bot.send_message(ADMIN_CHAT_ID, admin_message)
        logging.info("Xabar adminga muvaffaqiyatli yuborildi.")

        # Foydalanuvchiga javob yuborish
        await message.answer(texts[lang_code]['request_accepted'], reply_markup=main_menu_keyboard(lang_code))

    except Exception as e:
        logging.error(f"Adminga xabar yuborishda xatolik: {e}")
        await message.answer("Xatolik yuz berdi. Iltimos, keyinroq urinib ko'ring.", reply_markup=main_menu_keyboard(lang_code))
    finally:
        await state.clear()

# --- Chat ID'ni olish uchun maxsus buyruq ---
@dp.message(Command('get_chat_id'))
async def get_chat_id(message: Message):
    chat_id_message = f"Bu chatning ID'si: `{message.chat.id}`"
    logging.info(chat_id_message)
    await message.answer(chat_id_message)

# --- Botni ishga tushirish --- #
async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
