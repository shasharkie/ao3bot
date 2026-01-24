import logging
import requests
import os
import tempfile
import re
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from urllib.parse import urlparse

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)

BOT_TOKEN = "8256763899:AAGB3QTtW2lpqYOzd0BXwdZ5LfRzzDo8lN8"
AO3_BASE_URL = "https://archiveofourown.gay"

# Flask app для поддержания активности
app = Flask('')

@app.route('/')
def home():
    return "I'm alive"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()

class AO3Downloader:

    @staticmethod
    def extract_work_id(url):
        """Извлекает ID работы из URL AO3"""
        try:
            logging.info(f"🔍 Анализируем URL: {url}")
            url = url.strip()

            url = url.replace('archiveofourown.org', 'archiveofourown.gay')

            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url

            parsed = urlparse(url)
            path_parts = parsed.path.split('/')

            if 'works' in path_parts:
                work_index = path_parts.index('works')
                if work_index + 1 < len(path_parts):
                    work_id = path_parts[work_index + 1]
                    work_id = work_id.split('?')[0].split('#')[0]

                    if work_id.isdigit():
                        logging.info(f"✅ Корректный цифровой ID: {work_id}")
                        return work_id
            return None
        except Exception as e:
            logging.error(f"💥 Ошибка извлечения ID: {e}")
            return None

    @staticmethod
    def get_work_title(work_id):
        """Получает название фанфика из HTML страницы"""
        try:
            work_url = f"{AO3_BASE_URL}/works/{work_id}"
            logging.info(f"📖 Получаю название фанфика: {work_url}")

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            }

            response = requests.get(work_url, headers=headers, timeout=15)

            if response.status_code == 200:
                title_patterns = [
                    r'<h2 class="title">([^<]+)</h2>',
                    r'<h2 class="title heading">([^<]+)</h2>',
                    r'<title>([^<]+) - Works</title>',
                    r'property="og:title" content="([^"]+)"'
                ]

                for pattern in title_patterns:
                    matches = re.findall(pattern, response.text)
                    if matches:
                        title = matches[0].strip()
                        title = re.sub(r'[<>:"/\\|?*]', '', title)
                        title = title.replace('&amp;', 'and').replace('&', 'and')
                        title = title.strip()

                        if title and len(title) > 1:
                            logging.info(f"✅ Название фанфика: {title}")
                            return title

            logging.warning("❌ Не удалось найти название фанфика")
            return None

        except Exception as e:
            logging.error(f"💥 Ошибка при получении названия: {e}")
            return None

    @staticmethod
    def get_epub_download_url(work_id):
        """Получает прямую ссылку для скачивания EPUB"""
        try:
            work_url = f"{AO3_BASE_URL}/works/{work_id}?view_adult=true"
            logging.info(f"🌐 Получаю информацию о фанфике: {work_url}")

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            }

            session = requests.Session()
            session.headers.update(headers)

            response = session.get(work_url, timeout=15)

            if response.status_code == 200:
                epub_patterns = [
                    r'href="(/downloads/' + work_id + r'/[^"]+\.epub[^"]*)"',
                    r'href="([^"]*downloads/' + work_id + r'[^"]*\.epub[^"]*)"'
                ]

                for pattern in epub_patterns:
                    matches = re.findall(pattern, response.text)
                    if matches:
                        download_path = matches[0]
                        if download_path.startswith('http'):
                            download_url = download_path
                        else:
                            download_url = f"{AO3_BASE_URL}{download_path}"
                        logging.info(f"✅ Найдена ссылка в HTML: {download_url}")
                        return download_url

            manual_url = f"{AO3_BASE_URL}/downloads/{work_id}/download.epub"
            logging.info(f"🔄 Пробую стандартную ссылку: {manual_url}")
            return manual_url

        except requests.exceptions.Timeout:
            logging.error("⏰ Таймаут при получении информации")
            return f"{AO3_BASE_URL}/downloads/{work_id}/download.epub"
        except Exception as e:
            logging.error(f"💥 Ошибка при получении ссылки: {e}")
            return f"{AO3_BASE_URL}/downloads/{work_id}/download.epub"

    @staticmethod
    def download_epub(work_id):
        """Скачивает EPUB файл и возвращает путь и название"""
        try:
            work_title = AO3Downloader.get_work_title(work_id)
            epub_url = AO3Downloader.get_epub_download_url(work_id)
            logging.info(f"📥 Скачиваю: {epub_url}")

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/epub+zip, application/octet-stream, */*',
                'Referer': f'{AO3_BASE_URL}/works/{work_id}',
            }

            response = requests.get(epub_url, headers=headers, stream=True, timeout=60)
            logging.info(f"📥 Ответ сервера: {response.status_code}")

            if response.status_code == 200:
                file_size = int(response.headers.get('content-length', 0))
                logging.info(f"📊 Размер файла: {file_size} байт")

                with tempfile.NamedTemporaryFile(delete=False, suffix='.epub') as temp_file:
                    downloaded_size = 0
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            temp_file.write(chunk)
                            downloaded_size += len(chunk)

                    logging.info(f"💾 Файл сохранен, скачано: {downloaded_size} байт")

                    if downloaded_size < 1000:
                        logging.error(f"❌ Файл слишком маленький: {downloaded_size} байт")
                        os.unlink(temp_file.name)
                        return None, None

                    if work_title:
                        clean_title = re.sub(r'[<>:"/\\|?*]', '', work_title)
                        clean_title = clean_title.replace(' ', '_').replace('__', '_')
                        clean_title = clean_title[:100]
                        filename = f"{clean_title}.epub"
                    else:
                        filename = f"ao3_work_{work_id}.epub"

                    return temp_file.name, filename

            else:
                logging.error(f"❌ Ошибка HTTP при скачивании: {response.status_code}")
                return None, None

        except requests.exceptions.Timeout:
            logging.error("⏰ Таймаут при скачивании файла")
            return None, None
        except Exception as e:
            logging.error(f"💥 Ошибка при скачивании: {e}")
            return None, None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    welcome_text = """здравствуй! 

этот бот предназначен для скачивания фанфиков с сайта archive of our own в формате epub

🔗 принимаются ссылки с сайтов:
• archiveofourown.org
• archiveofourown.gay

📄 итоговый формат файла: 
• epub

бот скачает любой фанфик
пришли ссылку и бот отправит тебе файл с фанфиком! 

—————————-

hi! this bot can help you download a fanfiction from the website "archive of our own" in epub file format

🔗links from the following websites are accepted:
• archiveofourown.org
• archiveofourown.gay

📄 final file format:
• epub

bot can  download any fanfiction 
send a link and bot will give you the file with your chosen fanfiction!"""

    await update.message.reply_text(welcome_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    user_message = update.message.text.strip()
    logging.info(f"📨 Получено сообщение: {user_message}")

    if ('archiveofourown.org' in user_message or 'archiveofourown.gay' in user_message) and '/works/' in user_message:
        await update.message.reply_text("🔍 Анализирую ссылку...")

        work_id = AO3Downloader.extract_work_id(user_message)

        if work_id:
            await update.message.reply_text(f"📚 Найден фанфик ID: {work_id}\n⏳ Получаю информацию...")

            await update.message.chat.send_action(action="typing")

            epub_path, filename = AO3Downloader.download_epub(work_id)

            if epub_path and os.path.exists(epub_path):
                try:
                    file_size = os.path.getsize(epub_path)
                    logging.info(f"📦 Размер файла: {file_size} байт")

                    if file_size > 50 * 1024 * 1024:
                        await update.message.reply_text("❌ Файл слишком большой (>50MB) для Telegram")
                    else:
                        await update.message.reply_text("✅ Файл скачан! Отправляю...")
                        with open(epub_path, 'rb') as epub_file:
                            await update.message.reply_document(
                                document=epub_file,
                                filename=filename,
                                caption=f"📖 {filename.replace('.epub', '')}\n🌐 Скачано через зеркало AO3"
                            )
                        await update.message.reply_text("🎉 Готово!")

                except Exception as e:
                    logging.error(f"❌ Ошибка отправки: {e}")
                    await update.message.reply_text("❌ Ошибка при отправке файла")

                try:
                    os.unlink(epub_path)
                except:
                    pass
            else:
                error_msg = """❌ Не удалось скачать файл.

Возможные причины:
• Фанфик не поддерживает скачивание в EPUB
• Проблемы с соединением
• Фанфик требует регистрации

💡 Попробуйте другой фанфик."""
                await update.message.reply_text(error_msg)
        else:
            await update.message.reply_text("❌ Не могу извлечь ID из ссылки.")
    else:
        await update.message.reply_text("❌ Это не ссылка на фанфик AO3.")

def main():
    """Основная функция"""
    print("🚀 Запуск бота с Flask сервером...")
    print("🌐 Используется зеркало: https://archiveofourown.gay")
    print("📚 Файлы сохраняются с оригинальными названиями")
    print("⚡ Работает без VPN!")
    print("⏹️  Ctrl+C для остановки\n")

    # Запускаем Flask сервер в отдельном потоке
    keep_alive()

    try:
        application = Application.builder().token(BOT_TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        print("🤖 Бот запущен и готов к работе!")
        print("🌐 Flask сервер запущен на порту 8080")
        application.run_polling()

    except Exception as e:
        print(f"💥 Ошибка: {e}")

if __name__ == '__main__':
    main()