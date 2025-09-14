import os
import json
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web

# ===================== Настройки =====================
API_TOKEN = os.getenv("API_TOKEN")  # токен бота
INSTRUCTION_CHANNEL_ID = int(os.getenv("INSTRUCTION_CHANNEL_ID", "-1001234567890"))  # канал с инструкциями
NEWS_CHANNEL_USERNAME = os.getenv("NEWS_CHANNEL_USERNAME", "@brelkof")  # публичный username канала (для кнопки)
ADMINS = list(map(int, os.getenv("ADMINS", "").split(",")))

WORDS_FILE = "words.json"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# ===================== Работа со словами =====================
def load_words():
    try:
        with open(WORDS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_words(words):
    with open(WORDS_FILE, "w", encoding="utf-8") as f:
        json.dump(words, f, ensure_ascii=False, indent=4)

# ===================== Хэндлеры =====================
@dp.message(Command("start"))
async def start(message: types.Message):
    text = (
        "Привет!  \n"
        "На связи Даша - основатель бренда BRELKOF.\n"
        "Спасибо, что ты с нами)\n"
        "Мы делаем все, чтобы у тебя получился свой собственный плюшевый зайчик)\n\n"
        "Чтобы открыть доступ к инструкциям введи кодовое слово с листовки:\n"
        "Через команду /slovo"
    )
    await message.answer(text)

@dp.message(Command("slovo"))
async def ask_word(message: types.Message):
    await message.answer("✏️ Введи кодовое слово:")

@dp.message(Command("addword"))
async def add_word(message: types.Message):
    if message.from_user.id not in ADMINS:
        return await message.answer("⛔ У вас нет прав.")
    parts = message.text.split()
    if len(parts) != 2:
        return await message.answer("Использование: /addword <слово>")
    word = parts[1].strip().lower()
    words = load_words()
    if word in words:
        return await message.answer("⚠️ Слово уже существует.")
    words.append(word)
    save_words(words)
    await message.answer(f"✅ Слово '{word}' добавлено.")

@dp.message(Command("listwords"))
async def list_words(message: types.Message):
    if message.from_user.id not in ADMINS:
        return await message.answer("⛔ У вас нет прав.")
    words = load_words()
    if not words:
        return await message.answer("📭 Список пуст.")
    await message.answer("📌 Секретные слова:\n" + "\n".join(words))

@dp.message()
async def check_word(message: types.Message):
    word = message.text.strip().lower()
    words = load_words()

    if word in words:
        # Предлагаем подписку
        keyboard = InlineKeyboardMarkup().add(
            InlineKeyboardButton("Подписаться на канал BRELKOF", url=f"https://t.me/{NEWS_CHANNEL_USERNAME.strip('@')}")
        )
        await message.answer(
            "✅ Код принят!\n"
            "Перед тем, как перейти к урокам, подпишись на наш официальный канал BRELKOF.\n"
            "Именно там будут все новости, розыгрыши, конкурсы и анонсы наборов!",
            reply_markup=keyboard
        )
    else:
        await message.answer("❌ Неверное слово. Попробуй ещё раз.")

# Команда проверки подписки
@dp.message(Command("checksub"))
async def check_subscription(message: types.Message):
    try:
        member = await bot.get_chat_member(chat_id=NEWS_CHANNEL_USERNAME, user_id=message.from_user.id)
        if member.status in ["member", "administrator", "creator"]:
            # Подписка есть → выдаем инструкции
            bingo_btn = InlineKeyboardMarkup().add(
                InlineKeyboardButton("🎯 БИНГО", callback_data="bingo")
            )
            invite = await bot.create_chat_invite_link(
                chat_id=INSTRUCTION_CHANNEL_ID,
                member_limit=1
            )
            await message.answer(
                "Спасибо тебе!\n"
                "А еще у нас есть БИНГО 🎉\n"
                "Выполняя задания, ты получишь скидку на следующий заказ.",
                reply_markup=bingo_btn
            )
            await message.answer(
                "Я очень рада, что ты с нами!\nЖелаю тебе приятно провести это время)\n\n"
                f"Вот твоя ссылка на инструкции: {invite.invite_link}"
            )
        else:
            await message.answer("❌ Ты еще не подписался на канал BRELKOF!")
    except Exception as e:
        await message.answer("⚠️ Ошибка при проверке подписки. Убедись, что канал доступен и бот там админ.")

# Заглушка для бинго
@dp.callback_query()
async def bingo_callback(callback: types.CallbackQuery):
    if callback.data == "bingo":
        await callback.message.answer("🎯 Раздел БИНГО пока в разработке 😉")

# ===================== AIOHTTP сервер для Render =====================
async def handle(request):
    return web.Response(text="Bot is running")

async def start_web_app():
    app = web.Application()
    app.router.add_get("/", handle)
    port = int(os.getenv("PORT", 5000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

# ===================== Запуск =====================
async def main():
    asyncio.create_task(start_web_app())  # запускаем web-сервер
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
