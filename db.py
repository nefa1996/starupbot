import sqlite3
from datetime import datetime

conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

def init_db():
    # Пользователи: обычный и рекламный баланс
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        ref_id INTEGER,
        balance_usual REAL DEFAULT 0,
        balance_ads REAL DEFAULT 0,
        ref_paid INTEGER DEFAULT 0
    )
    """)

    # Задания (активные)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        channel TEXT,
        reward REAL DEFAULT 0.25,
        left_subs INTEGER,
        active INTEGER DEFAULT 0,
        owner_id INTEGER,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Пытаемся добавить колонку total_subs если её нет
    try:
        cursor.execute("ALTER TABLE tasks ADD COLUMN total_subs INTEGER DEFAULT 0")
    except:
        pass

    # Заявки на рекламу (модерация)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ad_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        channel TEXT,
        subs_count INTEGER,
        status TEXT DEFAULT 'pending'
    )
    """)

    # Выполненные задания
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS completed (
        user_id INTEGER,
        task_id INTEGER,
        date DATETIME DEFAULT CURRENT_TIMESTAMP,
        is_checked INTEGER DEFAULT 0
    )
    """)

    # Заявки на вывод (вывод подарков)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS withdraws (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL,
        status TEXT DEFAULT 'pending',
        date DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Администраторы
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admins (
        user_id INTEGER PRIMARY KEY,
        role TEXT DEFAULT 'moderator'
    )
    """)

    # Чеки
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS checks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        total_stars REAL,
        activations_count INTEGER,
        reward_per_user REAL DEFAULT 0.25,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Активации чеков
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS check_activations (
        check_id INTEGER,
        user_id INTEGER,
        date DATETIME DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (check_id, user_id)
    )
    """)

    conn.commit()

def add_user(user_id, username=None, ref_id=None):
    if username:
        cursor.execute("INSERT INTO users (user_id, username, ref_id) VALUES (?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET username=?", (user_id, username, ref_id, username))
    else:
        cursor.execute("INSERT OR IGNORE INTO users (user_id, ref_id) VALUES (?, ?)", (user_id, ref_id))
    if ref_id:
        pay_referral(user_id)
    conn.commit()

def add_balance(user_id, amount, balance_type="usual"):
    column = "balance_usual" if balance_type == "usual" else "balance_ads"
    cursor.execute(f"UPDATE users SET {column} = {column} + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()

def pay_referral(user_id):
    cursor.execute("SELECT ref_id, ref_paid FROM users WHERE user_id=?", (user_id,))
    res = cursor.fetchone()
    if res:
        ref_id, paid = res
        if ref_id and paid == 0:
            cursor.execute("UPDATE users SET balance_usual = balance_usual + 2.0 WHERE user_id=?", (ref_id,))
            cursor.execute("UPDATE users SET ref_paid = 1 WHERE user_id=?", (user_id,))
            conn.commit()

init_db()
