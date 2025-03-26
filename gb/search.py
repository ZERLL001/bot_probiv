import json
import os
import time
import datetime
import phonenumbers
from phonenumbers import carrier, geocoder
from aiogram import types, Dispatcher
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dadata import DadataAsync, Dadata
import requests
import re
from db import Database

# Глобальная инициализация базы (база находится в папке stats)
db = Database('stats/database.db')

# Инициализация клиентов Dadata
token = 'dadatatoken'
secret = 'dadata secret'
dadata = DadataAsync(token, secret)
dadata_for_inn = Dadata(token)

LEAKOSINT_API_KEY = "6262648152:AEx1jTW8"

def send_reques(request_text):
    url = 'https://leakosintapi.com/'
    token = LEAKOSINT_API_KEY
    data = {
        "token": token,
        "request": request_text,
        "limit": 1000,
        "lang": "ru"
    }
    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return f"❌ Ошибка: {e}"

def format_combined_response(response):
    # Отображаются только нужные поля согласно образцу
    field_mapping = {
        'PossibleNames': "Возможные имена",
        'FullName': "Возможное ФИО",
        'VkID': "Вконтакте",
        'BDay': "Дата рождения",
        'Email': "Email",
        'FullName': "Полное Имя",
        'Age': "Возраст",
        'PointAddress': "Адресс",
        'CreditCard': "Мобильный банк",
        'NickName': "Ник",
        'Password(SHA-256)': "Пороль",
        'Tags': "Возможные имена",
        'Snils': "Снилс",
        'IP': "Айпи",
        'Telegram': "Telegram",
        'TelegramGroups': "Группы Telegram",
        'Registrations': "Регистрации",
        'Interested': "Интересовались",
        'Reputation': "Репутация"
    }
    emoji_mapping = {
        'PossibleNames': "📓",
        'FullName': "👤",
        'VkID': "👨‍💻",
        'BDay': "🏥",
        'Email': "📪",
        'FullName': "👥",
        'Age': "🚑",
        'PointAddress': "🏠",
        'CreditCard': "💳",
        'NickName': "📕",
        'Password(SHA-256)': "📟",
        'Tags': "📓",
        'Snils': "🔖",
        'IP': "🖥",
        'Telegram': "📧",
        'TelegramGroups': "👥",
        'Registrations': "🌐",
        'Interested': "👁",
        'Reputation': "🏅"
    }
    aggregated = {}
    if response and 'List' in response:
        for db_name, db_info in response['List'].items():
            for entry in db_info.get('Data', []):
                for key, value in entry.items():
                    if key in field_mapping:
                        aggregated.setdefault(key, []).append(value)
        for key in aggregated:
            try:
                aggregated[key] = sorted(set(aggregated[key]))
            except Exception:
                aggregated[key] = list(set(aggregated[key]))
        formatted_str = ""
        for key in field_mapping:
            if key in aggregated:
                emoji = emoji_mapping.get(key, "")
                values_joined = ", ".join(str(v) for v in aggregated[key])
                formatted_str += f"{emoji} {field_mapping[key]}: {values_joined}\n"
        return formatted_str
    else:
        return "Нет данных для отображения."

LIMITS_FILE = "search_limits.json"
SEARCH_LIMIT = 10

