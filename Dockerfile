FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Это весь трюк — Koyeb будет думать, что это веб-приложение на порту 8080
ENV PORT=8080

# Запускаем бота нормально
CMD ["python", "digger.py"]
