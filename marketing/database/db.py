import aiosqlite

DB_PATH = "data/database.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS accounts(
            id INTEGER PRIMARY KEY,
            phone TEXT UNIQUE,
            status TEXT
        )""")

        await db.execute("""
        CREATE TABLE IF NOT EXISTS customers(
            id INTEGER PRIMARY KEY,
            telegram_id TEXT UNIQUE,
            contacted INTEGER DEFAULT 0
        )""")

        await db.execute("""
        CREATE TABLE IF NOT EXISTS ads(
            id INTEGER PRIMARY KEY,
            type TEXT,
            content TEXT
        )""")

        await db.execute("""
        CREATE TABLE IF NOT EXISTS dm_log(
            id INTEGER PRIMARY KEY,
            phone TEXT,
            telegram_id TEXT,
            date TEXT
        )""")

        await db.commit()
