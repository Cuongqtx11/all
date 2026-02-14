import asyncio
import logging
import random
import json
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from app.config import *
from app import database as db
from app.services import locket, nextdns

logger = logging.getLogger(__name__)

request_queue = asyncio.Queue()
pending_items = []
queue_lock = asyncio.Lock()

class Clr:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

async def update_pending_positions(app):
    for i, item in enumerate(pending_items):
        position = i + 1
        ahead = i
        try:
            # Update position text
            await app.bot.edit_message_text(
                chat_id=item['chat_id'],
                message_id=item['message_id'],
                text=T("queued", item['lang']).format(item['username'], position, ahead),
                parse_mode=ParseMode.HTML
            )
            
            # Notify if almost turn (ahead == 2)
            if ahead == 2:
                try:
                    await app.bot.send_message(
                        chat_id=item['chat_id'],
                        text=T("queue_almost", item['lang']),
                        parse_mode=ParseMode.HTML
                    )
                except:
                    pass
        except:
            pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = db.get_lang(user_id) or DEFAULT_LANG
    
    if not db.get_user_usage(user_id):
        pass 

    await update.message.reply_text(
        T("welcome", lang),
        parse_mode=ParseMode.HTML,
        reply_markup=get_main_menu_keyboard(lang)
    )

async def setlang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_language_select(update)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = db.get_lang(user_id) or DEFAULT_LANG
    
    help_text = T("help_msg", lang)
    if user_id == ADMIN_ID:
        help_text += (
            f"\n\n<b>👑 Admin Control:</b>\n"
            f"/noti [msg] - Broadcast message\n"
            f"/rs [id] - Reset usage limit\n"
            f"/setdonate - Set success photo\n"
            f"/settoken - Upload token sets\n"
            f"/stats - View detailed statistics"
        )
        
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID: return

    stats = db.get_stats()
    msg = (
        f"{E_STAT} <b>SYSTEM STATISTICS</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"{E_USER} <b>Active Users</b>: {stats['unique_users']}\n"
        f"{E_GLOBE} <b>Total Requests</b>: {stats['total']}\n"
        f"{E_SUCCESS} <b>Success</b>: {stats['success']}\n"
        f"{E_ERROR} <b>Failed</b>: {stats['fail']}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"{E_ANDROID} <b>Active Workers</b>: {NUM_WORKERS}\n"
        f"🔑 <b>Token Sets</b>: {len(db.get_token_sets() or TOKEN_SETS)}\n"
        f"⏳ <b>Queue Size</b>: {request_queue.qsize()}\n"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

# --- Admin Commands ---
async def broadcast_worker(bot, users, text, chat_id, message_id):
    success = 0
    fail = 0
    total = len(users)
    
    for i, uid in enumerate(users):
        try:
            await bot.send_message(chat_id=uid, text=f"📢 <b>ADMIN NOTIFICATION</b>\n\n{text}", parse_mode=ParseMode.HTML)
            success += 1
        except Exception:
            fail += 1
            
        # Update progress every 5 users or at the end
        if (i + 1) % 5 == 0 or (i + 1) == total:
            try:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=(
                        f"{E_LOADING} <b>Broadcasting...</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"🔄 <b>Progress</b>: {i+1}/{total}\n"
                        f"{E_SUCCESS} <b>Success</b>: {success}\n"
                        f"{E_ERROR} <b>Failed</b>: {fail}"
                    ),
                    parse_mode=ParseMode.HTML
                )
            except:
                pass
        
        await asyncio.sleep(0.05) # Prevent flood limits

    # Final completion message
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=(
                f"{E_SUCCESS} <b>Broadcast Complete!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"👥 <b>Total</b>: {total}\n"
                f"{E_SUCCESS} <b>Success</b>: {success}\n"
                f"{E_ERROR} <b>Failed</b>: {fail}"
            ),
            parse_mode=ParseMode.HTML
        )
    except:
        pass

