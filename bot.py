\
import os
import json
import logging
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import web

# ========= CONFIG =========
API_TOKEN = os.getenv("API_TOKEN")
ADMINS = list(map(int, os.getenv("ADMINS", "").split(","))) if os.getenv("ADMINS") else []
SUPPORT_CONTACT = os.getenv("SUPPORT_CONTACT", "@Dashq0")
WELCOME_PIC = os.getenv("WELCOME_PIC", "https://placekitten.com/600/350")
BINGO_PIC = os.getenv("BINGO_PIC", "https://placekitten.com/600/400")
NEWS_CHANNEL_ID = os.getenv("NEWS_CHANNEL_ID", "-1002900328490")
NEWS_CHANNEL_LINK = os.getenv("NEWS_CHANNEL_LINK", "https://t.me/+EVFwvTKKwlJhOTNi")

WORDS_MAP = {
    "ушастик": {"type": "id", "value": -1002900328490},
    "геннадий": {"type": "link", "value": "https://t.me/+E8VHovI3OAcyYjQy"},
}

USERS_FILE = "users.json"
MSGS_FILE = "messages.json"
BINGO_FILE = "bingo.json"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

REPLY_MAP = {}  # admin_message_id -> user_id

# ========= HELPERS =========
def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Error saving {path}: {e}")

def load_list(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_list(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_user(user_id):
    users = load_list(USERS_FILE)
    if user_id not in users:
        users.append(user_id)
        save_list(USERS_FILE, users)

def log_message(entry):
    msgs = load_list(MSGS_FILE)
    msgs.append(entry)
    save_list(MSGS_FILE, msgs)

# ========= KEYBOARDS =========
def reply_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="СТАРТ"), KeyboardButton(text="БИНГО")]],
        resize_keyboard=True
    )

def bingo_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ ГОТОВО", callback_data="bingo_done")
    kb.adjust(1)
    return kb.as_markup()

# ========= WEB KEEP-ALIVE =========
async def handle(request):
    return web.Response(text="Bot is alive")

