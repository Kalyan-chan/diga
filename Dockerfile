FROM python:3.12-slim

WORKDIR /app

# Копируем и ставим зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt aiohttp  # добавляем aiohttp прямо сюда

# Копируем код бота
COPY . .

# Открываем любой порт (для TCP health check)
EXPOSE 8000

# Запускаем лёгкий веб-сервер на фоне + сам бот
CMD python -c "\
import asyncio, aiohttp.web as web;\
async def h(r): return web.Response(text='OK');\
app = web.Application();\
app.router.add_get('/', h);\
asyncio.get_event_loop().create_task(web._run_app(app, port=8000));\
" & python digger.py