async def noti_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = db.get_lang(user_id) or DEFAULT_LANG
    
    if user_id != ADMIN_ID:
        return
        
    msg = " ".join(context.args)
    if not msg:
        await update.message.reply_text("Usage: /noti {message}")
        return

    users = db.get_all_users()
    if not users:
        await update.message.reply_text("No users found.")
        return

    status_msg = await update.message.reply_text(
        f"{E_LOADING} <b>Starting broadcast to {len(users)} users...</b>",
        parse_mode=ParseMode.HTML
    )
    
    asyncio.create_task(broadcast_worker(context.bot, users, msg, status_msg.chat_id, status_msg.message_id))

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = db.get_lang(user_id) or DEFAULT_LANG
    
    if user_id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text("Usage: /rs {user_id}")
        return
        
    try:
        target_id = int(context.args[0])
        db.reset_usage(target_id)
        await update.message.reply_text(T("admin_reset", lang).format(target_id))
    except ValueError:
        await update.message.reply_text("Invalid User ID")

async def set_donate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return

    photo = None
    if update.message.reply_to_message and update.message.reply_to_message.photo:
        photo = update.message.reply_to_message.photo[-1]
    elif update.message.photo:
        photo = update.message.photo[-1]
        
    if photo:
        file_id = photo.file_id
        db.set_config("donate_photo", file_id)
        await update.message.reply_text(f"✅ Updated Donate Photo ID:\n<code>{file_id}</code>", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text("❌ Please reply to a photo with /setdonate to set it.")

def parse_tokens_from_text(text):
    tokens = []

    try:
        json_match = re.search(r'(\[[\s\S]*\]|\{[\s\S]*\})', text)
        if json_match:
            data = json.loads(json_match.group(1))
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and ("fetch_token" in item or "app_transaction" in item):
                        tokens.append({
                            "fetch_token": item.get("fetch_token", ""),
                            "app_transaction": item.get("app_transaction", ""),
                            "hash_params": item.get("hash_params", ""),
                            "hash_headers": item.get("hash_headers", ""),
                            "is_sandbox": item.get("is_sandbox", False)
                        })
                if tokens:
                    return tokens
            elif isinstance(data, dict) and ("fetch_token" in data or "app_transaction" in data):
                tokens.append({
                    "fetch_token": data.get("fetch_token", ""),
                    "app_transaction": data.get("app_transaction", ""),
                    "hash_params": data.get("hash_params", ""),
                    "hash_headers": data.get("hash_headers", ""),
                    "is_sandbox": data.get("is_sandbox", False)
                })
                return tokens
    except (json.JSONDecodeError, ValueError):
        pass

    for line in text.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("|")
        if len(parts) >= 2:
            tokens.append({
                "fetch_token": parts[0].strip(),
                "app_transaction": parts[1].strip(),
                "hash_params": parts[2].strip() if len(parts) > 2 else "",
                "hash_headers": parts[3].strip() if len(parts) > 3 else "",
                "is_sandbox": parts[4].strip().lower() == "true" if len(parts) > 4 else False
            })

    if not tokens:
        ft_matches = re.findall(r'fetch_token["\s:=]+([^\s",\}]+)', text)
        at_matches = re.findall(r'app_transaction["\s:=]+([^\s",\}]+)', text)
        hp_matches = re.findall(r'hash_params["\s:=]+([^\s",\}]*)', text)
        hh_matches = re.findall(r'hash_headers["\s:=]+([^\s",\}]*)', text)
        sb_matches = re.findall(r'is_sandbox["\s:=]+(true|false|True|False)', text, re.IGNORECASE)

        count = max(len(ft_matches), len(at_matches))
        for i in range(count):
            tokens.append({
                "fetch_token": ft_matches[i] if i < len(ft_matches) else "",
                "app_transaction": at_matches[i] if i < len(at_matches) else "",
                "hash_params": hp_matches[i] if i < len(hp_matches) else "",
                "hash_headers": hh_matches[i] if i < len(hh_matches) else "",
                "is_sandbox": (sb_matches[i].lower() == "true") if i < len(sb_matches) else False
            })

    return tokens

async def settoken_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return

    await update.message.reply_text(
        f"{E_LOADING} <b>Gửi file token</b>\n\n"
        f"Gửi file <code>.json</code> hoặc <code>.txt</code> chứa token.\n\n"
        f"<b>JSON:</b>\n"
        f"<pre>[\n"
        f'  {{"fetch_token": "ey...", "app_transaction": "ey...", "hash_params": "", "hash_headers": "", "is_sandbox": true}}\n'
        f"]</pre>\n\n"
        f"<b>TXT</b> (mỗi dòng 1 token):\n"
        f"<pre>fetch_token|app_transaction|hash_params|hash_headers|true</pre>\n\n"
        f"Hoặc dán trực tiếp nội dung vào tin nhắn.",
        parse_mode=ParseMode.HTML
    )
    context.user_data['waiting_token'] = True

async def handle_token_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return False

    if update.message.document:
        file = await update.message.document.get_file()
        file_bytes = await file.download_as_bytearray()
        text = file_bytes.decode("utf-8", errors="ignore")
    elif context.user_data.get('waiting_token') and update.message.text:
        text = update.message.text.strip()
        context.user_data['waiting_token'] = False
    else:
        return False

    tokens = parse_tokens_from_text(text)
    if not tokens:
        await update.message.reply_text(
            f"{E_ERROR} Không tìm thấy token hợp lệ trong nội dung.\n"
            f"Kiểm tra lại định dạng file.",
            parse_mode=ParseMode.HTML
        )
        return True

    db.save_token_sets(tokens)

    import app.config as cfg
    cfg.TOKEN_SETS = db.get_token_sets()

    msg = f"{E_SUCCESS} <b>Đã lưu {len(tokens)} token set(s)!</b>\n\n"
    for i, ts in enumerate(tokens):
        ft_preview = ts['fetch_token'][:25] + "..." if len(ts['fetch_token']) > 25 else ts['fetch_token']
        sandbox = "Sandbox" if ts['is_sandbox'] else "Production"
        msg += f"#{i+1}: <code>{ft_preview}</code> ({sandbox})\n"
    msg += f"\nToken đã được lưu vào database, lần sau không cần gửi lại."

    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
    return True

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return
    handled = await handle_token_file(update, context)
    if not handled:
        await update.message.reply_text(
            f"{E_ERROR} Không đọc được token từ file.\nDùng /settoken để xem hướng dẫn.",
            parse_mode=ParseMode.HTML
        )

async def show_language_select(update: Update):
    keyboard = [
        [InlineKeyboardButton("Tiếng Việt 🇻🇳", callback_data="setlang_VI")],
        [InlineKeyboardButton("English 🇺🇸", callback_data="setlang_EN")]
    ]
    text = T("lang_select", "EN")
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id == ADMIN_ID and context.user_data.get('waiting_token'):
        handled = await handle_token_file(update, context)
        if handled:
            return

    if not update.message.reply_to_message or not update.message.reply_to_message.from_user.is_bot:
        return

    text = update.message.text.strip()
    lang = db.get_lang(user_id) or DEFAULT_LANG

    if "locket.cam/" in text:
        username = text.split("locket.cam/")[-1].split("?")[0]
    elif len(text) < 50 and " " not in text:
        username = text
    else:
        username = text

    msg = await update.message.reply_text(T("resolving", lang), parse_mode=ParseMode.HTML)
    
    uid = await locket.resolve_uid(username)
    if not uid:
        await msg.edit_text(T("not_found", lang), parse_mode=ParseMode.HTML)
        return
        
    # Admin bypass limit check
    if user_id != ADMIN_ID and not db.check_can_request(user_id):
        await msg.edit_text(T("limit_reached", lang), parse_mode=ParseMode.HTML)
        return
        
    await msg.edit_text(T("checking_status", lang), parse_mode=ParseMode.HTML)
    status = await locket.check_status(uid)
    
    status_text = T("free_status", lang)
    if status and status.get("active"):
        status_text = T("gold_active", lang).format(status['expires'])
    
    safe_username = username[:30]
    keyboard = [[InlineKeyboardButton(T("btn_upgrade", lang), callback_data=f"upg|{uid}|{safe_username}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await msg.edit_text(
        f"{T('user_info_title', lang)}\n"
        f"{E_ID}: <code>{uid}</code>\n"
        f"{E_TAG}: <code>{username}</code>\n"
        f"{E_STAT} <b>Status</b>: {status_text}\n\n"
        f"👇",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    lang = db.get_lang(user_id) or DEFAULT_LANG

    if data.startswith("setlang_"):
        new_lang = data.split("_")[1]
        db.set_lang(user_id, new_lang)
        lang = new_lang
        await query.answer(f"Language: {new_lang}")
        await query.message.edit_text(
            T("menu_msg", lang),
            parse_mode=ParseMode.HTML,
            reply_markup=get_main_menu_keyboard(lang)
        )
        return

    if data == "menu_lang":
        await show_language_select(update)
        return
        
    if data == "menu_help":
        help_text = T("help_msg", lang)
        if user_id == ADMIN_ID:
            help_text += (
                f"\n\n<b>👑 Admin Control:</b>\n"
                f"/noti [msg] - Broadcast message\n"
                f"/rs [id] - Reset usage limit\n"
                f"/setdonate - Set success photo\n"
                f"/stats - View detailed statistics"
            )
            
        await query.edit_message_text(
            help_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="menu_back")]])
        )
        return

    if data == "menu_back":
        await query.message.edit_text(
            T("menu_msg", lang),
            parse_mode=ParseMode.HTML,
            reply_markup=get_main_menu_keyboard(lang)
        )
        return

    if data == "menu_input":
        try:
            await query.answer()
        except:
            pass
        await query.message.reply_text(
            T("prompt_input", lang),
            parse_mode=ParseMode.HTML,
            reply_markup=ForceReply(selective=True, input_field_placeholder="Username...")
        )
        return

    if data.startswith("upg|"):
        parts = data.split("|")
        uid = parts[1]
        username = parts[2] if len(parts) > 2 else uid
        
        # Admin bypass limit check
        if user_id != ADMIN_ID and not db.check_can_request(user_id):
            try:
                await query.answer(T("limit_reached", lang), show_alert=True)
            except:
                pass
            return
            
        try:
            await query.answer("🚀 Queue...")
        except:
            pass
        
        item = {
            'user_id': user_id,
            'uid': uid,
            'username': username,
            'chat_id': query.message.chat_id,
            'message_id': query.message.message_id,
            'lang': lang
        }
        
        async with queue_lock:
            pending_items.append(item)
            position = len(pending_items)
            ahead = position - 1
        
        await query.edit_message_text(
            T("queued", lang).format(username, position, ahead),
            parse_mode=ParseMode.HTML
        )
        
        await request_queue.put(item)
        return

