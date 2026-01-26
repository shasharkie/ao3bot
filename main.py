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

# logging settings
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)

BOT_TOKEN = "8256763899:AAGB3QTtW2lpqYOzd0BXwdZ5LfRzzDo8lN8"
AO3_BASE_URL = "https://archiveofourown.gay"

# Flask app for staying active
app = Flask('')

@app.route('/')
def home():
    return "I'm alive"

def run_flask():
    app.run(host='0.0.0.0', port=5000)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()

class AO3Downloader:

    @staticmethod
    def extract_work_id(url):
        """ID of the work from AO3 URL"""
        try:
            logging.info(f"🔍 Analyzing URL: {url}")
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
                        logging.info(f"✅ correct ID: {work_id}")
                        return work_id
            return None
        except Exception as e:
            logging.error(f"💥 ID Error: {e}")
            return None

    @staticmethod
    def get_work_title(work_id):
        """title of the fic from HTML page"""
        try:
            work_url = f"{AO3_BASE_URL}/works/{work_id}"
            logging.info(f"📖 getting the title of the work: {work_url}")

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
                            logging.info(f"✅ fic name: {title}")
                            return title

            logging.warning("❌ title of the fic not found")
            return None

        except Exception as e:
            logging.error(f"💥 an error getting the title of the fic: {e}")
            return None

    @staticmethod
    def get_epub_download_url(work_id):
        """getting direct link for EPUB downloading"""
        try:
            work_url = f"{AO3_BASE_URL}/works/{work_id}?view_adult=true"
            logging.info(f"🌐 getting information about the fic: {work_url}")

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
                        logging.info(f"✅ HTML link found: {download_url}")
                        return download_url

            manual_url = f"{AO3_BASE_URL}/downloads/{work_id}/download.epub"
            logging.info(f"🔄 trying to give the link: {manual_url}")
            return manual_url

        except requests.exceptions.Timeout:
            logging.error("⏰ time out")
            return f"{AO3_BASE_URL}/downloads/{work_id}/download.epub"
        except Exception as e:
            logging.error(f"💥 an error while getting the link: {e}")
            return f"{AO3_BASE_URL}/downloads/{work_id}/download.epub"

    @staticmethod
    def download_epub(work_id):
        """downloads epub file"""
        try:
            work_title = AO3Downloader.get_work_title(work_id)
            epub_url = AO3Downloader.get_epub_download_url(work_id)
            logging.info(f"📥 downloading: {epub_url}")

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/epub+zip, application/octet-stream, */*',
                'Referer': f'{AO3_BASE_URL}/works/{work_id}',
            }

            response = requests.get(epub_url, headers=headers, stream=True, timeout=60)
            logging.info(f"📥 server response: {response.status_code}")

            if response.status_code == 200:
                file_size = int(response.headers.get('content-length', 0))
                logging.info(f"📊 file size: {file_size} b")

                with tempfile.NamedTemporaryFile(delete=False, suffix='.epub') as temp_file:
                    downloaded_size = 0
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            temp_file.write(chunk)
                            downloaded_size += len(chunk)

                    logging.info(f"💾 file saved, downloaded: {downloaded_size} b")

                    if downloaded_size < 1000:
                        logging.error(f"❌ the file is too small: {downloaded_size} b")
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
                logging.error(f"❌ http error while downloading: {response.status_code}")
                return None, None

        except requests.exceptions.Timeout:
            logging.error("⏰ time out while downloading the file")
            return None, None
        except Exception as e:
            logging.error(f"💥 an error while downloading: {e}")
            return None, None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """command /start"""
    welcome_text = """hi! this bot can help you download a fanfiction from the website "archive of our own" in epub file format

🔗links from the following websites are accepted:
• archiveofourown.org
• archiveofourown.gay

📄 final file format:
• epub

bot can  download any fanfiction 
send a link and bot will give you the file with your chosen fanfiction!"""

    await update.message.reply_text(welcome_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """text messages"""
    user_message = update.message.text.strip()
    logging.info(f"📨 message gotten: {user_message}")

    if ('archiveofourown.org' in user_message or 'archiveofourown.gay' in user_message) and '/works/' in user_message:
        await update.message.reply_text("🔍 analyzing the link...")

        work_id = AO3Downloader.extract_work_id(user_message)

        if work_id:
            await update.message.reply_text(f"📚 fic ID found: {work_id}\n⏳ getting the info...")

            await update.message.chat.send_action(action="typing")

            epub_path, filename = AO3Downloader.download_epub(work_id)

            if epub_path and os.path.exists(epub_path):
                try:
                    file_size = os.path.getsize(epub_path)
                    logging.info(f"📦 file size: {file_size} b")

                    if file_size > 50 * 1024 * 1024:
                        await update.message.reply_text("❌ the file is too large (>50MB) for Telegram")
                    else:
                        await update.message.reply_text("✅ the file is downloaded! sending...")
                        with open(epub_path, 'rb') as epub_file:
                            await update.message.reply_document(
                                document=epub_file,
                                filename=filename,
                                caption=f"📖 {filename.replace('.epub', '')}\n🌐 downloaded through AO3 mirror"
                            )
                        await update.message.reply_text("🎉 done!")

                except Exception as e:
                    logging.error(f"❌ Ошибка отправки: {e}")
                    await update.message.reply_text("❌ an error while sending the file")

                try:
                    os.unlink(epub_path)
                except:
                    pass
            else:
                error_msg = """❌ unable to download the file.

possible reasons:
• the fic does not support downloading in EPUB format
• connection issues
• the fic requires registration

💡 try another fic."""
                await update.message.reply_text(error_msg)
        else:
            await update.message.reply_text("❌ could not extraxt the ID from the link.")
    else:
        await update.message.reply_text("❌ it is not a link to AO3 fic.")

def main():
    """main function"""
    print("🚀 starting the bot with Flask server...")
    print("🌐 mirror used: https://archiveofourown.gay")
    print("📚 files are saved with original titles")
    print("⚡works without VPN!")
    print("⏹️  Ctrl+C to stop\n")

    # launching the Flask server in a seoarate thread
    keep_alive()

    try:
        application = Application.builder().token(BOT_TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        print("🤖 the bot is running and ready!")
        print("🌐 Flask server is running on port 5000")
        application.run_polling()

    except Exception as e:
        print(f"💥 an error: {e}")

if __name__ == '__main__':
    main()
