import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")

ADMIN_BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN")
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID"))

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

MAX_DM_PER_DAY = 15
