import sqlite3
from datetime import datetime

conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()


def init_db():
    # ---------------- USERS ----------------
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

    # ---------------- TASKS ----------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_id INTEGER,
        channel TEXT,
        reward REAL DEFAULT 0.50,
        total_subs INTEGER,
        left_subs INTEGER,
        active INTEGER DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ---------------- AD ORDERS (MODERATION) ----------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ad_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        channel TEXT,
        subs_count INTEGER,
        status TEXT DEFAULT 'pending',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ---------------- COMPLETED TASKS ----------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS completed (
        user_id INTEGER,
        task_id INTEGER,
        date DATETIME DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user_id, task_id)
    )
    """)

    # ---------------- WITHDRAWS ----------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS withdraws (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL,
        status TEXT DEFAULT 'pending',
        date DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ---------------- ADMINS ----------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admins (
        user_id INTEGER PRIMARY KEY,
        role TEXT DEFAULT 'moderator'
    )
    """)

    # ---------------- CHECKS ----------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS checks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        total_stars REAL,
        activations_count INTEGER,
        reward_per_user REAL DEFAULT 0.25,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ---------------- CHECK ACTIVATIONS ----------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS check_activations (
        check_id INTEGER,
        user_id INTEGER,
        date DATETIME DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (check_id, user_id)
    )
    """)

    conn.commit()


# ---------------- USER ----------------
def add_user(user_id, username=None, ref_id=None):
    cursor.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    exists = cursor.fetchone()

    if not exists:
        cursor.execute(
            "INSERT INTO users (user_id, username, ref_id) VALUES (?, ?, ?)",
            (user_id, username, ref_id)
        )
        conn.commit()

        if ref_id:
            pay_referral(user_id)

    else:
        if username:
            cursor.execute("UPDATE users SET username=? WHERE user_id=?", (username, user_id))
            conn.commit()


# ---------------- BALANCE ----------------
def add_balance(user_id, amount, balance_type="usual"):
    column = "balance_usual" if balance_type == "usual" else "balance_ads"
    cursor.execute(f"UPDATE users SET {column} = {column} + ? WHERE user_id=?", (amount, user_id))
    conn.commit()


# ---------------- REFERRAL ----------------
def pay_referral(user_id):
    cursor.execute("SELECT ref_id, ref_paid FROM users WHERE user_id=?", (user_id,))
    res = cursor.fetchone()

    if not res:
        return

    ref_id, paid = res
    if ref_id and paid == 0:
        cursor.execute("UPDATE users SET balance_usual = balance_usual + 2 WHERE user_id=?", (ref_id,))
        cursor.execute("UPDATE users SET ref_paid = 1 WHERE user_id=?", (user_id,))
        conn.commit()


init_db()
