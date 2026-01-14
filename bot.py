from datetime import datetime, timedelta
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery, BotCommand
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from config import BOT_TOKEN, ADMIN_ID, LOG_CHANNELS
from db import *
from keyboards import *

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

class OrderAd(StatesGroup):
    channel = State()
    count = State()

class Deposit(StatesGroup):
    amount = State()

class AdminAdd(StatesGroup):
    user_info = State()

class CreateCheck(StatesGroup):
    total_stars = State()

def is_admin(user_id):
    if user_id == ADMIN_ID: return True
    cursor.execute("SELECT 1 FROM admins WHERE user_id=?", (user_id,))
    return cursor.fetchone() is not None

async def notify_admin(text, kb=None):
    for chat_id in LOG_CHANNELS:
        try:
            await bot.send_message(chat_id, text, reply_markup=kb, parse_mode="HTML")
        except Exception as e:
            print(f"Error sending to {chat_id}: {e}")

@dp.callback_query(F.data == "admin_all_commands")
async def admin_all_commands(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return
    text = (
        "📜 <b>Все команды администратора:</b>\n\n"
        "<code>/admin</code> — Открыть панель управления\n"
        "<code>/id</code> — Узнать ID текущего чата\n"
        "<code>/addstars</code> — Тестовое начисление 1000 ⭐ (только супер-админ)\n"
        "<code>/create_check</code> — Создать чек на звезды\n"
    )
    await cb.message.answer(text, parse_mode="HTML")
    await cb.answer()

@dp.message(Command("create_check"))
async def create_check_cmd(msg: Message, state: FSMContext):
    if not is_admin(msg.from_user.id): return
    await msg.answer("Введите общее количество звезд для чека:")
    await state.set_state(CreateCheck.total_stars)

@dp.message(CreateCheck.total_stars)
async def process_create_check(msg: Message, state: FSMContext):
    if not msg.text.replace('.', '', 1).isdigit():
        return await msg.answer("Введите число!")
    
    total = float(msg.text)
    reward_per_user = 0.25
    activations = int(total / reward_per_user)
    
    if activations < 1:
        return await msg.answer("Слишком маленькая сумма!")

    cursor.execute("INSERT INTO checks (total_stars, activations_count, reward_per_user) VALUES (?, ?, ?)", 
                   (total, activations, reward_per_user))
    check_id = cursor.lastrowid
    conn.commit()

    bot_info = await bot.get_me()
    check_link = f"https://t.me/{bot_info.username}?start=check_{check_id}"
    
    # Текст для канала новостей
    news_text = (
        f"🎁 <b>Чек на {int(total)} Звёзд!</b> ⭐\n\n"
        f"💰 <b>Награда:</b> по {reward_per_user} ⭐\n"
        f"👤 <b>Активаций:</b> {activations}\n"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"👉 ЗАБРАТЬ {reward_per_user} ⭐", url=check_link)]
    ])
    
    try:
        await bot.send_message("@starupbotnews", news_text, reply_markup=kb, parse_mode="HTML")
        await msg.answer(f"✅ Чек создан и отправлен в @starupbotnews\nID чека: {check_id}")
    except Exception as e:
        await msg.answer(f"✅ Чек создан (ID: {check_id}), но не удалось отправить в канал: {e}\nСсылка: {check_link}")
    
    await state.clear()

@dp.callback_query(F.data == "admin_checks")
async def admin_checks_menu(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return
    
    mk = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Создать чек", callback_data="admin_create_check_btn")],
        [InlineKeyboardButton(text="📊 Статистика чеков", callback_data="admin_checks_stats")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_admin")]
    ])
    
    await cb.message.edit_text("🎟 <b>Управление чеками</b>", reply_markup=mk, parse_mode="HTML")
    await cb.answer()

@dp.callback_query(F.data == "admin_create_check_btn")
async def admin_create_check_btn_handler(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id): return
    await cb.message.answer("Введите общее количество звезд для чека:")
    await state.set_state(CreateCheck.total_stars)
    await cb.answer()

@dp.callback_query(F.data == "admin_checks_stats")
async def admin_checks_stats_handler(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return
    cursor.execute("SELECT id, total_stars, activations_count FROM checks ORDER BY id DESC LIMIT 10")
    rows = cursor.fetchall()
    if not rows: return await cb.answer("Чеков пока нет")
    
    text = "📋 <b>Последние 10 чеков:</b>\n\n"
    for r in rows:
        cursor.execute("SELECT COUNT(*) FROM check_activations WHERE check_id=?", (r[0],))
        used = cursor.fetchone()[0]
        text += f"ID: {r[0]} | Сумма: {r[1]}⭐ | Активаций: {used}/{r[2]}\n"
    
    mk = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_checks")]
    ])
    
    await cb.message.edit_text(text, reply_markup=mk, parse_mode="HTML")
    await cb.answer()

