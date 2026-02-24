import asyncio
import random
from database.models import get_ad

class Campaign:

    def __init__(self, manager):
        self.manager = manager

    async def broadcast(self, phone, groups):
        client = self.manager.running.get(phone)
        if not client:
            return

        ad_a = await get_ad("A")
        ad_b = await get_ad("B")

        for g in groups:
            try:
                await client.send_message(g, ad_a)
            except:
                await client.send_message(g, ad_b)

            await asyncio.sleep(random.randint(40,90))
