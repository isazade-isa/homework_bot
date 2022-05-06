# homework_bot/homework.py

import json
import logging
import os
import time
from typing import Dict

import requests
import telegram

from dotenv import load_dotenv
from http.client import OK
import exception

logging.basicConfig(
    level=logging.INFO,
    filename='main.log',
    format='%(asctime)s, %(levelname)s, %(message)s',
    filemode='a',
)
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
TWO_WEEKS = 1209600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправка сообщений."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.info('Сообщение отправлено!')
    except telegram.error.TelegramError as error:
        logger.error(f'Ошибка: {error}')
        message = 'Ошибка отправки сообшения!'
        raise exception.NotSendMessageError(message)


def get_api_answer(current_timestamp):
    """Отправка запроса к эндпоинту API-сервиса."""
    params = {'from_date': current_timestamp}
    try:
        response = requests.get(url=ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != OK:
            message = 'Ошибка при получении ответа с сервера'
            raise exception.NonStatusCodeError(message)
        logger.info('Соединение с сервером установлено!')
        return response.json()
    except json.decoder.JSONDecodeError:
        raise exception.JSonDecoderError('Ошибка преобразования в JSON')
    except requests.RequestException as request_error:
        message = f'Код ответа API (RequestException): {request_error}'
        raise exception.WrongStatusCodeError(message)
    except ValueError as value_error:
        message = f'Код ответа API (ValueError): {value_error}'
        raise exception.WrongStatusCodeError(message)


def check_response(response):
    """Проверка запроса."""
    try:
        homeworks = response['homeworks']
    except KeyError:
        logger.error('Отсутствует ключ у homeworks')
        raise KeyError('Отсутствует ключ у homeworks')
    if homeworks is None:
        raise KeyError("Не содержит ключ или пустое значение")
    if not isinstance(homeworks, list):
        raise TypeError("Неверный формат homework")
    if not homeworks:
        return False
    return homeworks


def parse_status(homework):
    """Парсировка статуса homework."""
    if not isinstance(homework, Dict):
        raise TypeError("homework не является словарем!")
    homework_name = homework.get('homework_name')  # если я правильно понял :)
    if homework_name is None:
        raise KeyError('У homework нет имени')
    homework_status = homework.get('status')
    if homework_status is None:
        raise KeyError('У homework нет статуса')
    verdict = HOMEWORK_STATUSES.get(homework_status)
    if verdict is None:
        raise KeyError(f'Ошибка статуса homework : {verdict}')
    logging.info(f'Новый статус {verdict}')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка доступности переменных окружения."""
    if all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        return True
    # правильно ли я сделал этот пункт? а то есть сомнения небольшие )
    elif PRACTICUM_TOKEN is None:
        logger.info('Отсутствует PRACTICUM_TOKEN')
        return False
    elif TELEGRAM_TOKEN is None:
        logger.info('Отсутствует TELEGRAM_TOKEN')
        return False
    elif TELEGRAM_CHAT_ID is None:
        logger.info('Отсутствует TELEGRAM_CHAT_ID')
        return False


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        message = 'Отсутствует необходимая переменная среды'
        logger.critical(message)
        raise exception.NonTokenError(message)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time() - TWO_WEEKS)
    prev_msg = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            statuses = check_response(response)
            for status in statuses:
                message = parse_status(status)
                send_message(bot, message)
            current_timestamp = response.get('current_date', current_timestamp)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(error)
            if message != prev_msg:
                send_message(bot, message)
                prev_msg = message  # тут у меня ошибка была, вчера
                # после отправки на ревью заметил и исправил )
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
