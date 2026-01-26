import asyncio
import logging
from bot import main as run_bot
from keep_alive import keep_alive

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

if __name__ == '__main__':
    print("=" * 50)
    print("AO3 Downloader Bot - запуск...")
    print("=" * 50)
    
    # Запускаем Flask сервер для keep-alive
    keep_alive()
    print("✅ Flask сервер запущен на порту 5000")
    print("📡 Доступен по адресу: http://localhost:5000")
    
    # Запускаем бота
    print("\n🤖 Запуск Telegram бота...")
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен")
    except Exception as e:
        print(f"\n💥 Ошибка: {e}")
