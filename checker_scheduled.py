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

def read_urls_from_file(file_path: str):
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

def load_history(filepath: str) -> dict:
    """Загружает историю статусов из JSON. Если файла нет — возвращает пустой dict."""
    path = Path(filepath)
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

def save_history(filepath: str, history: dict):
    """Сохраняет историю статусов в JSON (перезаписывает файл)."""
    with open(filepath, "w", encoding="utf-8", newline="") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def log_change(changes_file: str, url: str, old_status: str | None, new_status: str, timestamp: str):
    """Записывает изменение статуса в лог изменений и выводит в консоль."""
    message = f"[{timestamp}] ALERT: Status of {url} changed from {old_status} to {new_status}"
    print(message)
    with open(changes_file, "a", encoding="utf-8") as f:
        f.write(message + "\n")

def check_website(url: str, timeout: int) -> dict:
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

def write_csv_header(filepath: str):
    file_exists = Path(filepath).exists()
    with open(filepath, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow([
                "URL", "StatusCode", "ResponseTimeMs", "Status", "Timestamp"
            ])

def log_to_console(result: dict):
    status_code = result["status_code"] if result["status_code"] is not None else "N/A"
    response_time = result["response_time_ms"] if result["response_time_ms"] is not None else "N/A"
    print(
        f"{result['url']} - Status Code: {status_code}, "
        f"Time: {response_time}ms, Overall Status: {result['status']}"
    )
    if result["error"]:
        print(f"  └─ Ошибка: {result['error']}")


def run_single_check(args, history: dict) -> dict:
    """Выполняет одну итерацию проверки всех URL и обновляет историю."""
    if args.file:
        urls = read_urls_from_file(args.file)
    else:
        urls = args.urls

    if not urls:
        print("Ошибка: не предоставлено ни одного URL для проверки.")
        sys.exit(1)

    write_csv_header(args.log_file)

    current_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for url in urls:
        result = check_website(url, args.timeout)
        log_to_console(result)

        with open(args.log_file, "a", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                result["url"],
                result["status_code"],
                result["response_time_ms"],
                result["status"],
                result["timestamp"],
            ])

        old_status = history.get(url)
        new_status = result["status"]

        if old_status is not None and old_status != new_status:
            log_change(args.changes_log, url, old_status, new_status, current_timestamp)

        history[url] = new_status

    save_history(args.history_file, history)
    return history

def main():
    args = parse_args()

    history = load_history(args.history_file)

    if args.interval_minutes == 0:
        run_single_check(args, history)
        return

    print(f"Запуск проверки по расписанию: каждые {args.interval_minutes} мин. Ctrl+C для остановки.")
    while True:
        try:
            history = run_single_check(args, history)
            print(f"Следующая проверка через {args.interval_minutes} минут...\n")
            time.sleep(args.interval_minutes * 60)
        except KeyboardInterrupt:
            print("\nОстановка по запросу пользователя.")
            break
        except Exception as e:
            print(f"Неожиданная ошибка в цикле: {e}")
            time.sleep(args.interval_minutes * 60)


if __name__ == "__main__":
    main()