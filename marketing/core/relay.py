from config import ADMIN_GROUP_ID


class Relay:

    def __init__(self, bot, clone_manager):
        self.bot = bot
        self.clone_manager = clone_manager

    async def forward(self, phone, user_id, text):
        await self.bot.send_message(
            ADMIN_GROUP_ID,
            f"[{phone}]|{user_id}\n{text}"
        )

    async def handle_reply(self, message):
        # Không phải reply → bỏ qua
        if not message.reply_to_message:
            return

        original_text = message.reply_to_message.text
        if not original_text:
            return

        # Lấy dòng đầu tiên
        header = original_text.split("\n")[0]

        # Không đúng format relay → bỏ qua
        if "|" not in header:
            return

        try:
            clean = header.replace("[", "").replace("]", "")
            phone, user_id = clean.split("|")
        except:
            return

        client = self.clone_manager.running.get(phone)
        if not client:
            return

        try:
            await client.send_message(int(user_id), message.text)
        except:
            pass
