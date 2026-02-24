import asyncio
from database.db import init_db
from admin_bot.bot import dp, bot

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
