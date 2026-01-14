from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

def main_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="⭐ Заработать Звёзды"), KeyboardButton(text="💎 Задания")],
        [KeyboardButton(text="🎁 Вывести Звёзды")],
        [KeyboardButton(text="👥 Купить Подписчиков")]
    ], resize_keyboard=True)

def tasks_cabinet_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Мои Задания", callback_data="my_tasks")],
        [InlineKeyboardButton(text="💰 Создать Задание", callback_data="create_task")],
        [InlineKeyboardButton(text="💳 Пополнить Рекламный Баланс", callback_data="deposit_stars_menu")],
        [InlineKeyboardButton(text="ℹ️ Как пользоваться?", callback_data="ad_instruction")]
    ])

def deposit_methods_kb(amount):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="С обычного баланса", callback_data=f"dep_usual_{amount}")],
        [InlineKeyboardButton(text="Telegram Stars", callback_data=f"dep_stars_{amount}")]
    ])

def withdraw_gifts_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="15⭐", callback_data="wd_15"),
         InlineKeyboardButton(text="25⭐", callback_data="wd_25")],
        [InlineKeyboardButton(text="50⭐", callback_data="wd_50"),
         InlineKeyboardButton(text="100⭐", callback_data="wd_100")]
    ])

def task_kb(task_id, channel):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔎 Перейти", url=f"https://t.me/{channel.replace('@','')}"),
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"check_{task_id}")
        ],
        [InlineKeyboardButton(text="⏩ Пропустить", callback_data=f"skip_{task_id}")]
    ])

def admin_kb(is_superadmin=False):
    kb = [
        [InlineKeyboardButton(text="📝 Модерация рекламы", callback_data="admin_ads")],
        [InlineKeyboardButton(text="🎁 Заявки на выплату", callback_data="admin_withdrawals")],
        [InlineKeyboardButton(text="🎟 Управление чеками", callback_data="admin_checks")],
        [InlineKeyboardButton(text="📜 Все команды", callback_data="admin_all_commands")]
    ]
    if is_superadmin:
        kb.append([InlineKeyboardButton(text="👥 Управление админами", callback_data="admin_admins")])
    return InlineKeyboardMarkup(inline_keyboard=kb)
