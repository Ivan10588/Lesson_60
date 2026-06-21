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

