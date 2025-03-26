from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

main_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='🔎 Показать команды для поиска', callback_data='requests_commands')],
    [
        InlineKeyboardButton(text='⚙️ Мой аккаунт', callback_data='my_acc'),
        InlineKeyboardButton(text='🆘 Поддержка', callback_data='help_ing')
    ],
    [
        InlineKeyboardButton(text='🤝 Партнёрам', callback_data='parter'),
        InlineKeyboardButton(text='🤖 Создать бот', callback_data='my_bot')
    ]
])

back_command_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='🔙 Назад', callback_data='back_to_menu')]
])
