"""
Скрипт проверки доступности веб-сайтов.

Функционал:
- Читает URL из файла (--file) или аргументов командной строки.
- Выполняет HEAD (если сервер разрешает), иначе GET.
- Использует таймаут (--timeout, по умолчанию 5 сек).
- Логирует в консоль и CSV: URL, статус-код, время ответа (мс), статус (UP/DOWN), время проверки.
- Обрабатывает сетевые ошибки и таймауты.
"""

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path

import requests
from requests.exceptions import RequestException, Timeout, ConnectionError

def parse_args():
    """Парсинг аргументов командной строки."""
    parser = argparse.ArgumentParser(
        description="Проверка доступности веб-сайтов"
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
        "--output",
        type=str,
        default="availability_log.csv",
        help="Имя CSV-файла для записи результатов (по умолчанию: availability_log.csv)"
    )
    return parser.parse_args()

def read_urls_from_file(file_path: str):
    """Чтение URL из текстового файла, игнорируя пустые строки и комментарии (#)."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Файл не найден: {file_path}")
    urls = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            urls.append(line)
    if not urls:
        raise ValueError("В файле нет валидных URL.")
    return urls

def check_website(url: str, timeout: int) -> dict:
    """
    Проверка доступности одного сайта.

    Возвращает словарь с полями:
      - url
      - status_code
      - response_time_ms
      - status ("UP" / "DOWN")
      - timestamp
      - error (опционально, сообщение об ошибке)
    """
    result = {
        "url": url,
        "status_code": None,
        "response_time_ms": None,
        "status": "DOWN",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "error": None,
    }

    try:
        response = None
        for method in (requests.head, requests.get):
            try:
                response = method(url, timeout=timeout, allow_redirects=True)
                break
            except RequestException:
                continue

        if response is None:
            raise RequestException("Не удалось выполнить ни HEAD, ни GET запрос")

        result["status_code"] = response.status_code
        result["response_time_ms"] = round(response.elapsed.total_seconds() * 1000, 2)
        if 200 <= response.status_code < 300:
            result["status"] = "UP"
        else:
            result["status"] = "DOWN"

    except Timeout as e:
        result["error"] = f"Timeout: {e}"
    except ConnectionError as e:
        result["error"] = f"ConnectionError: {e}"
    except RequestException as e:
        result["error"] = f"RequestException: {e}"

    return result

