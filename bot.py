import os
import json
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# ===================== Настройки =====================
API_TOKEN = os.getenv("API_TOKEN")  # токен бота из переменной окружения
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "-1001234567890"))  # ID канала
ADMINS = list(map(int, os.getenv("ADMINS", "").split(",")))  # список ID админов через запятую

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
    await message.answer("Привет! Введите секретное слово, чтобы получить доступ.")


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


@dp.message(Command("delword"))
async def del_word(message: types.Message):
    if message.from_user.id not in ADMINS:
        return await message.answer("⛔ У вас нет прав.")
    parts = message.text.split()
    if len(parts) != 2:
        return await message.answer("Использование: /delword <слово>")
    word = parts[1].strip().lower()
    words = load_words()
    if word not in words:
        return await message.answer("⚠️ Такого слова нет.")
    words.remove(word)
    save_words(words)
    await message.answer(f"🗑 Слово '{word}' удалено.")


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
    await message.answer(f"ℹ️ Chat ID этого чата: `{message.chat.id}`", parse_mode="Markdown")


@dp.message()
async def check_word(message: types.Message):
    word = message.text.strip().lower()
    words = load_words()

    if word in words:
        # создаем одноразовую ссылку
        invite = await bot.create_chat_invite_link(
            chat_id=CHANNEL_ID,
            member_limit=1
        )
        await message.answer(
            f"✅ Секретное слово верное!\nВот ваша одноразовая ссылка: {invite.invite_link}"
        )
    else:
        await message.answer("❌ Неверное слово. Попробуйте ещё раз.")


# ===================== Запуск =====================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
