import asyncio
import re
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Импорты из ваших модулей
from keyboards import main_keyboard, back_command_keyboard
from db import Database
from search import (
    build_reputation_line, 
    process_phone_number, 
    process_email,
    process_address, 
    process_company, 
    process_inn
)

# Инициализация бота и диспетчера
bot = Bot(
    token='7227733030:AAGbLiSNeEmy1W9Gxf5N9hm3e9JVnpyVqmo',
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()
db = Database('stats/database.db')

# Подключение к базе рефералов
conn = sqlite3.connect("stats/referrals.db", check_same_thread=False)
cursor = conn.cursor()

# Создание таблиц (если их нет)
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    referrer_id INTEGER,
    referrals_count INTEGER DEFAULT 0
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS referrals (
    referrer_id INTEGER,
    referred_id INTEGER,
    FOREIGN KEY (referrer_id) REFERENCES users (user_id),
    FOREIGN KEY (referred_id) REFERENCES users (user_id)
)
""")
conn.commit()

def add_user(user_id: int, referrer_id: int = None) -> None:
    """Добавляет пользователя в базу рефералов."""
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO users (user_id, referrer_id) VALUES (?, ?)", 
            (user_id, referrer_id)
        )
        if referrer_id:
            cursor.execute(
                "UPDATE users SET referrals_count = referrals_count + 1 WHERE user_id = ?", 
                (referrer_id,)
            )
    conn.commit()

def get_referrals_count(user_id: int) -> int:
    """Возвращает количество рефералов пользователя."""
    cursor.execute("SELECT referrals_count FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    return result[0] if result else 0

@dp.message(Command("start"))
async def start_command(message: Message):
    user_id = message.from_user.id
    referrer_id = None

    if len(message.text.split()) > 1:
        try:
            referrer_id = int(message.text.split()[1])
            if referrer_id == user_id:
                await message.answer("❌ Нельзя использовать свою реферальную ссылку!")
                return
        except ValueError:
            pass

    add_user(user_id, referrer_id)

    if not db.user_exists(user_id):
        db.add_user(user_id)
        db.set_nickname(user_id, message.from_user.username)
        db.set_signup(user_id, "done")

    await message.answer(
        "Откройте мир возможностей с нами! Мы анализируем информацию из открытых источников, "
        "исключительно полученную законным путем, и превращаем её в ценные знания для экспериментов и поиска.\n\n"
        "<b>Выберите действие:</b>",
        reply_markup=main_keyboard
    )

@dp.callback_query(lambda query: query.data == 'requests_commands')
async def show_commands(callback: CallbackQuery):
    await callback.message.answer(
        "⬇️ Примеры команд для ввода:\n\n"
        "👤 Поиск по имени\n"
        "├  Блогер (Поиск по тегу)\n"
        "└  Фамилия Имя Отчество ДД.ММ.ГГГГ\n\n"
        "🚗 Поиск по транспорту\n"
        "├  А777АА777 - поиск авто по РФ\n"
        "└  WDB4632761X337911 - поиск по VIN\n\n"
        "👨 Социальные сети\n"
        "├  instagram.com/username - Instagram\n"
        "├  vk.com/id123456 - Вконтакте\n"
        "├  facebook.com/profile.php?id=1 - Facebook\n"
        "├  tiktok.com/@username - Tiktok\n"
        "└  ok.ru/profile/123456 - Одноклассники\n\n"
        "📱 79999999999 - для поиска по номеру телефона\n"
        "📨 elonmusk@spacex.com - для поиска по Email\n"
        "📧 12345678, @login или перешлите сообщение - поиск по Telegram аккаунту\n"
        "🏘 77:01:0001075:1361 - поиск по кадастровому номеру\n\n"
        "📖 /tag блогер - поиск по тегам в телефонной книжке\n"
        "🏛 /company Сбербанк - поиск по юр лицам\n"
        "📑 /inn 123456789123 - поиск по ИНН\n"
        "🗂 /vy 1234567890 - проверка водительского удостоверения\n\n"
        "📸 Отправьте фото человека, чтобы найти его или двойника на сайтах ВК.\n"
        "🚙 Отправьте фото номера автомобиля, чтобы получить о нем информацию.\n"
        "🙂 Отправьте стикер или эмодзи, чтобы найти создателя.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=back_command_keyboard
    )

@dp.callback_query(lambda query: query.data == 'back_to_menu')
async def back_to_menu(callback: CallbackQuery):
    await callback.message.answer(
        "Откройте мир возможностей с нами! Мы анализируем информацию из открытых источников, "
        "исключительно полученную законным путем, и превращаем её в ценные знания для экспериментов и поиска.\n\n"
        "<b>Выберите действие:</b>",
        reply_markup=main_keyboard
    )

@dp.callback_query(lambda query: query.data == 'help_ing')
async def help_ing(callback: CallbackQuery):
    await callback.message.answer(
        "Пожалуйста, опишите свою проблему и расскажите о ней нам!\n@Augustusov"
    )

@dp.callback_query(lambda query: query.data == 'my_bot')
async def my_bot(callback: CallbackQuery):
    await callback.message.answer("Coming Soon")

@dp.callback_query(lambda query: query.data == 'parter')
async def parter(callback: CallbackQuery):
    me = await bot.get_me()
    count = get_referrals_count(callback.from_user.id)
    await callback.message.answer(
        f"👋 Добро пожаловать!\n\n"
        f"🔗 Ваша реферальная ссылка: https://t.me/{me.username}?start={callback.from_user.id}\n\n"
        f"💼 Пригласите друзей и зарабатывайте бонусы!\n"
        f"👥 У вас {count} рефералов."
    )

@dp.callback_query(lambda query: query.data == 'my_acc')
async def my_account(callback: CallbackQuery):
    user_id = callback.from_user.id
    nickname = db.get_nickname(user_id) or "Не задан"
    signup = db.get_signup(user_id) or "Не задан"
    wallet = db.get_wallet(user_id)
    partner_account = db.get_partner_account(user_id)
    query_limit = db.get_query_limit(user_id)

    stats = db.cursor.execute(
        "SELECT photos, cars, emails, phone_numbers FROM users WHERE user_id=?",
        (user_id,)
    ).fetchone()
    photos, cars, emails, phone_numbers = stats if stats else (0, 0, 0, 0)

    account_text = (
        "<b>Мой аккаунт</b>\n"
        "Вся необходимая информация о вашем профиле\n\n"
        f"👁‍🗨 ID: {user_id}\n"
        f"👁‍🗨 Регистрация: {signup}\n\n"
        f"💶 Мой кошелёк: {wallet}\n"
        f"💷 Мой партнёрский счёт: {partner_account}\n"
        f"⚙️ Лимит запросов в сутки: {query_limit}\n\n"
        "🔎 Моя статистика запросов:\n"
        f"├ Фотографий: {photos}\n"
        f"├ Автомобилей: {cars}\n"
        f"├ Электронных почт: {emails}\n"
        f"└ Номеров телефонов: {phone_numbers}"
    )
    await callback.message.answer(account_text)

@dp.message(lambda message: re.match(r'^\+?\d{10,15}$', message.text))
async def phone_number_handler(message: Message):
    await process_phone_number(message)

@dp.message(lambda message: re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', message.text))
async def email_handler(message: Message):
    await process_email(message)

@dp.message(lambda message: ',' in message.text)
async def kadaster_number_handler(message: Message):
    await process_address(message)

@dp.message(Command("company"))
async def company_handler(message: Message):
    await process_company(message)

@dp.message(Command("inn"))
async def inn_handler(message: Message):
    await process_inn(message)

@dp.callback_query(lambda c: c.data and c.data.startswith("react|"))
async def reaction_handler(callback: CallbackQuery):
    parts = callback.data.split("|")
    if len(parts) < 3:
        await callback.answer("Ошибка данных.")
        return
    reaction_type, query = parts[1], parts[2]
    user_id = callback.from_user.id

    if db.reaction_exists(query, user_id):
        await callback.answer("Вы уже поставили реакцию.", show_alert=True)
        return

    if reaction_type == "up":
        db.update_stats(user_id, ratings=1)
    elif reaction_type == "down":
        db.update_stats(user_id, ratings=-1)

    db.add_reaction(query, user_id, reaction_type)
    await callback.answer("Ваша реакция учтена!")

    new_rep = build_reputation_line(query)
    new_text = re.sub(r"🏅 Репутация: \(\d+\)👍 \(\d+\)👎", new_rep, callback.message.text)
    await callback.message.edit_text(
        new_text,
        reply_markup=callback.message.reply_markup
    )

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())