@dp.callback_query(F.data == "back_to_admin")
async def back_to_admin_handler(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return
    await cb.message.edit_text("⚙️ Админ-панель", reply_markup=admin_kb(cb.from_user.id == ADMIN_ID))
    await cb.answer()

@dp.message(Command("create_check"))

@dp.message(F.text == "/id")
async def get_chat_id(msg: Message):
    await msg.answer(f"ID этого чата: <code>{msg.chat.id}</code>", parse_mode="HTML")

@dp.message(Command("admin"))
async def admin_panel_cmd(msg: Message):
    if not is_admin(msg.from_user.id): return
    await msg.answer("⚙️ Админ-панель", reply_markup=admin_kb(msg.from_user.id == ADMIN_ID))

@dp.message(CommandStart())
async def start(msg: Message):
    if msg.text and "admin" in msg.text:
        if is_admin(msg.from_user.id):
            await msg.answer("⚙️ Админ-панель", reply_markup=admin_kb(msg.from_user.id == ADMIN_ID))
            return
        else:
            await msg.answer("❌ У вас нет прав администратора.")
            return

    # Обработка чека
    if msg.text and "check_" in msg.text:
        try:
            check_id = int(msg.text.split("check_")[1])
            cursor.execute("SELECT total_stars, activations_count, reward_per_user FROM checks WHERE id=?", (check_id,))
            check = cursor.fetchone()
            if not check:
                return await msg.answer("😔 Чек не найден.")
            
            total, max_acts, reward = check
            
            # Проверка на повторную активацию
            cursor.execute("SELECT 1 FROM check_activations WHERE check_id=? AND user_id=?", (check_id, msg.from_user.id))
            if cursor.fetchone():
                return await msg.answer("❗️ Вы уже активировали этот чек.")
            
            # Проверка на лимит активаций
            cursor.execute("SELECT COUNT(*) FROM check_activations WHERE check_id=?", (check_id,))
            current_acts = cursor.fetchone()[0]
            if current_acts >= max_acts:
                return await msg.answer("😔 Этот чек уже активирован.")
            
            # Активация
            cursor.execute("INSERT INTO check_activations (check_id, user_id) VALUES (?, ?)", (check_id, msg.from_user.id))
            cursor.execute("UPDATE users SET balance_usual = balance_usual + ? WHERE user_id=?", (reward, msg.from_user.id))
            conn.commit()
            
            return await msg.answer(f"✅ Чек успешно активирован!\n\nНа ваш баланс начислено +{reward} ⭐")
        except Exception as e:
            print(f"Check activation error: {e}")
            return await msg.answer("❌ Произошла ошибка при активации чека.")

    username = msg.from_user.username
    add_user(msg.from_user.id, username, msg.text.split()[1] if len(msg.text.split()) > 1 else None)
    
    # 1. Анимация звездочки
    await msg.answer("⭐")
    
    # 2. Информация о рефералах
    user_id = msg.from_user.id
    cursor.execute("SELECT COUNT(*) FROM users WHERE ref_id=?", (user_id,))
    count = cursor.fetchone()[0]
    bot_info = await bot.get_me()
    ref_text = (
        f"Получайте +2 ⭐ за каждого приглашенного друга!\n\n"
        f"🔗 Ваша реферальная ссылка:\nhttps://t.me/{bot_info.username}?start={user_id}\n\n"
        f"🎉 Приглашайте по этой ссылке своих друзей, отправляйте её во все чаты и зарабатывайте Звёзды!\n\n"
        f"Приглашено вами: {count}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Отправить Ссылку Друзьям", switch_inline_query=f"start={user_id}")]
    ])
    await msg.answer(ref_text, reply_markup=kb, disable_web_page_preview=True)
    
    # Пауза
    await asyncio.sleep(2)
    
    # 3. Список заданий
    cursor.execute("SELECT * FROM tasks WHERE active=1 AND left_subs > 0")
    ts = cursor.fetchall()
    if not ts:
        await msg.answer("😔 К сожалению задания закончились, загляните позже!\n\nP.s Новые задания почти всегда доступны через 1 час.", reply_markup=main_menu())
    else:
        for t in ts:
            cursor.execute("SELECT 1 FROM completed WHERE user_id=? AND task_id=?", (msg.from_user.id, t[0]))
            if not cursor.fetchone():
                text = (
                    "💡 Получайте Звёзды за простые задания! 👇\n\n"
                    "🟢 Подпишитесь на канал и нажмите «Подтвердить»\n\n"
                    f"Вознаграждение: +0.50⭐"
                )
                await msg.answer(text, reply_markup=task_kb(t[0], t[1]))
        # Дополнительно отправим меню, если оно не отправилось выше
        await msg.answer("Главное меню:", reply_markup=main_menu())

