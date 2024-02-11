import telebot
from telebot import types
import requests
import sqlite3
from config import settings
import torch
from torchvision import transforms
import shutil
import subprocess
import os
import threading

bot = telebot.TeleBot(settings['TOKEN'])
imgbb_api_key = settings['IMG_TOKEN']

checkpoint = torch.load('/Users/denisbajramov/PycharmProjects/tgbot3/final_back/best.pt')
model = checkpoint['model']
model = model.to(torch.float)
model.eval()

preprocess = transforms.Compose([
    transforms.Resize((640, 640)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

lock = threading.Lock()
image_url = None

def create_database_connection():
    return sqlite3.connect('mollusk_database.db')


def initialize_database():
    conn = create_database_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS MolluskData (
            UserID INTEGER NOT NULL,
            PhotoData BLOB NOT NULL,
            Latitude REAL,
            Longitude REAL,
            ClassificationResult TEXT
        );
    ''')
    conn.commit()
    conn.close()


initialize_database()


def start_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton('Загрузить фотографию моллюска'))
    return markup


def geo_markup():
    markup_geo = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup_geo.add(types.KeyboardButton("Отмена"))
    markup_geo.add(types.KeyboardButton("Выбрать местоположение", request_location=True))
    return markup_geo


@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = start_markup()
    bot.reply_to(message, "Привет! Я бот для распознавания моллюсков по фотографиям. Пожалуйста, нажми кнопку ниже, чтобы загрузить фотографию моллюска.", reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == 'Загрузить фотографию моллюска')
def request_photo(message):
    markup = start_markup()
    bot.send_message(message.chat.id, "Загрузите фото моллюска, чтобы я смог его распознать.", reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == 'Отмена')
def cancel_operation(message):
    markup = start_markup()
    bot.send_message(message.chat.id, "Операция отменена.", reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == 'Выбрать местоположение')
def request_location(message):
    markup_geo = geo_markup()
    bot.send_message(message.chat.id, "Выберите местоположение.", reply_markup=markup_geo)


@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    global image_url  # Объявляем глобальную переменную

    try:
        # Блокируем доступ к обработке изображений, пока один из них не будет обработан
        lock.acquire()

        file_info = bot.get_file(message.photo[-1].file_id)
        file_path = file_info.file_path
        file_url = f'https://api.telegram.org/file/bot{settings["TOKEN"]}/{file_path}'
        response = requests.get(file_url)
        photo_data = response.content
        image_path = 'temp_image.jpg'

        with open(image_path, 'wb') as file:
            file.write(photo_data)

        command = f'yolo task=detect mode=predict model=/Users/denisbajramov/PycharmProjects/tgbot3/final_back/best.pt source={image_path}'
        start_command = subprocess.check_output(command, shell=True).decode("utf-8")
        result = '/Users/denisbajramov/PycharmProjects/tgbot3/final_back/runs/detect/predict/temp_image.jpg'

        with open(result, 'rb') as file:
            response = requests.post('https://api.imgbb.com/1/upload', files={'image': file}, data={'key': imgbb_api_key})

        image_url = response.json()['data']['url']

        bot.send_message(message.chat.id, f"Обработанное изображение: {image_url}")

        # Запрашиваем у пользователя местоположение
        markup_geo = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup_geo.add(types.KeyboardButton("Отправить местоположение", request_location=True))
        bot.send_message(message.chat.id, "Пожалуйста, отправьте местоположение, чтобы мы могли сохранить его в базе данных.", reply_markup=markup_geo)

        # Удаляем папку predict
        shutil.rmtree('/Users/denisbajramov/PycharmProjects/tgbot3/final_back/runs/detect/predict')

    except Exception as e:
        print(f"Ошибка при обработке фото: {e}")
        bot.reply_to(message, f"Ошибка обработки фотографии: {e}")

    finally:
        # После обработки изображения снимаем блокировку
        lock.release()


@bot.message_handler(content_types=['location'])
def handle_location(message):
    try:
        latitude = message.location.latitude
        longitude = message.location.longitude

        # Проверяем наличие URL изображения
        if image_url:
            conn = create_database_connection()
            cursor = conn.cursor()
            cursor.execute('INSERT INTO MolluskData (UserID, Latitude, Longitude, PhotoData) VALUES (?, ?, ?, ?)',
                           (message.from_user.id, latitude, longitude, image_url))  # Здесь используется переменная с URL изображения
            conn.commit()
            conn.close()

            bot.send_message(message.chat.id, "Местоположение успешно сохранено в базе данных.")
        else:
            bot.send_message(message.chat.id, "Ошибка: URL изображения не определен.")

    except Exception as e:
        print(f"Ошибка при сохранении местоположения: {e}")
        bot.reply_to(message, f"Ошибка сохранения местоположения: {e}")


if __name__ == "__main__":
    bot.polling()