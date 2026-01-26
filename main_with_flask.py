import asyncio
from aiogram_bot import main as run_bot
from keep_alive import keep_alive
import logging

logging.basicConfig(level=logging.INFO)

if __name__ == '__main__':
    # Запускаем Flask сервер для keep-alive
    keep_alive()
    print("🌐 Flask сервер запущен на порту 5000")

    # Запускаем бота
    asyncio.run(run_bot())