async def show_main_stats(msg: Message):
    username = msg.from_user.username
    add_user(msg.from_user.id, username, msg.text.split()[1] if hasattr(msg, 'text') and msg.text and len(msg.text.split()) > 1 else None)
    cursor.execute("SELECT balance_usual, balance_ads FROM users WHERE user_id=?", (msg.from_user.id,))
    res = cursor.fetchone()
    if not res:
        add_user(msg.from_user.id, username)
        b_usual, b_ads = (0, 0)
    else:
        b_usual, b_ads = res
    
    cursor.execute("SELECT SUM(amount) FROM withdraws WHERE user_id=? AND status='pending'", (msg.from_user.id,))
    waiting = cursor.fetchone()[0] or 0
    cursor.execute("SELECT SUM(amount) FROM withdraws WHERE user_id=? AND status='approved'", (msg.from_user.id,))
    withdrawn = cursor.fetchone()[0] or 0
    
    text = (
        f"🖥 <b>Мой Кабинет</b>\n\n"
        f"<b>Баланс</b>\n"
        f"Обычный: {b_usual} ⭐\n"
        f"Рекламный: {b_ads} ⭐\n\n"
        f"<b>Выводы</b>\n"
        f"Ожидают: {waiting} ⭐\n"
        f"Выведено: {withdrawn} ⭐\n\n"
        f"❗ Звёзды <b>выводятся</b> с обычного баланса.\n\n"
        f"👥 Хочешь подписчиков в свой Канал? Жми «Создать Задание» и обменивай звёзды на подписчиков!"
    )
    await msg.answer(text, reply_markup=main_menu(), parse_mode="HTML")

@dp.message(Command("cabinet"))
async def cabinet_cmd(msg: Message):
    await buy_subs_cabinet(msg)

@dp.message(Command("addstars"))
async def add_stars_cmd(msg: Message):
    if msg.from_user.id != ADMIN_ID: return
    add_balance(msg.from_user.id, 1000, "usual")
    add_balance(msg.from_user.id, 1000, "ads")
    await msg.answer("🎁 Вам начислено 1000 ⭐ на основной и 1000 ⭐ на рекламный баланс для тестирования!")
@dp.message(F.text == "👥 Купить Подписчиков")
async def buy_subs_cabinet(msg: Message):
    cursor.execute("SELECT balance_usual, balance_ads FROM users WHERE user_id=?", (msg.from_user.id,))
    res = cursor.fetchone()
    if not res:
        add_user(msg.from_user.id, msg.from_user.username)
        b_usual, b_ads = (0, 0)
    else:
        b_usual, b_ads = res
    
    cursor.execute("SELECT SUM(amount) FROM withdraws WHERE user_id=? AND status='pending'", (msg.from_user.id,))
    waiting = cursor.fetchone()[0] or 0
    cursor.execute("SELECT SUM(amount) FROM withdraws WHERE user_id=? AND status='approved'", (msg.from_user.id,))
    withdrawn = cursor.fetchone()[0] or 0
    
    text = (
        f"🖥 <b>Мой Кабинет</b>\n\n"
        f"<b>Баланс</b>\n"
        f"Обычный: {b_usual} ⭐\n"
        f"Рекламный: {b_ads} ⭐\n\n"
        f"<b>Выводы</b>\n"
        f"Ожидают: {waiting} ⭐\n"
        f"Выведено: {withdrawn} ⭐\n\n"
        f"❗ Звёзды <b>выводятся</b> с обычного баланса.\n\n"
        f"👥 Хочешь подписчиков в свой Канал? Жми «Создать Задание» и обменивай звёзды на подписчиков!"
    )
    await msg.answer(text, reply_markup=tasks_cabinet_kb(), parse_mode="HTML")

@dp.message(F.text == "💎 Задания")
async def tasks_list(msg: Message):
    cursor.execute("SELECT * FROM tasks WHERE active=1 AND left_subs > 0")
    ts = cursor.fetchall()
    found_any = False
    
    if ts:
        for t in ts:
            cursor.execute("SELECT 1 FROM completed WHERE user_id=? AND task_id=?", (msg.from_user.id, t[0]))
            if not cursor.fetchone():
                text = (
                    "💡 Получайте Звёзды за простые задания! 👇\n\n"
                    "🟢 Подпишитесь на канал и нажмите «Подтвердить»\n\n"
                    "Вознаграждение: +0.50⭐\n\n"
                    "❗ <b>Внимание:</b> Запрещено отписываться от каналов в течение 3-х дней. За нарушение — списание звезд и бан."
                )
                await msg.answer(text, reply_markup=task_kb(t[0], t[1]), parse_mode="HTML")
                found_any = True
                break # Show one task at a time to match skip/confirm logic

    if not found_any:
        await msg.answer("😔 К сожалению задания закончились, загляните позже!\n\nP.s Новые задания почти всегда доступны через 1 час.", reply_markup=main_menu())

