
import sqlite3
from telebot import TeleBot, types

bot = TeleBot('8421507526:AAHq5MYaNPOQVYHAYvWbAR9fQkl6ZZRpST8')

# Создаем базу данных для хранения кодовых слов и ссылок
def init_db():
    conn = sqlite3.connect('brelkof.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS codes
                 (id INTEGER PRIMARY KEY, code TEXT UNIQUE, link TEXT)''')
    conn.commit()
    conn.close()

# Функция проверки подписки (у вас уже есть, оставляем)
def check_subscription(user_id):
    try:
        chat_member = bot.get_chat_member('@brelkof_news', user_id)
        return chat_member.status in ['member', 'administrator', 'creator']
    except:
        return False

# Добавляем кодовое слово и ссылку в базу
def add_code_word(code, link):
    conn = sqlite3.connect('brelkof.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO codes (code, link) VALUES (?, ?)", (code, link))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # если код уже существует
    finally:
        conn.close()

# Получаем ссылку по кодовому слову
def get_link_by_code(code):
    conn = sqlite3.connect('brelkof.db')
    c = conn.cursor()
    c.execute("SELECT link FROM codes WHERE code = ?", (code,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup()
    channel_btn = types.InlineKeyboardButton("Подписаться на канал", url="https://t.me/brelkof_news")
    check_btn = types.InlineKeyboardButton("✅ Проверить подписку", callback_data="check_subscription")
    markup.add(channel_btn, check_btn)
    
    bot.send_message(message.chat.id, 
                    "Добро пожаловать в бот brelkof! 🧶\n\n"
                    "После покупки набора для вязания:\n"
                    "1. Подпишитесь на наш новостной канал\n"
                    "2. Введите кодовое слово из набора\n"
                    "3. Получите ссылку на видео-инструкцию",
                    reply_markup=markup)

# Обработчик проверки подписки
@bot.callback_query_handler(func=lambda call: call.data == "check_subscription")
def check_subscription_callback(call):
    user_id = call.from_user.id
    if check_subscription(user_id):
        bot.send_message(call.message.chat.id, 
                        "✅ Отлично! Вы подписаны на канал.\n\n"
                        "Теперь введите кодовое слово из вашего набора:")
    else:
        bot.send_message(call.message.chat.id, 
                        "❌ Вы еще не подписаны на канал. Пожалуйста, подпишитесь и попробуйте снова.")

# Обработчик текстовых сообщений (кодовых слов)
@bot.message_handler(content_types=['text'])
def handle_code_word(message):
    user_id = message.from_user.id
    
    # Проверяем подписку
    if not check_subscription(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Подписаться на канал", url="https://t.me/brelkof_news"))
        bot.send_message(message.chat.id, 
                        "❌ Для получения доступа к инструкциям необходимо подписаться на наш канал.",
                        reply_markup=markup)
        return
    
    # Проверяем кодовое слово
    code = message.text.strip().lower()
    link = get_link_by_code(code)
    
    if link:
        bot.send_message(message.chat.id, 
                        f"🎉 Отлично! Вот ваша ссылка на видео-инструкцию:\n{link}\n\n"
                        f"Приятного вязания! 🧶")
    else:
        bot.send_message(message.chat.id, 
                        "❌ Кодовое слово не найдено. Пожалуйста, проверьте правильность ввода.\n"
                        "Кодовое слово указано в вашем наборе для вязания.")

# Команда для администратора чтобы добавить новые кодовые слова
@bot.message_handler(commands=['add_code'])
def add_code_command(message):
    # Проверяем, является ли пользователь администратором
    if message.from_user.id != 410300780:  # Замените на ID администратора
        return
    
    try:
        _, code, link = message.text.split(' ', 2)
        if add_code_word(code.lower(), link):
            bot.send_message(message.chat.id, f"✅ Код '{code}' добавлен!")
        else:
            bot.send_message(message.chat.id, "❌ Ошибка: такой код уже существует")
    except ValueError:
        bot.send_message(message.chat.id, "Использование: /add_code <кодовое_слово> <ссылка>")

# Инициализируем базу данных при запуске
init_db()

# Добавляем пример кодового слова (можно удалить после тестирования)
add_code_word("вяжем2024", "https://t.me/brelkof_channel/1")

bot.polling()