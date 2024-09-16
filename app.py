import os
import requests
import requests_cache
import pandas as pd
from datetime import datetime
from openmeteo_requests import Client
import openmeteo_requests
import pandas as pd
from retry_requests import retry
from tabulate import tabulate
from dotenv import load_dotenv
import openmeteo_requests
from retry_requests import retry
from tabulate import tabulate

load_dotenv()


def format_numbers(df, column_width=2):
    """Форматирует числа с одинаковым количеством отступов."""
    df = df.copy()  # Создаем копию DataFrame
    for col in df.select_dtypes(include=['number']).columns:
        df[col] = df[col].apply(
            lambda x: f"{x:>{column_width}.3f}")  # Форматируем числа
    return df


def get_weather():
    # Setup the Open-Meteo API client with cache and retry on error
    cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = Client(session=retry_session)

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": 47.2227,
        "longitude": 39.7165,
        "hourly": "temperature_2m",
        "daily": "weather_code",
        "timezone": "Europe/Moscow",
        "forecast_days": 1
    }
    responses = openmeteo.weather_api(url, params=params)

    response = responses[0]

    hourly = response.Hourly()
    hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()

    hourly_data = {"Дата": pd.date_range(
        start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
        end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
        freq=pd.Timedelta(seconds=hourly.Interval()),
        inclusive="right"
    )}

    # Форматируем дату и время без временной зоны
    hourly_data["Дата"] = hourly_data["Дата"].map(
        lambda x: x.strftime("%Y-%m-%d %H:%M"))

    hourly_data["Ростов-На-Дону"] = hourly_temperature_2m

    # Создаем DataFrame
    hourly_dataframe = pd.DataFrame(data=hourly_data)

   # Форматируем числовые значения с одинаковым количеством отступов
    hourly_dataframe = format_numbers(hourly_dataframe)

    # Используем tabulate для красивого форматирования таблицы без индексов
    table = tabulate(
        hourly_dataframe,
        headers="keys",
        tablefmt="grid",   # Используем формат grid для отображения в коде
        stralign="left",   # Выравнивание строк по левому краю
        showindex=False    # Отключаем индексы
    )

    return table


def get_news_for_telegram():
    # Ваш API ключ от NewsAPI
    API_KEY = os.getenv('NEWS_APIKEY')

    # Получаем сегодняшнюю дату в формате 'YYYY-MM-DD'
    today_date = datetime.today().strftime('%Y-%m-%d')

    # URL для запроса
    url = 'https://newsapi.org/v2/everything'
    '2024-09-01'

    # Параметры запроса
    params = {
        'q': 'технологии',          # Поиск по ключевому слову
        'from': '2024-09-15',       # Диапазон поиска
        'language': 'ru',           # Новости на русском языке
        'sortBy': 'popularity',     # Сортировка по популярности
        'apiKey': API_KEY           # Ваш API-ключ
    }

    # Выполнение запроса
    response = requests.get(url, params=params)

    # Проверка статуса запроса
    if response.status_code == 200:
        news_data = response.json()
        if news_data['totalResults'] > 0:
            # Формируем текст для отправки в Telegram
            telegram_message = ""
            for i, article in enumerate(news_data['articles'], 1):
                title = article['title']
                description = article['description'] or 'Описание отсутствует'
                url = article['url']
                telegram_message += f"📰 <b>{i}. {title}</b>\n{
                    description}\n<a href='{url}'>Читать далее</a>\n\n"

            # Ограничиваем длину до 4000 символов
            return telegram_message.strip()[:4000]
        else:
            return "Нет результатов по данному запросу."
    else:
        return f"Ошибка: {response.status_code}"


def send_message(message):
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_TOKEN')
    TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')

    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'

    params = {
        'chat_id': TELEGRAM_CHANNEL_ID,
        'text': message,
        'parse_mode': 'HTML'  # Указываем HTML, чтобы поддерживать форматирование
    }

    res = requests.post(url, params=params)
    res.raise_for_status()

    return res.json()


if __name__ == '__main__':
    news = get_news_for_telegram()  # Получаем новости
    weather = get_weather()         # Получаем погоду

    # Упрощаем таблицу и делаем её текстом
    weather_message = f"<b>🌤️ Погода на сегодня:</b>\n{weather}"

    # Проверяем, если новостей нет
    if not news:
        news = "Нет свежих новостей на данный момент."

    # Объединяем погоду и новости в одно сообщение
    combined_message = f"{weather_message}\n\n<b>📰 Новости:</b>\n\n{news}"

    # Ограничиваем размер сообщения (Telegram может ограничивать длину)
    if len(combined_message) > 4096:
        combined_message = combined_message[:4093] + "..."

    # Отправляем сообщение в Telegram
    send_message(combined_message)