async def queue_worker(app, worker_id):
    import app.config as cfg

    print(f"Worker #{worker_id} started...")
    
    while True:
        try:
            item = await request_queue.get()
            
            user_id = item['user_id']
            uid = item['uid']
            username = item['username']
            chat_id = item['chat_id']
            message_id = item['message_id']
            lang = item['lang']
            
            async with queue_lock:
                if item in pending_items:
                    pending_items.remove(item)
                await update_pending_positions(app) # Enabled queue updates
            
            token_idx = (worker_id - 1) % len(cfg.TOKEN_SETS)
            token_config = cfg.TOKEN_SETS[token_idx]
            token_name = f"Token-{token_idx+1}"
            
            print(f"{Clr.BLUE}[Worker #{worker_id}][{token_name}] Processing:{Clr.ENDC} UID={uid} | UserID={user_id}")
            
            async def edit(text):
                try:
                    await app.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=text,
                        parse_mode=ParseMode.HTML,
                        disable_web_page_preview=True
                    )
                except Exception as e:
                    if "Message is not modified" in str(e):
                        pass
                    elif "Message to edit not found" in str(e):
                        pass
                    else:
                        logger.error(f"Edit msg error: {e}")

            # Double check limit before processing (unless admin)
            if user_id != ADMIN_ID and not db.check_can_request(user_id):
                await edit(T("limit_reached", lang))
                request_queue.task_done()
                continue
            
            logs = [f"[Worker #{worker_id}] Processing Request..."]
            loop = asyncio.get_running_loop()
            
            def safe_log_callback(msg):
                clean_msg = msg.replace(Clr.BLUE, "").replace(Clr.GREEN, "").replace(Clr.WARNING, "").replace(Clr.FAIL, "").replace(Clr.ENDC, "").replace(Clr.BOLD, "")
                logs.append(clean_msg)
                asyncio.run_coroutine_threadsafe(update_log_ui(), loop)

            async def update_log_ui():
                display_logs = "\n".join(logs[-10:])
                text = (
                    f"{E_LOADING} <b>⚡ SYSTEM EXPLOIT RUNNING...</b>\n"
                    f"<pre>{display_logs}</pre>"
                )
                try:
                    await app.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=text,
                        parse_mode=ParseMode.HTML,
                        disable_web_page_preview=True
                    )
                except:
                    pass

            await update_log_ui()
            
            # Use dynamic token config
            success, msg_result = await locket.inject_gold(uid, token_config, safe_log_callback)
            
            # Log request to DB
            db.log_request(user_id, uid, "SUCCESS" if success else "FAIL")
            
            if success:
                if user_id != ADMIN_ID:
                    db.increment_usage(user_id)
                    
                pid, link = await nextdns.create_profile(NEXTDNS_KEY, safe_log_callback)
                
                dns_text = ""
                if link:
                   dns_text = T('dns_msg', lang).format(link, pid)
                else:
                   dns_text = f"{E_ERROR} NextDNS Error: Check API Key"
                
                final_msg = (
                    f"{T('success_title', lang)}\n\n"
                    f"{E_TAG}: <code>{username}</code>\n"
                    f"{E_ID}: <code>{uid}</code>\n"
                    f"{E_CALENDAR} <b>Plan</b>: Gold (30d)\n"
                    f"{dns_text}"
                )
                
                await asyncio.sleep(2.0)
                
                # Delete progress message and send photo with caption
                try:
                    await app.bot.delete_message(chat_id=chat_id, message_id=message_id)
                except:
                    pass
                
                try:
                    current_photo = db.get_config("donate_photo", DONATE_PHOTO)
                    await app.bot.send_photo(
                        chat_id=chat_id,
                        photo=current_photo,
                        caption=final_msg,
                        parse_mode=ParseMode.HTML
                    )
                except Exception as e:
                    logger.error(f"Send photo error: {e}")
                    # Fallback to text if photo fails
                    await app.bot.send_message(
                        chat_id=chat_id,
                        text=final_msg,
                        parse_mode=ParseMode.HTML,
                        disable_web_page_preview=True
                    )

                # Wait 45s for THIS token/worker
                await asyncio.sleep(45)
            else:
                final_msg = f"{T('fail_title', lang)}\nInfo:\n<code>{msg_result}</code>"
                await edit(final_msg)
                
            request_queue.task_done()
            
        except Exception as e:
            logger.error(f"Worker #{worker_id} Exception: {e}")
            request_queue.task_done()

