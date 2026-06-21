"""
Скрипт проверки доступности веб-сайтов с расписанием, историей статусов и алертами.

Функционал:
- Читает URL из файла (--file) или аргументов командной строки.
- Выполняет HEAD (если сервер разрешает), иначе GET.
- Использует таймаут (--timeout, по умолчанию 5 сек).
- Запускает проверки по расписанию (--interval-minutes, по умолчанию 5 минут).
- Логирует в CSV (--log-file, по умолчанию availability_log.csv).
- Хранит историю статусов в status_history.json.
- При изменении статуса пишет в status_changes.log и выводит в консоль.
- Обрабатывает сетевые ошибки и таймауты.
"""

import argparse
import csv
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from requests.exceptions import RequestException, Timeout, ConnectionError


def parse_args():
    parser = argparse.ArgumentParser(
        description="Проверка доступности веб-сайтов по расписанию"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--file",
        type=str,
        help="Путь к файлу со списком URL (по одному на строку)"
    )
    group.add_argument(
        "urls",
        nargs="*",
        help="Список URL для проверки (передаются как аргументы)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=5,
        help="Таймаут запроса в секундах (по умолчанию: 5)"
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default="availability_log.csv",
        help="Имя CSV-файла для записи результатов (по умолчанию: availability_log.csv)"
    )
    parser.add_argument(
        "--interval-minutes",
        type=int,
        default=5,
        help="Интервал между проверками в минутах (по умолчанию: 5). Если 0 — однократная проверка."
    )
    parser.add_argument(
        "--history-file",
        type=str,
        default="status_history.json",
        help="Файл для хранения истории статусов (по умолчанию: status_history.json)"
    )
    parser.add_argument(
        "--changes-log",
        type=str,
        default="status_changes.log",
        help="Файл для записи изменений статуса (по умолчанию: status_changes.log)"
    )
    return parser.parse_args()

