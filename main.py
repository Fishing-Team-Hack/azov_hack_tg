import telebot
from telebot import types
import json
import requests

from config import settings

bot = telebot.TeleBot(settings['TOKEN'])

def reply_keyboard(chat_id, text):
    keyboard = {
        "keyboard": [
            ["Привет", ""],
            [{"request_location": True, "text": "Где я нахожусь"}]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": True
    }

    reply_markup = json.dumps(keyboard)
    bot.send_message(chat_id, text, reply_markup=reply_markup)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton('Загрузить фотографию моллюска'))
    markup.add(types.KeyboardButton("Отправить местоположение 🌐", request_location=True))
    bot.reply_to(message, "Привет! Я бот для распознавания моллюсков по фотографиям. Пожалуйста, нажми кнопку ниже, чтобы загрузить фотографию моллюска или отправь мне своё местоположение.", reply_markup=markup)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    if message.text == 'Загрузить фотографию моллюска':
        bot.send_message(message.chat.id, "Пожалуйста, загрузи фотографию моллюска.")
    elif message.text == 'Отправить местоположение 🌐':
        reply_keyboard(message.chat.id, "Пожалуйста, отправь мне своё местоположение.")
    else:
        bot.reply_to(message, "Я понимаю только команду /start и кнопки 'Загрузить фотографию моллюска' и 'Отправить местоположение 🌐'.")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    try:
        # Получаем информацию о фотографии
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        file_url = f'https://api.telegram.org/file/bot{settings["TOKEN"]}/{file_info.file_path}'

        # Скачиваем фотографию
        with requests.get(file_url, stream=True) as r:
            r.raise_for_status()
            with open('photo.jpg', 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

        # Отправляем фотографию на сервер для обработки
        mollusk_name = process_photo('photo.jpg')

        # Отправляем результат пользователю
        bot.reply_to(message, f"Моллюск на фотографии: {mollusk_name}")

    except Exception as e:
        bot.reply_to(message, f"Ошибка обработки фотографии: {e}")

@bot.message_handler(content_types=['location'])
def handle_location(message):
    # Обрабатываем данные местоположения
    latitude = message.location.latitude
    longitude = message.location.longitude

    # Ваш код для обработки местоположения здесь
    # Например, можно использовать эти координаты для каких-то действий

    bot.reply_to(message, f"Спасибо за предоставленное местоположение: {latitude}, {longitude}")

def process_photo(photo_path):
    # Здесь должен быть ваш код для обработки фотографии с использованием нейронной сети
    # В данном примере мы просто возвращаем фиктивное название моллюска
    return "Dummy Mollusk"

if __name__ == "__main__":
    bot.polling()