@dp.message(F.text == "⭐ Заработать Звёзды")
async def earn_stars(msg: Message):
    # This button should also show tasks according to StarsovGamesBot logic (earn stars = tasks)
    await tasks_list(msg)

@dp.message(F.text == "🎁 Вывести Звёзды")
async def withdraw_gifts(msg: Message):
    cursor.execute("SELECT balance_usual FROM users WHERE user_id=?", (msg.from_user.id,))
    res = cursor.fetchone()
    if not res:
        add_user(msg.from_user.id, msg.from_user.username)
        bal = 0
    else:
        bal = res[0]
    await msg.answer(f"Заработано: {bal} ⭐\n\nВыберите сумму для вывода\n\nКанал с выводами: @starupbotout", reply_markup=withdraw_gifts_kb())

@dp.callback_query(F.data == "deposit_stars_menu")
async def deposit_menu(cb: CallbackQuery, state: FSMContext):
    await cb.message.answer("Введите сумму для пополнения:\n\nМинимум: 50 ⭐\n\nОтменить — /cancel")
    await state.set_state(Deposit.amount)
    await cb.answer()

@dp.message(Deposit.amount)
async def deposit_amount(msg: Message, state: FSMContext):
    if not msg.text.isdigit(): return await msg.answer("Введите число!")
    amount = int(msg.text)
    if amount < 50: return await msg.answer("Минимальная сумма пополнения: 50 ⭐")
    await state.update_data(amount=amount)
    await msg.answer(f"💳 <b>Выберите способ пополнения:</b>\n\nСумма: {amount} ⭐\n\nОтменить — /cancel", 
                     reply_markup=deposit_methods_kb(amount), parse_mode="HTML")

@dp.callback_query(F.data.startswith("dep_usual_"))
async def deposit_usual(cb: CallbackQuery, state: FSMContext):
    amount = int(cb.data.split("_")[2])
    cursor.execute("SELECT balance_usual FROM users WHERE user_id=?", (cb.from_user.id,))
    res = cursor.fetchone()
    if not res:
        add_user(cb.from_user.id, cb.from_user.username)
        usual = 0
    else:
        usual = res[0]
        
    if usual < amount:
        return await cb.answer(f"❌ Недостаточно звезд на обычном балансе (у вас {usual})!", show_alert=True)
    
    cursor.execute("UPDATE users SET balance_usual = balance_usual - ?, balance_ads = balance_ads + ? WHERE user_id = ?", (amount, amount, cb.from_user.id))
    conn.commit()
    await cb.message.answer(f"✅ Переведено {amount} ⭐ на рекламный баланс!")
    
    user_info = f"👤 {cb.from_user.id}"
    if cb.from_user.username: user_info += f" (@{cb.from_user.username})"
    
    try:
        for chat_id in LOG_CHANNELS:
            await bot.send_message(
                chat_id,
                f"💰 <b>Перевод с баланса!</b>\n{user_info}\n⭐ {amount}",
                parse_mode="HTML"
            )
    except Exception as e:
        print(f"Error sending to LOG_CHANNELS: {e}")

    await state.clear()
    await cb.answer()

@dp.callback_query(F.data.startswith("dep_stars_"))
async def deposit_stars_invoice(cb: CallbackQuery, state: FSMContext):
    amount = int(cb.data.split("_")[2])
    await cb.message.answer_invoice(
        title="Пополнение рекламного баланса",
        description=f"Пополнение на {amount} звезд",
        prices=[LabeledPrice(label="XTR", amount=amount)],
        provider_token="", payload=f"dep_ads_{amount}", currency="XTR"
    )
    await state.clear()
    await cb.answer()

@dp.callback_query(F.data == "create_task")
async def create_task_start(cb: CallbackQuery, state: FSMContext):
    await cb.message.answer("Введите ссылку на канал (с @):")
    await state.set_state(OrderAd.channel)
    await cb.answer()

@dp.message(OrderAd.channel)
async def ad_channel(msg: Message, state: FSMContext):
    channel = msg.text
    if not (channel.startswith("@") or channel.startswith("https://t.me/")):
        return await msg.answer("❌ Введите корректную ссылку!")
    try:
        chat = await bot.get_chat(channel)
        member = await bot.get_chat_member(chat.id, (await bot.get_me()).id)
        if member.status not in ["administrator", "creator"]:
            return await msg.answer("❌ Бот должен быть администратором в канале!")
    except: return await msg.answer("❌ Бот не может найти канал!")
    await state.update_data(channel=channel)
    await msg.answer("Введите количество подписчиков (1 подписка = 1 звезда):")
    await state.set_state(OrderAd.count)

