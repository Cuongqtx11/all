from telethon.tl.functions.contacts import SearchRequest
from telethon.tl.functions.channels import JoinChannelRequest
import asyncio
import random

class GroupScanner:

    async def find_join(self, client, keyword, limit=5):
        result = await client(SearchRequest(q=keyword, limit=limit))

        for chat in result.chats:
            try:
                await client(JoinChannelRequest(chat))
                await asyncio.sleep(random.randint(10,25))
            except:
                pass
