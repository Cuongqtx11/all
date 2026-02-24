from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

from config import ADMIN_BOT_TOKEN, API_ID, API_HASH
from core.clone_manager import CloneManager
from database.models import add_account

bot = Bot(ADMIN_BOT_TOKEN)
dp = Dispatcher()
manager = CloneManager(bot)


# ==============================
# FSM LOGIN FLOW
# ==============================

class LoginState(StatesGroup):
    waiting_phone = State()
    waiting_code = State()
    waiting_2fa = State()


login_sessions = {}


# ==============================
# HELP
# ==============================

@dp.message(Command("help"))
async def help_cmd(message: Message):
    await message.answer("""
📌 DANH SÁCH LỆNH:

/login  → Thêm tài khoản clone mới
/list   → Xem danh sách clone
/start_clone <phone>
/stop_clone <phone>

/set_ad_a
/set_ad_b

/status → Kiểm tra hệ thống
""")


# ==============================
# LOGIN CLONE
# ==============================

@dp.message(Command("login"))
async def login_start(message: Message, state: FSMContext):
    await message.answer("📱 Nhập số điện thoại (VD: 849xxxxxxxx):")
    await state.set_state(LoginState.waiting_phone)


@dp.message(LoginState.waiting_phone)
async def get_phone(message: Message, state: FSMContext):
    phone = message.text.strip()

    client = TelegramClient(f"sessions/{phone}", API_ID, API_HASH)
    await client.connect()
    await client.send_code_request(phone)

    login_sessions[message.from_user.id] = {
        "client": client,
        "phone": phone
    }

    await message.answer("🔐 Nhập mã OTP Telegram:")
    await state.set_state(LoginState.waiting_code)


@dp.message(LoginState.waiting_code)
async def get_code(message: Message, state: FSMContext):
    code = message.text.strip()

    data = login_sessions.get(message.from_user.id)
    client = data["client"]
    phone = data["phone"]

    try:
        await client.sign_in(phone, code)
    except SessionPasswordNeededError:
        await message.answer("🔑 Tài khoản có 2FA. Nhập mật khẩu:")
        await state.set_state(LoginState.waiting_2fa)
        return

    await add_account(phone)
    await message.answer("✅ Đăng nhập thành công & lưu session.")
    await state.clear()


@dp.message(LoginState.waiting_2fa)
async def get_2fa(message: Message, state: FSMContext):
    password = message.text.strip()

    data = login_sessions.get(message.from_user.id)
    client = data["client"]
    phone = data["phone"]

    await client.sign_in(password=password)

    await add_account(phone)
    await message.answer("✅ Đăng nhập thành công (2FA) & lưu session.")
    await state.clear()


# ==============================
# START CLONE
# ==============================

@dp.message(Command("start_clone"))
async def start_clone(message: Message):
    parts = message.text.split()

    if len(parts) < 2:
        await message.answer("❌ Dùng đúng cú pháp:\n/start_clone 849xxxxxxxx")
        return

    phone = parts[1]

    await manager.start_clone(phone)
    await message.answer(f"🚀 Clone {phone} đã bắt đầu.")


# ==============================
# STOP CLONE
# ==============================

@dp.message(Command("stop_clone"))
async def stop_clone(message: Message):
    parts = message.text.split()

    if len(parts) < 2:
        await message.answer("❌ Dùng đúng cú pháp:\n/stop_clone 849xxxxxxxx")
        return

    phone = parts[1]

    if phone in manager.running:
        await manager.running[phone].disconnect()
        del manager.running[phone]
        await message.answer(f"🛑 Clone {phone} đã dừng.")
    else:
        await message.answer("Clone chưa chạy.")


# ==============================
# LIST CLONE
# ==============================

@dp.message(Command("list"))
async def list_clone(message: Message):
    if not manager.running:
        await message.answer("Không có clone nào đang chạy.")
        return

    text = "📋 Clone đang chạy:\n"
    for phone in manager.running:
        text += f"• {phone}\n"

    await message.answer(text)


# ==============================
# STATUS
# ==============================

@dp.message(Command("status"))
async def status_cmd(message: Message):
    running = len(manager.running)

    await message.answer(f"""
📊 HỆ THỐNG:

Clone đang chạy: {running}
Admin Bot: Hoạt động
AI Groq: Hoạt động
Relay: Hoạt động
""")


# ==============================
# RELAY ADMIN REPLY
# ==============================

@dp.message()
async def relay_reply(message: Message):
    await manager.relay.handle_reply(message)