def load_search_limits():
    if os.path.exists(LIMITS_FILE):
        with open(LIMITS_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_search_limits(limits):
    with open(LIMITS_FILE, "w") as f:
        json.dump(limits, f, indent=4)

def check_search_limit(user_id):
    limits = load_search_limits()
    now = time.time()
    user_id_str = str(user_id)
    if user_id_str in limits:
        last_reset_time = limits[user_id_str]["reset_time"]
        search_count = limits[user_id_str]["count"]
        if now - last_reset_time > 3600:
            limits[user_id_str] = {"count": 0, "reset_time": now}
            save_search_limits(limits)
            return True
        elif search_count >= SEARCH_LIMIT:
            return False
        return True
    limits[user_id_str] = {"count": 0, "reset_time": now}
    save_search_limits(limits)
    return True

def increment_search_count(user_id):
    limits = load_search_limits()
    user_id_str = str(user_id)
    limits[user_id_str]["count"] += 1
    save_search_limits(limits)

# Функция для формирования строки репутации на основе реакций для данного запроса
def build_reputation_line(query):
    counts = db.get_reaction_counts(query)
    likes = counts.get("up", 0)
    dislikes = counts.get("down", 0)
    return f'🏅 Репутация: ({likes})👍 ({dislikes})👎'

# Функция для обработки поиска по номеру телефона
async def process_phone_number(message: types.Message):
    user_id = message.from_user.id
    if not check_search_limit(user_id):
        await message.reply("❗️ Превышен лимит поисков. Попробуйте позже.")
        return

    number = message.text.strip().replace("+", "").replace(" ", "")
    parsed_number = phonenumbers.parse("+" + number)
    if not phonenumbers.is_valid_number(parsed_number):
        await message.reply("❗️ Неверный формат номера.", parse_mode='MARKDOWN')
        return

    country = phonenumbers.region_code_for_number(parsed_number) or "Неизвестно"
    operator = carrier.name_for_number(parsed_number, "ru") or "неопределен"
    leak_data = send_reques(number)
    print(leak_data)
    db.log_search(user_id, number)
    search_count = db.count_unique_searches(number)
    leak_dat = format_combined_response(leak_data)

    # Формируем клавиатуру: передаем запрос в callback_data
    reaction_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👍", callback_data=f"react|up|{number}"),
            InlineKeyboardButton(text="👎", callback_data=f"react|down|{number}")
        ]
    ])

    sent_msg = await message.answer(
        f'📱\n'
        f'├ Номер: <i>{number}</i>\n'
        f'├ Страна: <i>{country}</i>\n'
        f'└ Оператор: <i>{operator}</i>\n\n'
        f'{leak_dat}\n\n'
        f'👁 Интересовались: {search_count} человек(а)\n'
        f'{build_reputation_line(number)}',
        parse_mode='HTML',
        reply_markup=reaction_keyboard
    )

    increment_search_count(user_id)
    db.update_stats(user_id, phone_numbers=1, views=1, ratings=0)

# Функция для обработки поиска по email
async def process_email(message: types.Message):
    user_id = message.from_user.id
    if not check_search_limit(user_id):
        await message.reply("❗️ Превышен лимит поисков. Попробуйте позже.")
        return

    email = message.text.strip()
    if not re.match(r'^\S+@\S+\.\S+$', email):
        await message.reply("❗️ Неверный формат email.", parse_mode='MARKDOWN')
        return

    leak_data = send_reques(email)
    print(leak_data)
    db.log_search(user_id, email)
    search_count = db.count_unique_searches(email)
    leak_info = format_combined_response(leak_data)
    reaction_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👍", callback_data=f"react|up|{email}"),
            InlineKeyboardButton(text="👎", callback_data=f"react|down|{email}")
        ]
    ])
    sent_msg = await message.answer(
        f'✉️ <b>Email:</b> <i>{email}</i>\n\n'
        f'{leak_info}\n\n'
        f'👁 Интересовались: {search_count} человек(а)\n'
        f'{build_reputation_line(email)}',
        parse_mode='HTML',
        reply_markup=reaction_keyboard
    )
    increment_search_count(user_id)
    db.update_stats(user_id, emails=1, views=1, ratings=0)

# Функция для обработки поиска по адресу
async def process_address(message: types.Message):
    user_id = message.from_user.id
    if not check_search_limit(user_id):
        await message.reply("❗️ Превышен лимит поисков. Попробуйте позже.")
        return

    try:
        address_query = message.text.strip()
        db.log_search(user_id, address_query)
        search_count = db.count_unique_searches(address_query)
        result = await dadata.clean("address", address_query)
        reaction_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="👍", callback_data=f"react|up|{address_query}"),
                InlineKeyboardButton(text="👎", callback_data=f"react|down|{address_query}")
            ]
        ])
        sent_msg = await message.answer(
            f'🏠 ***Адрес***\n'
            f'├ **Полный адрес:** `{result["result"]}`\n'
            f'├ **Улица:** `{result.get("street", "Не найдено")}`\n'
            f'├ **Дом:** `{result.get("house", "Не найдено")}`\n'
            f'├ **Квартира:** `{result.get("flat", "Не найдено")}`\n'
            f'├ **Почтовый индекс:** `{result.get("postal_code", "Не найдено")}`\n'
            f'└ **Регион:** `{result.get("region", "Не найдено")}`\n\n'
            f'👁 Интересовались: {search_count} человек(а)\n'
            f'{build_reputation_line(address_query)}',
            parse_mode='MARKDOWN',
            reply_markup=reaction_keyboard
        )
        increment_search_count(user_id)
    except Exception as e:
        print(f"Ошибка при обработке адреса: {e}")
        await message.answer("❗️ Ошибка при обработке запроса.")

