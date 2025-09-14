import os
import json
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import web

# ===================== Настройки =====================
API_TOKEN = os.getenv("API_TOKEN")  # токен бота
INSTRUCTION_CHANNEL_ID = int(os.getenv("INSTRUCTION_CHANNEL_ID", "-1001234567890"))  # канал с инструкциями (numeric ID)
NEWS_CHANNEL_ID = os.getenv("NEWS_CHANNEL_USERNAME", "-1001234567890")  # ID новостного канала (numeric)
NEWS_CHANNEL_LINK = os.getenv("NEWS_CHANNEL_LINK", "https://t.me/+EVFwvTKKwlJhOTNi")  # ссылка для кнопки
WELCOME_PIC = os.getenv("WELCOME_PIC", "https://placekitten.com/400/300")  # картинка при старте
ADMINS = list(map(int, os.getenv("ADMINS", "").split(","))) if os.getenv("ADMINS") else []

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

# ===================== Команды =====================
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
    try:
        await message.answer_photo(photo=WELCOME_PIC, caption=text)
    except Exception:
        await message.answer(text)

@dp.message(Command("slovo"))
async def ask_word(message: types.Message):
    await message.answer("✏️ Введи кодовое слово:")

@dp.message(Command("addword"))
async def add_word(message: types.Message):
    if message.from_user.id not in ADMINS:
        return await message.answer("⛔ У вас нет прав.")
    parts = message.text.split(maxsplit=1)
    if len(parts) != 2 or not parts[1].strip():
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

@dp.message(Command("getid"))
async def get_id(message: types.Message):
    await message.answer(f"ID этого чата: {message.chat.id}")

@dp.message(Command("sendpic"))
async def send_pic(message: types.Message):
    if message.from_user.id not in ADMINS:
        return await message.answer("⛔ У вас нет прав.")
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        return await message.answer("Использование: /sendpic <url_картинки> <текст>")
    url = parts[1]
    caption = parts[2]
    try:
        await message.answer_photo(photo=url, caption=caption)
    except Exception as e:
        await message.answer(f"⚠️ Ошибка при отправке картинки: {e}")

# ===================== Проверка слова =====================
@dp.message()
async def check_word(message: types.Message):
    word = message.text.strip().lower()
    words = load_words()

    if word in words:
        kb = InlineKeyboardBuilder()
        kb.button(text="🔗 Подписаться на канал", url=NEWS_CHANNEL_LINK)
        kb.button(text="✅ Проверить подписку", callback_data="checksub")
        kb.adjust(1)

        await message.answer(
            "✅ Код принят!\n"
            "Перед тем, как перейти к урокам, подпишись на наш официальный канал BRELKOF.\n"
            "Именно там будут все новости, розыгрыши, конкурсы и анонсы наборов!",
            reply_markup=kb.as_markup()
        )
    else:
        await message.answer("❌ Неверное слово. Попробуй ещё раз.")

# ===================== Callback: проверка подписки =====================
@dp.callback_query(F.data == "checksub")
async def checksub_callback(callback: types.CallbackQuery):
    try:
        chat_for_check = int(NEWS_CHANNEL_ID) if NEWS_CHANNEL_ID.startswith("-100") else NEWS_CHANNEL_ID

        member = await bot.get_chat_member(chat_id=chat_for_check, user_id=callback.from_user.id)
        status = getattr(member, "status", None)
        if status in ("member", "administrator", "creator"):
            kb_bingo = InlineKeyboardBuilder()
            kb_bingo.button(text="🎯 БИНГО", callback_data="bingo")
            kb_bingo.adjust(1)

            await callback.message.answer(
                "Спасибо тебе!\n"
                "А еще у нас есть БИНГО 🎉\n"
                "Выполняя задания, ты получишь скидку на следующий заказ.",
                reply_markup=kb_bingo.as_markup()
            )
            await callback.message.answer_photo(
                photo="https://placekitten.com/500/300",
                caption=(
                    "Я очень рада, что ты с нами!\nЖелаю тебе приятно провести это время)\n\n"
                    f"Вот твоя ссылка на инструкции: https://t.me/+EVFwvTKKwlJhOTNi"
                )
            )
        else:
            await callback.message.answer("❌ Ты еще не подписался на канал BRELKOF!")
    except Exception as e:
        await callback.message.answer(f"⚠️ Ошибка при проверке подписки: {e}")
    finally:
        try:
            await callback.answer()
        except Exception:
            pass

# Заглушка для бинго
@dp.callback_query(F.data == "bingo")
async def bingo_callback(callback: types.CallbackQuery):
    await callback.message.answer("🎯 Раздел БИНГО пока в разработке 😉")
    try:
        await callback.answer()
    except Exception:
        pass

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
    asyncio.create_task(start_web_app())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
