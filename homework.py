import logging
import os
import sys
import time

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 60 * 10
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)

logger = logging.getLogger(__name__)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)


def check_tokens():
    """Проверка наличия к окружении токенов и номера чата."""
    for token in [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]:
        if token is None or token == '':
            logging.critical('Отсутствует обязательная переменная окружения')
            sys.exit()


def send_message(bot, message):
    """Отправка сообщения в Telegram чат пользователю."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug('Сообщение отправлено в Telegram')
    except Exception:
        logging.error('Не удалось отправить сообщение в Telegram')


def get_api_answer(timestamp):
    """Отправка запроса к эндпоинту API-сервиса."""
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp - RETRY_PERIOD}
        )
    except Exception:
        logging.error(
            f'Сбой в работе программы: Эндпоинт {ENDPOINT} недоступен.'
            f'Код ответа API: {response.status_code}'
        )

    if response.status_code == 200:
        homework_data = response.json()
    else:
        logging.error('Неверно переданы значения токена/времени отсчета.'
                      f'Код ответа API: {response.status_code}')
        raise Exception()

    return homework_data


def check_response(response):
    """Проверка ответа API на соответствие документации."""
    try:
        homeworks = response['homeworks']
    except KeyError:
        logging.error('В ответе API отсутствует ключ <homeworks>')

    if homeworks == []:
        logging.debug('Статус по домашней работе не изменился')
    elif (
        type(homeworks) != list
        or type(homeworks[0]) != dict
        or type(response) != dict
    ):
        logging.error('Неожиданная структура данных о домашке в ответе API')
        raise TypeError('Неожиданная структура данных о домашке в ответе API')
    else:
        return parse_status(homeworks[0])


def parse_status(homework):
    """Извлечение статуса домашней работы."""
    try:
        homework_name = homework['homework_name']
        status = homework['status']
    except KeyError:
        logging.error('В ответе API домашки нет нужного ключа name/status')
    if status not in HOMEWORK_VERDICTS:
        raise Exception('Неожиданный статус домашки в ответе API')
    else:
        verdict = HOMEWORK_VERDICTS[status]
        logging.info('Изменился статус проверки работы')
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(timestamp)
            message = check_response(response)
            if message:
                send_message(bot, message)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