@dp.message(OrderAd.count)
async def ad_finish(msg: Message, state: FSMContext):
    if not msg.text.isdigit(): return await msg.answer("Введите число!")
    count = int(msg.text)
    cursor.execute("SELECT balance_ads FROM users WHERE user_id=?", (msg.from_user.id,))
    if cursor.fetchone()[0] < count: return await msg.answer("❌ Недостаточно рекламного баланса!")
    data = await state.get_data()
    cursor.execute("UPDATE users SET balance_ads = balance_ads - ? WHERE user_id = ?", (count, msg.from_user.id))
    cursor.execute("INSERT INTO ad_orders (user_id, channel, subs_count) VALUES (?,?,?)", (msg.from_user.id, data['channel'], count))
    conn.commit()
    
    user_info = f"👤 {msg.from_user.id}"
    if msg.from_user.username: user_info += f" (@{msg.from_user.username})"
    
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Написать клиенту", url=f"tg://user?id={msg.from_user.id}")],
        [InlineKeyboardButton(text="⚙️ Админ-панель", url=f"https://t.me/{(await bot.get_me()).username}?start=admin")]
    ])
    
    # Отправляем уведомление ТОЛЬКО в канал логов
    try:
        for chat_id in LOG_CHANNELS:
            await bot.send_message(
                chat_id,
                f"📢 <b>Новая заявка на рекламу!</b>\n"
                f"Клиент: {user_info}\n"
                f"🔗 Канал: {data['channel']}\n"
                f"👥 Кол-во: {count}",
                reply_markup=admin_kb,
                parse_mode="HTML"
            )
    except Exception as e:
        print(f"Error sending to LOG_CHANNELS: {e}")

    await msg.answer("✅ Заявка отправлена на модерацию!")
    await state.clear()

@dp.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)

@dp.message(F.successful_payment)
async def success_payment(msg: Message):
    amount = msg.successful_payment.total_amount
    add_balance(msg.from_user.id, amount, "ads")
    await msg.answer(f"✅ Рекламный баланс пополнен на {amount} ⭐!")
    
    user_info = f"👤 {msg.from_user.id}"
    if msg.from_user.username: user_info += f" (@{msg.from_user.username})"
    
    try:
        for chat_id in LOG_CHANNELS:
            await bot.send_message(
                chat_id,
                f"💰 <b>Пополнение Stars!</b>\n{user_info}\n⭐ {amount}",
                parse_mode="HTML"
            )
    except Exception as e:
        print(f"Error sending to LOG_CHANNELS: {e}")

@dp.callback_query(F.data.startswith("wd_"))
async def wd_request(cb: CallbackQuery):
    amount = int(cb.data.split("_")[1])
    cursor.execute("SELECT balance_usual FROM users WHERE user_id=?", (cb.from_user.id,))
    if cursor.fetchone()[0] < amount: return await cb.answer("❌ Недостаточно звёзд!", show_alert=True)
    cursor.execute("UPDATE users SET balance_usual = balance_usual - ? WHERE user_id = ?", (amount, cb.from_user.id))
    cursor.execute("INSERT INTO withdraws (user_id, amount) VALUES (?,?)", (cb.from_user.id, amount))
    conn.commit()
    
    # Уведомление в канал @starupbotout
    username_text = f"@{cb.from_user.username}" if cb.from_user.username else f"ID: {cb.from_user.id}"
    public_text = (
        f"⌛️ Создана заявка на вывод!\n\n"
        f"👤 Пользователь: {username_text}\n"
        f"⭐️ Количество звезд: {amount}\n\n"
        f"👉 @starupb_bot"
    )
    try:
        await bot.send_message("@starupbotout", public_text)
    except Exception as e:
        print(f"Error sending to channel: {e}")

    await notify_admin(f"🎁 Новая заявка на вывод!\n👤 {cb.from_user.id}\n⭐ Сумма: {amount}")
    await cb.message.answer("✅ Заявка на вывод создана!")
    await cb.answer()

@dp.callback_query(F.data == "admin_withdrawals")
async def admin_wd_list(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return
    cursor.execute("SELECT * FROM withdraws WHERE status='pending'")
    rows = cursor.fetchall()
    if not rows: return await cb.answer("Нет заявок")
    for r in rows:
        mk = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"wdapp_{r[0]}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"wdrej_{r[0]}")
        ]])
        await cb.message.answer(f"🎁 Заявка #{r[0]}\n👤 Юзер: {r[1]}\n⭐ Сумма: {r[2]}", reply_markup=mk)
    await cb.answer()

