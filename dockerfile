FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .

RUN pip install --no-cache-dir aiogram==3.12.0
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python -c "import aiogram; print(f'aiogram {aiogram.__version__} установлен')"

CMD ["python", "main_with_flask.py"]