def get_main_menu_keyboard(lang):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(T("btn_input", lang), callback_data="menu_input")],
        [InlineKeyboardButton(T("btn_lang", lang), callback_data="menu_lang"),
         InlineKeyboardButton(T("btn_help", lang), callback_data="menu_help")]
    ])

def run_bot():
    logging.basicConfig(
        format='%(message)s',
        level=logging.INFO
    )
    logging.getLogger("httpx").setLevel(logging.ERROR)
    logging.getLogger("telegram").setLevel(logging.ERROR)
    logging.getLogger("aiohttp").setLevel(logging.ERROR)

    if not BOT_TOKEN:
        print("[ERROR] BOT_TOKEN chua duoc cau hinh trong file .env")
        return
    if not ADMIN_ID:
        print("[WARNING] ADMIN_ID chua duoc cau hinh trong file .env - cac lenh admin se khong hoat dong")

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setlang", setlang_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("noti", noti_command))
    app.add_handler(CommandHandler("rs", reset_command))
    app.add_handler(CommandHandler("setdonate", set_donate_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("settoken", settoken_command))
    
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    async def post_init(application):
        import app.config as cfg
        has_valid_tokens = any(
            ts.get('fetch_token') for ts in cfg.TOKEN_SETS
        )
        if not has_valid_tokens and ADMIN_ID:
            try:
                await application.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=(
                        f"{E_LOADING} <b>Bot đã khởi động nhưng chưa có token!</b>\n\n"
                        f"Gửi file <code>api.txt</code> hoặc <code>.json</code> chứa token vào đây.\n"
                        f"Bot sẽ tự đọc và chạy ngay."
                    ),
                    parse_mode=ParseMode.HTML
                )
                print("[INFO] Chua co token - da gui yeu cau toi admin")
            except Exception as e:
                print(f"[WARNING] Khong gui duoc tin nhan cho admin: {e}")

        for i in range(1, NUM_WORKERS + 1):
            asyncio.create_task(queue_worker(application, i))

    app.post_init = post_init
    print(f"Bot is running... ({NUM_WORKERS} workers)")
    app.run_polling()
