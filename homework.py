# homework_bot/homework.py

import logging
import os
import time

import requests
import telegram

from dotenv import load_dotenv
from http.client import OK

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

RETRY_TIME = 60
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


class CustomError(Exception):
    """Кастомное исключение."""
    
    pass


def send_message(bot, message):
    """Отправка сообщений."""
    
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.info('Сообщение отправлено!')
    except telegram.error.TelegramError as error:
        logger.error(f'Ошибка: {error}')


def get_api_answer(current_timestamp):
    """Отправка запроса к эндпоинту API-сервиса."""
    
    timestamp = current_timestamp or int(time.time() - 2700000)
    params = {'from_date': timestamp}
    try:
        response = requests.get(url=ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != OK:
            message = 'Ошибка при получении ответа с сервера'
            logger.info(message)
            raise CustomError(message)
        logger.info('Соединение с сервером установлено!')
        return response.json()
    except requests.RequestException as request_error:
        message = f'Код ответа API (RequestException): {request_error}'
        logger.error(message)
        raise CustomError(message)
    except ValueError as value_error:
        message = f'Код ответа API (ValueError): {value_error}'
        logger.error(message)
        raise CustomError(message)


def parse_status(homework):
    """Парсировка статуса homework."""
    
    homework_name = homework.get('homework_name')
    if homework_name is None:
        raise KeyError('У homework нет имени')
    homework_status = homework.get('status')
    if homework_status is None:
        raise KeyError('У homework нет статуса')
    verdict = HOMEWORK_STATUSES.get(homework_status)
    if verdict is None:
        raise CustomError(f'Ошибка: {verdict}')
    logging.info(f'Новый статус {verdict}')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_response(response):
    """Проверка запроса."""
    
    homeworks = response['homeworks']
    if homeworks is None:
        raise KeyError("Не содержит ключ или пустое значение")
    if not isinstance(homeworks, list):
        raise TypeError("Неверный формат homework")
    if not homeworks:
        return False
    return homeworks


def check_tokens():
    """Проверка доступности переменных окружения."""
    
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота."""
    
    if not check_tokens():
        message = 'Отсутствует необходимая переменная среды'
        logger.critical(message)
        raise CustomError(message)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    errors = False
    while True:
        try:
            response = get_api_answer(current_timestamp)
            result = check_response(response)
            if result:
                message = parse_status(result)
                send_message(bot, message)
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if errors:
                errors = False
                send_message(bot, message)
            logger.critical(message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
