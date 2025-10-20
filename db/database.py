import sqlite3, time
from typing import Any, Dict, List
from pathlib import Path

DB_PATH = Path("idol_agency.db")

def db() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def now_ts() -> int:
    return int(time.time())

def init_db():
    con = db()
    cur = con.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        money REAL NOT NULL DEFAULT 0,
        last_tick INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS user_girls (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        rarity TEXT NOT NULL,
        level INTEGER NOT NULL DEFAULT 1,
        xp REAL NOT NULL DEFAULT 0,
        income REAL NOT NULL,
        popularity REAL NOT NULL,
        fans REAL NOT NULL DEFAULT 0,
        stamina REAL NOT NULL DEFAULT 100,
        is_working INTEGER NOT NULL DEFAULT 1,
        image_url TEXT,
        specialty TEXT,
        UNIQUE(user_id, name),
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    );
    """)
    # migrations (ignore if already applied)
    try:
        cur.execute("ALTER TABLE user_girls ADD COLUMN specialty TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cur.execute("ALTER TABLE user_girls ADD COLUMN image_url TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cur.execute("ALTER TABLE user_girls ADD COLUMN level INTEGER NOT NULL DEFAULT 1")
    except sqlite3.OperationalError:
        pass
    try:
        cur.execute("ALTER TABLE user_girls ADD COLUMN xp REAL NOT NULL DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    con.commit()
    con.close()

def ensure_user(user_id: int):
    con = db()
    cur = con.cursor()
    cur.execute("SELECT 1 FROM users WHERE user_id=?", (user_id,))
    if not cur.fetchone():
        cur.execute("INSERT INTO users(user_id, money, last_tick) VALUES(?,?,?)", (user_id, 0, now_ts()))
        con.commit()
    con.close()