@dp.callback_query(F.data.startswith("wdapp_"))
async def wd_approve(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return
    wid = int(cb.data.split("_")[1])
    cursor.execute("SELECT user_id, amount FROM withdraws WHERE id=?", (wid,))
    row = cursor.fetchone()
    if not row: return await cb.answer("Заявка не найдена")
    
    user_id, amount = row
    cursor.execute("UPDATE withdraws SET status='approved' WHERE id=?", (wid,))
    conn.commit()
    
    # Уведомление в канал @starupbotout
    cursor.execute("SELECT username FROM users WHERE user_id=?", (user_id,))
    u_res = cursor.fetchone()
    username_text = f"@{u_res[0]}" if u_res and u_res[0] else f"ID: {user_id}"
    
    public_text = (
        f"✅ Отправлена выплата!!\n\n"
        f"👤 Пользователь: {username_text}\n\n"
        f"👉 @starupb_bot"
    )
    try:
        await bot.send_message("@starupbotout", public_text)
    except Exception as e:
        print(f"Error sending approval to channel: {e}")

    await cb.message.edit_text("✅ Одобрено! Вышлите подарок.")
    await cb.answer()

@dp.callback_query(F.data == "admin_ads")
async def admin_ads_list(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return
    cursor.execute("SELECT * FROM ad_orders")
    rows = cursor.fetchall()
    if not rows: return await cb.answer("Нет заявок на модерацию", show_alert=True)
    for r in rows:
        mk = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"adapp_{r[0]}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"adrej_{r[0]}")
        ]])
        await cb.message.answer(f"📢 Реклама #{r[0]}\n👤 Юзер: {r[1]}\n🔗 Канал: {r[2]}\n👥 Подписчиков: {r[3]}", reply_markup=mk)
    await cb.answer()

