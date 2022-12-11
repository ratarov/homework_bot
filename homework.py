import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

import exceptions

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

logger = logging.getLogger(__name__)
my_homeworks = {}


def check_tokens():
    """Проверка наличия к окружении токенов и номера чата."""
    if not all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        logging.critical('Отсутствует обязательная переменная окружения')
        sys.exit('Программа принудительно остановлена.')


def send_message(bot, message):
    """Отправка сообщения в Telegram чат пользователю."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug('Сообщение отправлено в Telegram')
    except Exception:
        logging.error('Не удалось отправить сообщение в Telegram')


def get_api_answer(timestamp):
    """Отправка запроса к эндпоинту API-сервиса."""
    logging.debug('Отправляем запрос к эндпоинту API-сервиса')
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
        if response.status_code == HTTPStatus.OK:
            return response.json()
        else:
            raise exceptions.EndpointError(
                'Неверные значения токена/времени в запросе.'
                f'Код ответа API: {response.status_code}'
            )
    except Exception:
        raise exceptions.EndpointError(
            f'Эндпоинт {ENDPOINT} недоступен.'
            f'Код ответа API: {response.status_code}'
        )


def check_response(response):
    """Проверка ответа API на соответствие документации."""
    if 'homeworks' in response:
        homeworks = response['homeworks']
    else:
        raise TypeError('В ответе API отсутствует ключ <homeworks>')

    if not isinstance(homeworks, list):
        raise TypeError('Неожиданная структура данных о домашке в ответе API')
    else:
        return homeworks


def parse_status(homework):
    """Извлечение статуса домашней работы."""
    if 'homework_name' in homework and 'status' in homework:
        homework_name = homework['homework_name']
        status = homework['status']
    else:
        raise KeyError('В ответе API домашки нет нужного ключа name/status')

    if homework_name in my_homeworks and my_homeworks[homework_name] == status:
        logging.debug('Новый статус проверки не появился')
    else:
        my_homeworks[homework_name] = status
        if status not in HOMEWORK_VERDICTS:
            raise KeyError('Статус домашки в ответе API отсутвует в словаре')
        else:
            verdict = HOMEWORK_VERDICTS[status]
            logging.info('Изменился статус проверки работы')
            return (f'Изменился статус проверки работы "{homework_name}". '
                    f'{verdict}')


def main():
    """Основная логика работы бота."""
    logging.basicConfig(
        format='%(asctime)s - %(levelname)s - %(message)s - func %(funcName)s',
        level=logging.DEBUG,
    )
    handler = logging.StreamHandler(stream=sys.stdout)
    logger.addHandler(handler)

    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks == []:
                logging.debug('Новый статус проверки не появился')
            else:
                message = parse_status(homeworks[0])
                if message:
                    send_message(bot, message)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
