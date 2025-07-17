"""🔧 config.py — конфигурация из .env"""

import os
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

# Основные настройки
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "-1000000000000"))

# Пути по умолчанию
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEDIA_FOLDER = os.path.join(BASE_DIR, "../data")
DB_PATH = os.path.join(MEDIA_FOLDER, "data.sqlite")

# Проверка токена (опционально)
if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN не задан в .env")
