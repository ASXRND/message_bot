import os
import requests


import requests_cache
import pandas as pd
from datetime import datetime
from openmeteo_requests import Client
import openmeteo_requests

import requests_cache
import pandas as pd
from retry_requests import retry

from tabulate import tabulate

from dotenv import load_dotenv

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
    print(f"Coordinates {response.Latitude()}°N {response.Longitude()}°E")
    print(f"Elevation {response.Elevation()} m asl")
    print(f"Timezone {response.Timezone()} {response.TimezoneAbbreviation()}")
    print(f"Timezone difference to GMT+0 {response.UtcOffsetSeconds()} s")

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
        # tablefmt="pipe",   # Markdown стиль таблицы
        tablefmt="grid",   # Используем формат grid для отображения в коде
        # numalign="right",  # Выравнивание чисел по правому краю
        stralign="left",   # Выравнивание строк по левому краю
        showindex=False    # Отключаем индексы
    )

    return table


def send_message(message):

    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_TOKEN')
    TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')

    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'

    params = {
        'chat_id': TELEGRAM_CHANNEL_ID,
        'text': f'{message}'
    }

    res = requests.post(url, params=params)
    res.raise_for_status()

    return res.json()


if __name__ == '__main__':
    weather = get_weather()
    print(weather)
    send_message(weather)
