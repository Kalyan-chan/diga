FROM python:3.12-slim

# Открываем порт 8000 — это нужно только для того, чтобы TCP health check прошёл
EXPOSE 8000

# Добавляем крошечный TCP-сервер на фоне (не мешает боту вообще)
RUN pip install aiohttp

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Запускаем бота + крошечный сервер для health check одновременно
CMD aiohttp web -H 0.0.0.0 -p 8000 aiohttp.web:handle & python digger.py
