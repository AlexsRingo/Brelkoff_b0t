\
import os
import json
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web

# ============== CONFIG ==============
API_TOKEN = os.getenv("API_TOKEN")
ADMINS = list(map(int, os.getenv("ADMINS", "").split(","))) if os.getenv("ADMINS") else []
SUPPORT_CONTACT = os.getenv("SUPPORT_CONTACT", "@Dashq0")

WELCOME_PIC = os.getenv("WELCOME_PIC", "https://placekitten.com/800/500")
CODE_ACCEPTED_PIC = os.getenv("CODE_ACCEPTED_PIC")          # картинка после принятия кода
INSTRUCTION_PIC = os.getenv("INSTRUCTION_PIC")              # картинка перед выдачей инструкции

NEWS_CHANNEL_ID = os.getenv("NEWS_CHANNEL_ID", "")          # -100... или @username
NEWS_CHANNEL_LINK = os.getenv("NEWS_CHANNEL_LINK", "https://t.me/")

WORDS_FILE = "words.json"   # словарь кодовых слов
STATE_FILE = "state.json"   # прогресс пользователей (выданная ссылка)
USERS_FILE = "users.json"   # база пользователей (на будущее)

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# ============== HELPERS ==============
def _load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def _save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_words():
    return _load_json(WORDS_FILE, {})

def save_words(d):
    _save_json(WORDS_FILE, d)

def load_state():
    return _load_json(STATE_FILE, {})

def save_state(d):
    _save_json(STATE_FILE, d)

def load_users():
    return _load_json(USERS_FILE, [])

def save_users(lst):
    _save_json(USERS_FILE, lst)

def add_user(user_id: int):
    users = load_users()
    if user_id not in users:
        users.append(user_id)
        save_users(users)

def norm_chat_ref(v: str):
    v = (v or "").strip()
    if v.startswith("-100"):
        return int(v)
    if v.startswith("@"):
        return v
    return f"@{v}" if v else v

# ============== KEYBOARDS ==============
def reply_kb():
    # Только СТАРТ — БИНГО отключено
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="СТАРТ")]],
        resize_keyboard=True
    )