@dp.callback_query(F.data.startswith("skip_"))
async def skip_task(cb: CallbackQuery):
    tid = int(cb.data.split("_")[1])
    # Добавляем в выполненные, чтобы не показывать больше, но без награды
    cursor.execute("INSERT INTO completed (user_id, task_id, date) VALUES (?,?,?)", 
                   (cb.from_user.id, tid, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    
    # Удаляем текущее сообщение с заданием
    try:
        await cb.message.delete()
    except Exception as e:
        print(f"Error deleting message: {e}")
    
    # Сразу после нажатия "Пропустить" ищем и показываем следующее доступное задание
    cursor.execute("SELECT * FROM tasks WHERE active=1 AND left_subs > 0")
    ts = cursor.fetchall()
    found_next = False
    
    for t in ts:
        # Проверяем, не выполнял ли (или не пропускал ли) пользователь это задание
        cursor.execute("SELECT 1 FROM completed WHERE user_id=? AND task_id=?", (cb.from_user.id, t[0]))
        if not cursor.fetchone():
            text = (
                "💡 Получайте Звёзды за простые задания! 👇\n\n"
                "🟢 Подпишитесь на канал и нажмите «Подтвердить»\n\n"
                "Вознаграждение: +0.50⭐\n\n"
                "❗ <b>Внимание:</b> Запрещено отписываться от каналов в течение 3-х дней. За нарушение — списание звезд и бан."
            )
            try:
                # Используем bot.send_message напрямую для надежности
                await bot.send_message(cb.from_user.id, text, reply_markup=task_kb(t[0], t[1]), parse_mode="HTML")
                found_next = True
            except Exception as e:
                print(f"Error sending next task: {e}")
            break
            
    if not found_next:
        try:
            # Если заданий больше нет, уведомляем пользователя
            await bot.send_message(cb.from_user.id, "😔 К сожалению задания закончились, загляните позже!\n\nP.s Новые задания почти всегда доступны через 1 час.", reply_markup=main_menu())
        except Exception as e:
            print(f"Error sending out of tasks message: {e}")
    
    # Всегда отвечаем на колбэк, чтобы убрать часы с кнопки
    await cb.answer("Задание пропущено")

@dp.callback_query(F.data.startswith("check_"))
async def check_sub(cb: CallbackQuery):
    tid = int(cb.data.split("_")[1])
    cursor.execute("SELECT channel, reward FROM tasks WHERE id=?", (tid,))
    task = cursor.fetchone()
    if not task: return await cb.answer("Задание не найдено")
    
    reward = 0.50
    
    try:
        member = await bot.get_chat_member(task[0], cb.from_user.id)
        if member.status in ["member", "administrator", "creator"]:
            cursor.execute("SELECT 1 FROM completed WHERE user_id=? AND task_id=?", (cb.from_user.id, tid))
            if cursor.fetchone(): return await cb.answer("Вы уже получили награду!", show_alert=True)
            
            # Записываем выполнение с текущей датой
            cursor.execute("INSERT INTO completed (user_id, task_id, date) VALUES (?,?,?)", 
                           (cb.from_user.id, tid, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            cursor.execute("UPDATE users SET balance_usual = balance_usual + ? WHERE user_id=?", (reward, cb.from_user.id))
            cursor.execute("UPDATE tasks SET left_subs = left_subs - 1 WHERE id=?", (tid,))
            conn.commit()
            await cb.message.delete()
            await bot.send_message(cb.from_user.id, f"✅ Награда {reward} ⭐ зачислена!")

            # После успешного выполнения показываем следующее задание
            cursor.execute("SELECT * FROM tasks WHERE active=1 AND left_subs > 0")
            ts = cursor.fetchall()
            found_next = False
            for t in ts:
                cursor.execute("SELECT 1 FROM completed WHERE user_id=? AND task_id=?", (cb.from_user.id, t[0]))
                if not cursor.fetchone():
                    text = (
                        "💡 Получайте Звёзды за простые задания! 👇\n\n"
                        "🟢 Подпишитесь на канал и нажмите «Подтвердить»\n\n"
                        "Вознаграждение: +0.50⭐"
                    )
                    await bot.send_message(cb.from_user.id, text, reply_markup=task_kb(t[0], t[1]))
                    found_next = True
                    break
        else:
            await cb.answer("❌ Вы не подписались на канал!", show_alert=True)
    except:
        await cb.answer("❌ Ошибка проверки подписки. Убедитесь, что бот есть в канале.", show_alert=True)
    await cb.answer()

@dp.callback_query(F.data.startswith("adapp_"))
async def ad_approve(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return
    aid = int(cb.data.split("_")[1])
    cursor.execute("SELECT * FROM ad_orders WHERE id=?", (aid,))
    order = cursor.fetchone()
    if order:
        # Устанавливаем награду 0.50 при создании задания из заявки
        cursor.execute("INSERT INTO tasks (channel, reward, total_subs, left_subs, active) VALUES (?, 0.50, ?, ?, 1)", (order[2], order[3], order[3]))
        cursor.execute("DELETE FROM ad_orders WHERE id=?", (aid,))
        conn.commit()
        await cb.message.edit_text(f"✅ Реклама {order[2]} одобрена и запущена!")
    await cb.answer()

@dp.callback_query(F.data.startswith("adrej_"))
async def ad_reject(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return
    aid = int(cb.data.split("_")[1])
    cursor.execute("SELECT user_id, subs_count FROM ad_orders WHERE id=?", (aid,))
    order = cursor.fetchone()
    if order:
        cursor.execute("UPDATE users SET balance_ads = balance_ads + ? WHERE user_id = ?", (order[1], order[0]))
        cursor.execute("DELETE FROM ad_orders WHERE id=?", (aid,))
        conn.commit()
        await cb.message.edit_text("❌ Реклама отклонена, звезды вернулись на баланс.")
    await cb.answer()

@dp.callback_query(F.data.startswith("wdrej_"))
async def wd_reject(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return
    wid = int(cb.data.split("_")[1])
    cursor.execute("SELECT user_id, amount FROM withdraws WHERE id=?", (wid,))
    row = cursor.fetchone()
    if row:
        cursor.execute("UPDATE users SET balance_usual = balance_usual + ? WHERE user_id = ?", (row[1], row[0]))
        cursor.execute("DELETE FROM withdraws WHERE id=?", (wid,))
        conn.commit()
        await cb.message.edit_text("❌ Выплата отклонена, звезды вернулись на баланс.")
    await cb.answer()

@dp.callback_query(F.data == "admin_admins")
async def admin_manage(cb: CallbackQuery, state: FSMContext):
    if cb.from_user.id != ADMIN_ID: return
    cursor.execute("SELECT user_id FROM admins")
    rows = cursor.fetchall()
    text = "👥 <b>Список администраторов:</b>\n\n"
    if not rows:
        text += "Список пуст"
    else:
        for r in rows:
            cursor.execute("SELECT username FROM users WHERE user_id=?", (r[0],))
            user_res = cursor.fetchone()
            username = user_res[0] if user_res else "unknown"
            text += f"• <code>{r[0]}</code> (@{username})\n"
    
    mk = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить админа", callback_data="add_new_admin")]
    ])
    await cb.message.edit_text(text, reply_markup=mk, parse_mode="HTML")
    await cb.answer()

@dp.callback_query(F.data == "my_tasks")
async def my_tasks_list(cb: CallbackQuery):
    try:
        cursor.execute("SELECT id, channel, subs_count FROM ad_orders WHERE user_id=?", (cb.from_user.id,))
        orders = cursor.fetchall()
        
        cursor.execute("SELECT id, channel, total_subs, left_subs FROM tasks WHERE channel IN (SELECT channel FROM ad_orders WHERE user_id=?)", (cb.from_user.id,))
        active_tasks = cursor.fetchall()

        text = "📋 <b>Мои задания:</b>\n\n"
        
        if not orders and not active_tasks:
            text += "У вас пока нет созданных заданий."
        else:
            if orders:
                text += "<b>На модерации:</b>\n"
                for o in orders:
                    text += f"• {o[1]} ({o[2]} подп.)\n"
                text += "\n"
            
            if active_tasks:
                text += "<b>Активные:</b>\n"
                for t in active_tasks:
                    text += f"• {t[1]}: осталось {t[3]} из {t[2]}\n"

        await cb.message.answer(text, parse_mode="HTML")
    except Exception as e:
        print(f"Error in my_tasks_list: {e}")
        await cb.message.answer("❌ Произошла ошибка при загрузке заданий.")
    await cb.answer()

@dp.callback_query(F.data == "ad_instruction")
async def ad_instruction_handler(cb: CallbackQuery):
    text = (
        "📖 <b>Инструкция по рекламе</b>\n\n"
        "<b>Как запустить рекламу?</b>\n"
        "1. Пополните рекламный баланс через Telegram Stars или переводом с основного баланса.\n"
        "2. Нажмите «Создать Задание» и отправьте ссылку на ваш канал (с @).\n"
        "3. <b>Важно:</b> Бот должен быть администратором в вашем канале, чтобы проверять подписки.\n"
        "4. Укажите количество нужных подписчиков (1 подписка = 1 звезда).\n"
        "5. После модерации (обычно до 1 часа) задание станет доступно пользователям.\n\n"
        "<b>Правила и запреты:</b>\n"
        "❌ Запрещены каналы с шок-контентом, насилием, порнографией.\n"
        "❌ Запрещена реклама наркотических веществ и скам-проектов.\n"
        "❌ Запрещены каналы, нарушающие законы или правила Telegram.\n"
        "✅ Разрешены блоги, игровые каналы, новости, магазины и другие полезные ресурсы.\n\n"
        "💡 <i>Все заявки проверяются модераторами вручную.</i>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Купить Звёзды", callback_data="deposit_stars_menu")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_cabinet")]
    ])
    await cb.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await cb.answer()

@dp.callback_query(F.data == "back_to_cabinet")
async def back_to_cabinet_handler(cb: CallbackQuery):
    # Повторяем логику buy_subs_cabinet, но с edit_text
    cursor.execute("SELECT balance_usual, balance_ads FROM users WHERE user_id=?", (cb.from_user.id,))
    res = cursor.fetchone()
    b_usual, b_ads = res if res else (0, 0)
    
    cursor.execute("SELECT SUM(amount) FROM withdraws WHERE user_id=? AND status='pending'", (cb.from_user.id,))
    waiting = cursor.fetchone()[0] or 0
    cursor.execute("SELECT SUM(amount) FROM withdraws WHERE user_id=? AND status='approved'", (cb.from_user.id,))
    withdrawn = cursor.fetchone()[0] or 0
    
    text = (
        f"🖥 <b>Мой Кабинет</b>\n\n"
        f"<b>Баланс</b>\n"
        f"Обычный: {b_usual} ⭐\n"
        f"Рекламный: {b_ads} ⭐\n\n"
        f"<b>Выводы</b>\n"
        f"Ожидают: {waiting} ⭐\n"
        f"Выведено: {withdrawn} ⭐\n\n"
        f"❗ Звёзды <b>выводятся</b> с обычного баланса.\n\n"
        f"👥 Хочешь подписчиков в свой Канал? Жми «Создать Задание» и обменивай звёзды на подписчиков!"
    )
    await cb.message.edit_text(text, reply_markup=tasks_cabinet_kb(), parse_mode="HTML")
    await cb.answer()

@dp.callback_query(F.data == "add_new_admin")
async def add_admin_start(cb: CallbackQuery, state: FSMContext):
    await cb.message.answer("Введите ID пользователя или его @username для добавления в админы:\n\nОтменить — /cancel")
    await state.set_state(AdminAdd.user_info)
    await cb.answer()

@dp.message(AdminAdd.user_info)
async def process_add_admin(msg: Message, state: FSMContext):
    user_info = msg.text.strip().replace("@", "")
    target_id = None
    if user_info.isdigit():
        target_id = int(user_info)
    else:
        cursor.execute("SELECT user_id FROM users WHERE username=?", (user_info,))
        row = cursor.fetchone()
        if row: target_id = row[0]
        else: return await msg.answer("❌ Пользователь не найден в базе бота.")
    
    cursor.execute("INSERT OR REPLACE INTO admins (user_id) VALUES (?)", (target_id,))
    conn.commit()
    await msg.answer(f"✅ Пользователь {target_id} теперь администратор!")
    await state.clear()

async def main():
    await bot.delete_my_commands()
    await bot.set_my_commands([
        BotCommand(command="start", description="Меню"),
        BotCommand(command="cabinet", description="Кабинет")
    ])
    print("Commands set successfully")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