async def start_web_app():
    app = web.Application()
    app.router.add_get("/", handle)
    port = int(os.getenv("PORT", 5000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

# ========= COMMANDS =========
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    add_user(message.from_user.id)
    text = (
        "Привет!\\n"
        "На связи Даша — основатель бренда BRELKOF.\\n"
        "Спасибо, что ты с нами! 💛\\n\\n"
        "Чтобы открыть доступ к инструкциям, введи кодовое слово с листовки через команду /slovo\\n\\n"
        f"Если возникнут вопросы — пиши в поддержку: {SUPPORT_CONTACT}"
    )
    try:
        await message.answer_photo(WELCOME_PIC, caption=text, reply_markup=reply_kb())
    except:
        await message.answer(text, reply_markup=reply_kb())

@dp.message(Command("info"))
async def cmd_info(message: types.Message):
    text = (
        "ℹ️ Команды бота:\\n"
        "/start — приветствие\\n"
        "/slovo — ввести кодовое слово\\n"
        "/getid — ID чата\\n"
        "/info — помощь\\n\\n"
        "👑 Админы:\\n"
        "- пересылай посты сюда для рассылки\\n"
        "- отвечай на пересланные сообщения пользователей для обратной связи"
    )
    await message.answer(text, reply_markup=reply_kb())

@dp.message(Command("getid"))
async def cmd_getid(message: types.Message):
    await message.answer(f"ID этого чата: {message.chat.id}")

@dp.message(Command("slovo"))
async def cmd_slovo(message: types.Message):
    await message.answer("✏️ Введи кодовое слово:")

# ========= BINGO =========
@dp.message(F.text == "БИНГО")
async def btn_bingo(message: types.Message):
    try:
        chat_for_check = int(NEWS_CHANNEL_ID) if str(NEWS_CHANNEL_ID).startswith("-100") else NEWS_CHANNEL_ID
        member = await bot.get_chat_member(chat_for_check, message.from_user.id)
        if member.status not in ("member", "administrator", "creator"):
            return await message.answer("❌ Сначала подпишись на наш канал!", reply_markup=reply_kb())
    except Exception as e:
        return await message.answer(f"⚠️ Ошибка проверки подписки: {e}")

    text = (
        "А еще у нас есть БИНГО 😍\\n\\n"
        "Выполни задания, зачеркни все на карточке и получи промокод 15% себе или другу\\n"
        "🥰 промокод единоразовый\\n\\n"
        "1. Подписаться на Телеграм и Инстаграм\\n"
        "2. Оставить отзыв на Озоне или ВБ / если набор подарили — в посте\\n"
        "3. Выложить зайца в свои соц.сети, отметив BRELKOF\\n"
        "4. Дать обратную связь на набор по кнопке ниже. Нам очень ценна ваша конструктивная критика\\n\\n"
        "🥰 После выполнения тыкай ГОТОВО"
    )
    try:
        await message.answer_photo(BINGO_PIC, caption=text, reply_markup=bingo_kb())
    except:
        await message.answer(text, reply_markup=bingo_kb())

@dp.callback_query(F.data == "bingo_done")
async def bingo_done(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    bingo_data = load_json(BINGO_FILE)
    user_data = bingo_data.get(uid, {})
    if not user_data.get("review") or not user_data.get("social"):
        await callback.message.answer("❌ Ты не прислал все ссылки. Нужно отзыв и пост в соцсетях.")
    else:
        for admin in ADMINS:
            try:
                await bot.send_message(
                    admin,
                    f"📩 Заявка БИНГО от @{callback.from_user.username or callback.from_user.id}\\n"
                    f"Отзыв: {user_data['review']}\\n"
                    f"Соцсети: {user_data['social']}"
                )
            except:
                pass
        await callback.message.answer("✅ Спасибо! Мы проверим задания и вручную отправим промокод 🥰")
    try:
        await callback.answer()
    except:
        pass

# ========= LINKS HANDLER =========
@dp.message(F.text.regexp(r'^https?://'))
async def handle_links(message: types.Message):
    uid = str(message.from_user.id)
    bingo_data = load_json(BINGO_FILE)
    if uid not in bingo_data:
        bingo_data[uid] = {"username": message.from_user.username}
    # если ссылки ещё нет — сохраняем как отзыв, иначе как соцсети
    if not bingo_data[uid].get("review"):
        bingo_data[uid]["review"] = message.text.strip()
        await message.answer("✅ Ссылка на отзыв сохранена! Пришли теперь ссылку на пост в соцсетях 🐰")
    elif not bingo_data[uid].get("social"):
        bingo_data[uid]["social"] = message.text.strip()
        await message.answer("✅ Ссылка на соцсети сохранена! Теперь жми ГОТОВО 😍")
    else:
        await message.answer("⚠️ Ты уже прислал все ссылки. Жми ГОТОВО!")
    save_json(BINGO_FILE, bingo_data)

# ========= OTHER HANDLERS (support, broadcast) =========
@dp.message()
async def all_messages(message: types.Message):
    add_user(message.from_user.id)
    if message.from_user.id in ADMINS and message.forward_from_chat:
        users = load_list(USERS_FILE)
        sent = 0
        for uid in users:
            try:
                await bot.copy_message(uid, message.chat.id, message.message_id)
                sent += 1
            except:
                pass
        await message.answer(f"✅ Рассылка отправлена {sent} пользователям.")
        return
    entry = {
        "user_id": message.from_user.id,
        "username": f"@{message.from_user.username}" if message.from_user.username else None,
        "text": message.text or "[non-text]",
        "date": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    }
    log_message(entry)
    for admin in ADMINS:
        try:
            sent_msg = await bot.copy_message(admin, message.chat.id, message.message_id)
            REPLY_MAP[sent_msg.message_id] = message.from_user.id
        except:
            pass

# ========= RUN =========
async def main():
    asyncio.create_task(start_web_app())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