def subscribe_kb():
    # Кнопка подписки + Проверки
    kb = []
    if NEWS_CHANNEL_LINK:
        kb.append([InlineKeyboardButton(text="🔗 Подписаться на канал", url=NEWS_CHANNEL_LINK)])
    kb.append([InlineKeyboardButton(text="✅ Проверить подписку", callback_data="checksub")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

# ============== WEB KEEP-ALIVE (Render) ==============
async def handle(_):
    return web.Response(text="Bot is running")

async def start_web_app():
    app = web.Application()
    app.router.add_get("/", handle)
    port = int(os.getenv("PORT", 5000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

# ============== COMMANDS ==============
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    add_user(message.from_user.id)
    text = (
        "Привет!\n"
        "На связи Даша — основатель бренда BRELKOF.\n"
        "Спасибо, что ты с нами! 💛\n\n"
        "Чтобы открыть доступ к инструкциям, введи кодовое слово с листовки через команду /slovo\n\n"
        f"Если возникнут вопросы — пиши в поддержку: {SUPPORT_CONTACT}"
    )
    try:
        await message.answer_photo(WELCOME_PIC, caption=text, reply_markup=reply_kb())
    except Exception:
        await message.answer(text, reply_markup=reply_kb())

# Кнопка "СТАРТ" (reply)
@dp.message(F.text.casefold() == "старт")
async def btn_start(message: types.Message):
    await cmd_start(message)

@dp.message(Command("info"))
async def cmd_info(message: types.Message):
    txt = (
        "ℹ️ Команды:\n"
        "/start — приветствие\n"
        "/slovo — ввести кодовое слово\n"
        "/getid — ID и тип чата\n"
        "👑 Админы:\n"
        "/listwords — список слов\n"
        "/addword_id <слово> <-100...> — слово → приватный канал (одноразовый инвайт)\n"
        "/addword_link <слово> <invite_link> — слово → постоянная ссылка\n"
        "/delword <слово> — удалить кодовое слово"
    )
    await message.answer(txt, reply_markup=reply_kb())

@dp.message(Command("getid"))
async def cmd_getid(message: types.Message):
    await message.answer(f"ID этого чата: {message.chat.id} | Тип: {message.chat.type}", reply_markup=reply_kb())

@dp.message(Command("slovo"))
async def cmd_slovo(message: types.Message):
    await message.answer("✏️ Введи кодовое слово:", reply_markup=reply_kb())

# ===== Admin word management =====
@dp.message(Command("listwords"))
async def cmd_listwords(message: types.Message):
    if message.from_user.id not in ADMINS:
        return await message.answer("⛔ Нет прав.")
    words = load_words()
    if not words:
        return await message.answer("📭 Список слов пуст.")
    lines = [f"• {w} → {cfg.get('type')} | {cfg.get('value')}" for w, cfg in words.items()]
    await message.answer("\n".join(lines))

@dp.message(Command("addword_id"))
async def cmd_addword_id(message: types.Message):
    if message.from_user.id not in ADMINS:
        return await message.answer("⛔ Нет прав.")
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        return await message.answer("Использование: /addword_id <слово> <-100...>")
    word = parts[1].strip().lower()
    try:
        chan_id = int(parts[2])
    except Exception:
        return await message.answer("ID должен быть числом -100...")
    words = load_words()
    words[word] = {"type": "id", "value": chan_id}
    save_words(words)
    await message.answer(f"✅ Слово '{word}' добавлено (канал: {chan_id}).")

@dp.message(Command("addword_link"))
async def cmd_addword_link(message: types.Message):
    if message.from_user.id not in ADMINS:
        return await message.answer("⛔ Нет прав.")
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        return await message.answer("Использование: /addword_link <слово> <invite_link>")
    word = parts[1].strip().lower()
    link = parts[2].strip()
    words = load_words()
    words[word] = {"type": "link", "value": link}
    save_words(words)
    await message.answer(f"✅ Слово '{word}' добавлено (ссылка).")

@dp.message(Command("delword"))
async def cmd_delword(message: types.Message):
    if message.from_user.id not in ADMINS:
        return await message.answer("⛔ Нет прав.")
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return await message.answer("Использование: /delword <слово>")
    word = parts[1].strip().lower()
    words = load_words()
    if word in words:
        words.pop(word)
        save_words(words)
        return await message.answer(f"🗑️ Удалено слово '{word}'.")
    await message.answer("Такого слова нет.")

# ============== CODE WORDS FLOW ==============
async def process_code_word(message: types.Message, word_text: str):
    word = word_text.strip().lower()
    words = load_words()
    cfg = words.get(word)
    if not cfg:
        return await message.answer("❌ Неверное слово. Попробуй ещё раз.", reply_markup=reply_kb())

    # сохраним выбранное слово в state
    state = load_state()
    uid = str(message.from_user.id)
    state.setdefault(uid, {})
    state[uid]["word"] = word
    save_state(state)

    intro_text = (
        "✅ Код принят!\n"
        "Перед тем, как перейти к урокам, подпишись на наш официальный канал BRELKOF.\n"
        "Именно там будут все новости, розыгрыши, конкурсы и анонсы наборов!"
    )
    try:
        if CODE_ACCEPTED_PIC:
            await message.answer_photo(CODE_ACCEPTED_PIC, caption=intro_text, reply_markup=subscribe_kb())
        else:
            await message.answer(intro_text, reply_markup=subscribe_kb())
    except Exception:
        await message.answer(intro_text, reply_markup=subscribe_kb())

@dp.callback_query(F.data == "checksub")
async def cb_checksub(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    state = load_state()
    user_state = state.get(uid, {})
    current_word = user_state.get("word")

    if not current_word:
        return await callback.message.answer("Сначала введи кодовое слово через /slovo.")

    # проверка подписки
    try:
        chat_for_check = norm_chat_ref(NEWS_CHANNEL_ID)
        member = await bot.get_chat_member(chat_for_check, callback.from_user.id)
        if getattr(member, "status", None) not in ("member", "administrator", "creator"):
            return await callback.message.answer("❌ Ты ещё не подписался на канал BRELKOF!")
    except Exception as e:
        return await callback.message.answer(f"⚠️ Ошибка проверки подписки. Проверял: {NEWS_CHANNEL_ID}\nДетали: {e}")

    # подписка пройдена → выдаём ссылку
    words = load_words()
    cfg = words.get(current_word, {})
    deliver_text = "Я очень рада, что ты с нами!\nЖелаю тебе приятно провести это время)\n\n"

    prev_link = user_state.get("issued_link")

    if cfg.get("type") == "id":
        if prev_link:
            msg = deliver_text + f"Вот твоя ссылка на инструкции: {prev_link}"
            if INSTRUCTION_PIC:
                await callback.message.answer_photo(INSTRUCTION_PIC, caption=msg)
            else:
                await callback.message.answer(msg)
        else:
            try:
                invite = await bot.create_chat_invite_link(chat_id=cfg["value"], member_limit=1)
                link = invite.invite_link
                user_state["issued_link"] = link
                state[uid] = user_state
                save_state(state)
                msg = deliver_text + f"Вот твоя ссылка на инструкции: {link}"
                if INSTRUCTION_PIC:
                    await callback.message.answer_photo(INSTRUCTION_PIC, caption=msg)
                else:
                    await callback.message.answer(msg)
            except Exception as e:
                await callback.message.answer(
                    "⚠️ Не удалось создать одноразовую ссылку. "
                    "Убедись, что бот — админ канала и имеет право создавать инвайты.\n"
                    f"Детали: {e}"
                )
    elif cfg.get("type") == "link":
        link = cfg.get("value")
        msg = deliver_text + f"Вот твоя ссылка на инструкции: {link}"
        if INSTRUCTION_PIC:
            await callback.message.answer_photo(INSTRUCTION_PIC, caption=msg)
        else:
            await callback.message.answer(msg)

# ============== TEXT ROUTER ==============
@dp.message(F.text)
async def on_text(message: types.Message):
    txt = message.text.strip()
    words = load_words()
    if txt.lower() in words:
        return await process_code_word(message, txt)

# ============== RUN ==============
async def main():
    asyncio.create_task(start_web_app())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