# Функция для обработки поиска по названию компании
async def process_company(message: types.Message):
    user_id = message.from_user.id
    if not check_search_limit(user_id):
        await message.reply("❗️ Превышен лимит поисков. Попробуйте позже.")
        return

    try:
        company_name = message.text.split(maxsplit=1)[1]
        db.log_search(user_id, company_name)
        search_count = db.count_unique_searches(company_name)
        result = await dadata.suggest("party", company_name)
        if result:
            company_info = result[0]["data"]
            reaction_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="👍", callback_data=f"react|up|{company_name}"),
                    InlineKeyboardButton(text="👎", callback_data=f"react|down|{company_name}")
                ]
            ])
            sent_msg = await message.answer(
                f'🏛 ***Компания***\n'
                f'├ **Название:** `{company_info["name"]["full_with_opf"]}`\n'
                f'├ **Адрес:** `{company_info["address"]["value"]}`\n'
                f'├ **ИНН:** `{company_info["inn"]}`\n'
                f'├ **ОГРН:** `{company_info["ogrn"]}`\n'
                f'└ **Дата регистрации:** `{datetime.datetime.fromtimestamp(company_info["ogrn_date"] / 1000).strftime("%Y-%m-%d")}`\n\n'
                f'👁 Интересовались: {search_count} человек(а)\n'
                f'{build_reputation_line(company_name)}',
                parse_mode='MARKDOWN',
                reply_markup=reaction_keyboard
            )
            await sent_msg.edit_text(sent_msg.text, parse_mode='MARKDOWN', reply_markup=reaction_keyboard)
            increment_search_count(user_id)
        else:
            await message.answer("❗️ Компания не найдена.")
    except Exception as e:
        print(f"Ошибка при обработке компании: {e}")
        await message.answer("❗️ Ошибка при обработке запроса.")

# Функция для обработки поиска по ИНН
async def process_inn(message: types.Message):
    user_id = message.from_user.id
    if not check_search_limit(user_id):
        await message.reply("❗️ Превышен лимит поисков. Попробуйте позже.")
        return

    try:
        inn = message.text.split(maxsplit=1)[1]
        db.log_search(user_id, inn)
        search_count = db.count_unique_searches(inn)
        result = dadata_for_inn.find_by_id("party", inn)
        if result:
            company_info = result[0]["data"]
            reaction_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="👍", callback_data=f"react|up|{inn}"),
                    InlineKeyboardButton(text="👎", callback_data=f"react|down|{inn}")
                ]
            ])
            sent_msg = await message.answer(
                f'🏛 ***Компания***\n'
                f'├ **Название:** `{company_info["name"]["full_with_opf"]}`\n'
                f'├ **Адрес:** `{company_info["address"]["value"]}`\n'
                f'├ **ИНН:** `{company_info["inn"]}`\n'
                f'├ **ОГРН:** `{company_info["ogrn"]}`\n'
                f'└ **Дата регистрации:** `{datetime.datetime.fromtimestamp(company_info["ogrn_date"] / 1000).strftime("%Y-%m-%d")}`\n\n'
                f'👁 Интересовались: {search_count} человек(а)\n'
                f'{build_reputation_line(inn)}',
                parse_mode='MARKDOWN',
                reply_markup=reaction_keyboard
            )
            await sent_msg.edit_text(sent_msg.text, parse_mode='MARKDOWN', reply_markup=reaction_keyboard)
            increment_search_count(user_id)
        else:
            await message.answer("❗️ Компания с таким ИНН не найдена.")
    except Exception as e:
        print(f"Ошибка при обработке ИНН: {e}")
        await message.answer("❗️ Ошибка при обработке запроса.")

# Обработчик реакций (callback query)
