import aiosqlite
from datetime import datetime
from database.db import DB_PATH

async def add_account(phone, status="stopped"):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO accounts (phone, status) VALUES (?,?)",
            (phone, status)
        )
        await db.commit()

async def update_status(phone, status):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE accounts SET status=? WHERE phone=?",
            (status, phone)
        )
        await db.commit()

async def set_ad(ad_type, content):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM ads WHERE type=?", (ad_type,))
        await db.execute(
            "INSERT INTO ads (type, content) VALUES (?,?)",
            (ad_type, content)
        )
        await db.commit()

async def get_ad(ad_type):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT content FROM ads WHERE type=?",
            (ad_type,)
        )
        row = await cur.fetchone()
        return row[0] if row else None

async def log_dm(phone, telegram_id):
    today = datetime.utcnow().date().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO dm_log (phone, telegram_id, date) VALUES (?,?,?)",
            (phone, telegram_id, today)
        )
        await db.commit()

async def count_today_dm(phone):
    today = datetime.utcnow().date().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT COUNT(*) FROM dm_log WHERE phone=? AND date=?",
            (phone, today)
        )
        row = await cur.fetchone()
        return row[0] if row else 0
