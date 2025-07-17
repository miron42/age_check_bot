import os
import aiosqlite
from config import DB_PATH


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS confirmed_users (
                user_id INTEGER PRIMARY KEY,
                confirmed_at TEXT
            );
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS ads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT,
                image_path TEXT
            );
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY
            );
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS preview (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                text TEXT,
                image_path TEXT
            );
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_broadcasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT,
                image_path TEXT,
                send_at TEXT
            );
        """)

        await db.commit()


# --- Подтверждённые пользователи ---
async def add_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO confirmed_users (user_id, confirmed_at) VALUES (?, datetime('now'))",
            (user_id,)
        )
        await db.commit()


async def is_user_confirmed(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM confirmed_users WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone() is not None


async def get_confirmed_users() -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM confirmed_users") as cursor:
            return [row[0] for row in await cursor.fetchall()]


# --- Реклама ---
async def add_ad(text: str, image_path: str | None = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO ads (text, image_path) VALUES (?, ?)",
            (text, image_path)
        )
        await db.commit()


async def get_ad(ad_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, text, image_path FROM ads WHERE id = ?", (ad_id,)) as cursor:
            return await cursor.fetchone()


async def get_all_ads():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, text FROM ads ORDER BY id") as cursor:
            return await cursor.fetchall()


async def get_latest_ad():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, text, image_path FROM ads ORDER BY id DESC LIMIT 1") as cursor:
            return await cursor.fetchone()


async def add_ad_get_id(text: str, image_path: str | None = None) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO ads (text, image_path) VALUES (?, ?)",
            (text, image_path)
        )
        await db.commit()
        return cursor.lastrowid


async def remove_ad(ad_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM ads WHERE id = ?", (ad_id,))
        await db.commit()


# --- Админы ---
async def is_admin(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone() is not None


async def add_admin(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (user_id,))
        await db.commit()


async def remove_admin(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
        await db.commit()


async def get_admins() -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM admins") as cursor:
            return [row[0] for row in await cursor.fetchall()]


# --- Превью ---
async def get_preview():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT text, image_path FROM preview WHERE id = 1") as cursor:
            return await cursor.fetchone()


async def set_preview(text: str, image_path: str | None = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "REPLACE INTO preview (id, text, image_path) VALUES (1, ?, ?)",
            (text, image_path)
        )
        await db.commit()


# --- Отложенные рассылки ---
async def add_scheduled_broadcast(text: str, image_path: str | None, send_at: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO scheduled_broadcasts (text, image_path, send_at) VALUES (?, ?, ?)",
            (text, image_path, send_at)
        )
        await db.commit()


async def get_scheduled_broadcasts():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, text, image_path, send_at FROM scheduled_broadcasts ORDER BY send_at") as cursor:
            return await cursor.fetchall()


async def remove_scheduled_broadcast(broadcast_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM scheduled_broadcasts WHERE id = ?", (broadcast_id,))
        await db.commit()


async def remove_all_scheduled_broadcasts():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM scheduled_broadcasts")
        await db.commit()
