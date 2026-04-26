import telebot
import json
import os
from datetime import datetime
import requests

TOKEN = "your_token"

PROXY = "socks5://user:pass@ip:port"

session = requests.Session()
session.proxies = {
    "http": PROXY,
    "https": PROXY
}

telebot.apihelper.SESSION = session

bot = telebot.TeleBot(TOKEN)

DATA_FILE = "products.json"


def load_products():
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []


def save_products(products):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=2)


@bot.message_handler(commands=['start'])
def start(message):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        telebot.types.KeyboardButton('➕ Добавить'),
        telebot.types.KeyboardButton('📋 Список'),
        telebot.types.KeyboardButton('⚠️ Проверить'),
        telebot.types.KeyboardButton('🗑 Удалить')
    )
    bot.send_message(message.chat.id, "🥶 Привет! Это твой холодильник", reply_markup=markup)


user_temp = {}

@bot.message_handler(func=lambda m: m.text == '➕ Добавить')
def add_start(message):
    msg = bot.send_message(message.chat.id, "Введите название продукта:")
    bot.register_next_step_handler(msg, get_name)


def get_name(message):
    user_temp[message.chat.id] = {"name": message.text}
    msg = bot.send_message(message.chat.id, "Введите ДЕНЬ (например 05):")
    bot.register_next_step_handler(msg, get_day)


def get_day(message):
    if not message.text.isdigit():
        return bot.send_message(message.chat.id, "❌ День должен быть числом")

    user_temp[message.chat.id]["day"] = message.text
    msg = bot.send_message(message.chat.id, "Введите МЕСЯЦ (например 12):")
    bot.register_next_step_handler(msg, get_month)


def get_month(message):
    if not message.text.isdigit():
        return bot.send_message(message.chat.id, "❌ Месяц должен быть числом")

    user_temp[message.chat.id]["month"] = message.text
    msg = bot.send_message(message.chat.id, "Введите ГОД (например 2025):")
    bot.register_next_step_handler(msg, get_year)


def get_year(message):
    if not message.text.isdigit():
        return bot.send_message(message.chat.id, "❌ Год должен быть числом")

    data = user_temp.get(message.chat.id)

    try:
        day = int(data["day"])
        month = int(data["month"])
        year = int(message.text)

        date_obj = datetime(year, month, day)
        date_str = date_obj.strftime("%Y-%m-%d")

        products = load_products()
        products.append({
            "name": data["name"],
            "date": date_str
        })
        save_products(products)

        bot.send_message(
            message.chat.id,
            f"✅ Добавлено: {data['name']} до {date_str}"
        )

        user_temp.pop(message.chat.id, None)

    except Exception:
        bot.send_message(message.chat.id, "❌ Неверная дата!")


@bot.message_handler(func=lambda m: m.text == '📋 Список')
def show_list(message):
    products = load_products()

    if not products:
        bot.send_message(message.chat.id, "🍃 Холодильник пуст")
        return

    text = "📋 Твои продукты:\n"
    for i, p in enumerate(products, 1):
        text += f"{i}. {p['name']} — до {p['date']}\n"

    bot.send_message(message.chat.id, text)


@bot.message_handler(func=lambda m: m.text == '⚠️ Проверить')
def check(message):
    products = load_products()
    today = datetime.now().date()

    expired = []
    for p in products:
        try:
            exp_date = datetime.strptime(p['date'], "%Y-%m-%d").date()
            if exp_date < today:
                expired.append(p)
        except:
            continue

    if expired:
        text = "⚠️ Просрочено:\n"
        text += "\n".join([f"- {p['name']}" for p in expired])
    else:
        text = "✅ Всё свежее!"

    bot.send_message(message.chat.id, text)


delete_temp = {}

@bot.message_handler(func=lambda m: m.text == '🗑 Удалить')
def delete_start(message):
    products = load_products()

    if not products:
        bot.send_message(message.chat.id, "❌ Список пуст")
        return

    text = "Выбери номер продукта для удаления:\n"
    for i, p in enumerate(products, 1):
        text += f"{i}. {p['name']} — до {p['date']}\n"

    msg = bot.send_message(message.chat.id, text)
    bot.register_next_step_handler(msg, delete_choose)


def delete_choose(message):
    if not message.text.isdigit():
        return bot.send_message(message.chat.id, "❌ Введи число")

    index = int(message.text) - 1
    products = load_products()

    if index < 0 or index >= len(products):
        return bot.send_message(message.chat.id, "❌ Нет такого номера")

    delete_temp[message.chat.id] = index
    product = products[index]

    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("✅ Да", "❌ Нет")

    msg = bot.send_message(
        message.chat.id,
        f"Удалить {product['name']} (до {product['date']})?",
        reply_markup=markup
    )
    bot.register_next_step_handler(msg, delete_confirm)


def delete_confirm(message):
    if message.text == "✅ Да":
        index = delete_temp.get(message.chat.id)
        products = load_products()

        if index is not None and 0 <= index < len(products):
            removed = products.pop(index)
            save_products(products)

            bot.send_message(
                message.chat.id,
                f"🗑 Удалено: {removed['name']}",
                reply_markup=telebot.types.ReplyKeyboardRemove()
            )
        else:
            bot.send_message(message.chat.id, "❌ Ошибка удаления")

    else:
        bot.send_message(
            message.chat.id,
            "❌ Удаление отменено",
            reply_markup=telebot.types.ReplyKeyboardRemove()
        )

    delete_temp.pop(message.chat.id, None)


print("Бот запущен!")
bot.infinity_polling()