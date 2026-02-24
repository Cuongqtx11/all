import asyncio
from telethon import TelegramClient, events
from config import API_ID, API_HASH, MAX_DM_PER_DAY
from core.ai_agent import check_potential
from core.anti_ban import random_sleep
from database.models import count_today_dm, log_dm
from core.relay import Relay

class CloneManager:

    def __init__(self, bot):
        self.running = {}
        self.bot = bot
        self.relay = Relay(bot, self)

    async def start_clone(self, phone):
        client = TelegramClient(f"sessions/{phone}", API_ID, API_HASH)
        await client.start()

        self.running[phone] = client

        @client.on(events.NewMessage(incoming=True))
        async def private_handler(event):
            if event.is_private:
                await self.relay.forward(
                    phone,
                    event.sender_id,
                    event.raw_text
                )

        @client.on(events.NewMessage)
        async def group_monitor(event):
            if event.is_group:
                if await check_potential(event.raw_text):
                    if await count_today_dm(phone) < MAX_DM_PER_DAY:
                        await random_sleep()
                        await client.send_message(
                            event.sender_id,
                            "Chào bạn, mình hỗ trợ nhé!"
                        )
                        await log_dm(phone, event.sender_id)

        asyncio.create_task(client.run_until_disconnected())
