FROM python:3.12-slim

EXPOSE 8000

WORKDIR /app

# Копируем requirements и ставим зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код бота
COPY . .

# Запускаем бота (замени digger.py на то, как реально называется твой главный файл)
CMD ["python", "digger.py"]
