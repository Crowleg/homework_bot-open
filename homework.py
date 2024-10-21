import logging
import os
import requests
import sys
import time

from dotenv import load_dotenv
from telebot import TeleBot, apihelper

from exception import (
    APIRequestException,
    SendMessageException,
    HomeworkStatusException,
    WrongStatusCode
)

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

logger = logging.getLogger(__name__)

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяет наличие всех токенов."""
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    missing_tokens = [name for name, token in tokens.items() if token is None]
    if missing_tokens:
        logger.critical(
            f'Отсутствуют следующие токены: {", ".join(missing_tokens)}'
        )
        return False
    return True


def send_message(bot, message):
    """Отправляет сообщение в Telegram."""
    logger.debug('Начало отправки сообщения.')
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
        logger.debug('Бот успешно отправил сообщение')
    except (apihelper.ApiException, requests.RequestException) as error:
        error_message = f'Ошибка при отправке сообщения: {error}'
        logger.error(error_message)
        raise SendMessageException(error_message)


def get_api_answer(timestamp):
    """Делает запрос к API."""
    request_kwargs = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': timestamp}
    }
    logger.debug(f'Запрос к API: {request_kwargs}')
    try:
        response = requests.get(**request_kwargs)
    except requests.RequestException as error:
        error_message = (
            f'Ошибка при запросе к API: {request_kwargs}. Ошибка: {error}'
        )
        logger.error(error_message)
        raise APIRequestException(error_message)
    if response.status_code != 200:
        raise WrongStatusCode(
            f'Эндпоинт недоступен. Код ответа:{response.status_code}'
        )
    return response.json()


def check_response(response):
    """Проверяет ответ API."""
    if not isinstance(response, dict):
        raise TypeError('Ответ API не словарь')
    if 'homeworks' not in response:
        raise KeyError('Отсутствует ключ "homeworks" в ответе API')
    if not isinstance(response['homeworks'], list):
        raise TypeError('homeworks должен быть списком')
    return response['homeworks']


def parse_status(homework):
    """Извлекает статус сданного проекта."""
    if not isinstance(homework, dict):
        raise TypeError('homework должен быть словарём')
    if 'status' not in homework:
        raise KeyError('Отсутствует ключ "status" в домашней работе')
    if 'homework_name' not in homework:
        raise KeyError('Отсутствует ключ "homework_name" в домашней работе')
    status = homework['status']
    if status not in HOMEWORK_VERDICTS:
        raise HomeworkStatusException(
            f'Неожиданный статус домашней работы: {status}'
        )
    verdict = HOMEWORK_VERDICTS.get(
        status
    )
    homework_name = homework['homework_name']
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def send_error_message(bot, error, last_error):
    """Отправляет сообщение об ошибке."""
    message_text = f'Сбой в работе программы: {error}'
    if message_text != last_error:
        try:
            send_message(bot, message_text)
            last_error = message_text
        except SendMessageException:
            logger.error('Не удалось отправить сообщение об ошибке.')
        logger.error(message_text)
    else:
        logger.debug(f'Ошибка повторяется: {message_text}')
    return last_error


def send_homework_status(bot, homeworks, last_homework):
    """Отправляет сообщение о статусе домашней работы."""
    homework = homeworks[0]
    message = parse_status(homework)
    if message != last_homework:
        send_message(bot, message)
        last_homework = message
    else:
        logger.debug('Повторяющееся сообщение не отправлено.')
    return last_homework


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        sys.exit('Отсутствуют токены.')
    bot = TeleBot(TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_message = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks:
                last_message = send_homework_status(
                    bot,
                    homeworks,
                    last_message
                )
            else:
                logger.debug('Новых статусов домашних работ нет.')
            timestamp = response.get('current_date', timestamp)
        except Exception as error:
            last_message = send_error_message(bot, error, last_message)
# Действительно, спасибо! Сначала запутался в целом с перехватом ошибок.
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s, %(levelname)s, %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    main()
