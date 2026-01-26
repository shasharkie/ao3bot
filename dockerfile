FROM python:3.11-slim
WORKDIR /app

RUN pip install --no-cache-dir \
    aiogram==3.12.0 \
    requests==2.31.0 \
    Flask==3.0.2 \
    python-dotenv==1.0.0 \
    aiohttp==3.9.3

COPY . .

CMD ["python", "main_with_flask.py"]
