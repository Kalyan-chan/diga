import os
import json
import random
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)

# Конфигурация
TOKEN = "7752930706:AAEeY8KhjX2HuuRXEm9SGlqZsBVYOCs7x7U"
ADMIN_IDS = [1086796062]
CHANNEL_ID = -1002534375147
CHANNEL_LINK = "https://t.me/+0wj3N9ICDoVmNGMy"
DATA_DIR = "digger_data"
CHATS_DIR = os.path.join(DATA_DIR, "bunkers")
GLOBAL_DATA_FILE = os.path.join(DATA_DIR, "global_loot.json")
CHATS_LIST_FILE = os.path.join(DATA_DIR, "active_chats.json")
PROMO_FILE = os.path.join(DATA_DIR, "promocodes.json")

os.makedirs(CHATS_DIR, exist_ok=True)

WELCOME_MESSAGES = [
    "Привет, {username}! Добро пожаловать в пугабот.",
    "Здесь мы исследуем заброшенные места и находим ГЭПЭПЯТ.",
    "Будь осторожен - некоторые места охраняются!",
    "Команды: /dig - искать хабар, /myloot - мой улов, /top - топ, /global_top - мировой рейтинг\nПомощь: /help"
]

SUCCESS_MESSAGES = [
    "Тебе удалось залезть в бункер Метрополитена и вынес хабар +{} ГП-5",
    "Ты пробрался в консерву и вынес хабар +{} ГП-5",
    "Ты залез на ЗИЛ, нашел и вынес хабар +{} ГП-5",
    "Ты вскрыл поддомник и вынес хабар +{} ГП-5",
    "Ты проник в штаб ГО и вынес хабар +{} ГП-5",
    "Ты пролез на военнную часть и вынес хабар +{} ГП-5",
    "ЧОП отдал тебе списаные пуги +{} ГП-5",
    "Ты залез на МиГ и вынес хабар +{} ГП-5",
    "Ты притворился ЧОПом и забрал у школьника хабар +{} ГП-5"
]

FAIL_MESSAGES = [
    "Тебя схватил ЧОП! Ты потерял {} ГП-5",
    "Противогазы оказались гнилые... Ты выбросил {} ГП-5",
    "Твои противогазы кто-то натянул и они порвались - {} ГП-5",
    "Ты рассыпал хабар по дороге - {} ГП-5",
    "Злая бабка отобрала сумку с хабаром - {} ГП-5",
    "Маман нашла заначку с пугами и все выбросила - {} ГП-5",
    "Ты неправильно хранил пуги и они заржавели - {} ГП-5",
    "Тебя приняли на обьекте - {} ГП-5"
]

# Соответствие сообщений картинкам (без чисел)
MESSAGE_IMAGES = {
    # Успешные сообщения (1-9)
    "Тебе удалось залезть в бункер Метрополитена и вынес хабар": "1.png",
    "Ты пробрался в консерву и вынес хабар": "2.png",
    "Ты залез на ЗИЛ, нашел и вынес хабар": "3.png",
    "Ты вскрыл поддомник и вынес хабар": "4.png",
    "Ты проник в штаб ГО и вынес хабар": "5.png",
    "Ты пролез на военнную часть и вынес хабар": "6.png",
    "ЧОП отдал тебе списаные пуги": "7.png",
    "Ты залез на МиГ и вынес хабар": "8.png",
    "Ты притворился ЧОПом и забрал у школьника хабар": "9.png",
    
    # Неудачные сообщения (10-17)
    "Тебя схватил ЧОП! Ты потерял": "10.png",
    "Противогазы оказались гнилые... Ты выбросил": "11.png",
    "Твои противогазы кто-то натянул и они порвались -": "12.png",
    "Ты рассыпал хабар по дороге -": "13.png",
    "Злая бабка отобрала сумку с хабаром -": "14.png",
    "Маман нашла заначку с пугами и все выбросила -": "15.png",
    "Ты неправильно хранил пуги и они заржавели -": "16.png",
    "Тебя приняли на обьекте -": "17.png",
    
    # Супер-удача (18)
    "🔥 Шанс 1%! Ты смог утащить целый ящик +40 ГП-5": "18.png"
}

# ======= ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =======
def load_data(file_path):
    if not os.path.exists(file_path):
        return {}
    with open(file_path, "r") as f:
        return json.load(f)

def save_data(data, file_path):
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)

def get_bunker_file(bunker_id):
    return os.path.join(CHATS_DIR, f"bunker_{bunker_id}.json")

def update_chat_list(chat_id, chat_title):
    chats_data = load_data(CHATS_LIST_FILE)
    chats_data[str(chat_id)] = {
        "title": chat_title,
        "last_active": datetime.now().isoformat()
    }
    save_data(chats_data, CHATS_LIST_FILE)

def format_wait_time(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours} ч. {minutes} мин."

async def check_subscription(user_id, context):
    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

async def update_global_stats(user_id, new_gp5, username):
    global_data = load_data(GLOBAL_DATA_FILE)
    if str(user_id) in global_data:
        if new_gp5 > global_data[str(user_id)]["gp5"]:
            global_data[str(user_id)] = {"gp5": new_gp5, "username": username}
    else:
        global_data[str(user_id)] = {"gp5": new_gp5, "username": username}
    save_data(global_data, GLOBAL_DATA_FILE)

async def find_user_in_chats(user_id):
    user_data = None
    for filename in os.listdir(CHATS_DIR):
        if filename.startswith("bunker_") and filename.endswith(".json"):
            chat_data = load_data(os.path.join(CHATS_DIR, filename))
            if str(user_id) in chat_data:
                if user_data is None or chat_data[str(user_id)]["gp5"] > user_data["gp5"]:
                    user_data = chat_data[str(user_id)]
                    user_data["chat_id"] = filename.split("_")[1].split(".")[0]
    return user_data

def get_image_for_message(message):
    """Находит картинку для сообщения, убирая числа из поиска"""
    # Убираем числа и знаки +/-
    clean_message = ''.join([c for c in message if not c.isdigit() and c not in ['+', '-']]).strip()
    
    # Ищем подходящую картинку
    for msg_pattern, image_file in MESSAGE_IMAGES.items():
        if msg_pattern in clean_message:
            return image_file
    return None

# ======= КОМАНДЫ СТАРЫЕ =======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.message.chat.type == "private":
        await update.message.reply_text("Я работаю только в чатах!")
        return
    update_chat_list(update.effective_chat.id, update.effective_chat.title)
    welcome = "\n".join(WELCOME_MESSAGES).format(username=update.effective_user.mention_markdown())
    await update.message.reply_text(welcome, parse_mode="Markdown")

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.message.chat.type == "private":
        await update.message.reply_text("Я работаю только в чатах!")
        return
    help_text = (
        "📜 Доступные команды:\n"
        "/dig - искать хабар (раз в 4 часа)\n"
        "/myloot - проверить свой улов\n"
        "/top - топ текущего чата\n"
        "/global_top - мировой рейтинг\n"
        "/promo - использовать промокод\n\n"
        f"Для доступа к боту нужно подписаться на канал: {CHANNEL_LINK}\n"
        "Также можно использовать слово 'хабарить' для поиска хабара"
    )
    await update.message.reply_text(help_text)

async def admin_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("Неизвестная команда")
        return
    help_text = (
        "🛠️ Админ-команды:\n"
        "/secretgive <кол-во> <ID> - выдать ГП-5\n"
        "/resetcooldown - сбросить таймер (ответ на сообщение)\n"
        "/chatstats - статистика по чатам\n"
        "/post - разослать пост (ответ на сообщение)\n"
        "/promoadd - создать промокод\n"
        "/promoinfo - информация по промокодам\n"
        "/ahelp - это меню"
    )
    await update.message.reply_text(help_text)

# ======= dig =======
async def dig(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.message.chat.type == "private":
        await update.message.reply_text("Я работаю только в чатах!")
        return
    user = update.effective_user
    bunker = update.effective_chat
    update_chat_list(bunker.id, bunker.title)

    if not await check_subscription(user.id, context):
        keyboard = [[InlineKeyboardButton("Подписаться", url=CHANNEL_LINK)]]
        await update.message.reply_text(
            "Для доступа к полазам нужно подписаться на наш канал:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    bunker_file = get_bunker_file(bunker.id)
    bunker_data = load_data(bunker_file)
    is_new_user = str(user.id) not in bunker_data
    digger_data = bunker_data.get(str(user.id), {
        "gp5": 0,
        "last_dig": None,
        "username": user.full_name,
        "last_loot_type": None
    })

    if digger_data["last_dig"]:
        last_dig = datetime.fromisoformat(digger_data["last_dig"])
        time_diff = datetime.now() - last_dig
        if time_diff < timedelta(hours=4):
            wait_seconds = (timedelta(hours=4) - time_diff).seconds
            await update.message.reply_text(f"Еще рано идти! Жди {format_wait_time(wait_seconds)}")
            return

    if random.random() < 0.01 and digger_data.get("last_loot_type") != "super":
        loot = 40
        message = "🔥 Шанс 1%! Ты смог утащить целый ящик +40 ГП-5"
        loot_type = "super"
    else:
        if is_new_user:
            loot = random.randint(1, 5)
            message = random.choice(SUCCESS_MESSAGES).format(loot)
            loot_type = "normal"
        else:
            is_success = random.choices([True, False], weights=[75, 25])[0]
            if is_success:
                loot = random.randint(1, 5)
                message = random.choice(SUCCESS_MESSAGES).format(loot)
                loot_type = "normal"
            else:
                lost = random.randint(1, 3)
                message = random.choice(FAIL_MESSAGES).format(lost)
                loot = -lost
                loot_type = "fail"

    digger_data["gp5"] += loot
    digger_data["last_dig"] = datetime.now().isoformat()
    digger_data["username"] = user.full_name
    digger_data["last_loot_type"] = loot_type
    bunker_data[str(user.id)] = digger_data
    save_data(bunker_data, bunker_file)

    await update_global_stats(user.id, digger_data["gp5"], user.full_name)
    
    # Отправка сообщения с картинкой
    image_file = get_image_for_message(message)
    print(f"DEBUG: Полученное сообщение: '{message}'")
    print(f"DEBUG: Найденная картинка: {image_file}")
    print(f"DEBUG: Путь к картинке: {os.path.abspath(image_file) if image_file else 'None'}")
    print(f"DEBUG: Картинка существует: {os.path.exists(image_file) if image_file else 'False'}")
    
    if image_file and os.path.exists(image_file):
        print(f"Отправка картинки: {image_file}")
        try:
            with open(image_file, 'rb') as photo:
                await update.message.reply_photo(
                    photo=photo,
                    caption=f"{message}\nТвой улов: {digger_data['gp5']} ГП-5"
                )
                print("Картинка успешно отправлена!")
        except Exception as e:
            print(f"Ошибка при отправке картинки: {e}")
            await update.message.reply_text(f"{message}\nТвой улов: {digger_data['gp5']} ГП-5")
    else:
        print(f"Картинка не найдена или не существует: {image_file}")
        await update.message.reply_text(f"{message}\nТвой улов: {digger_data['gp5']} ГП-5")

# ======= ОБРАБОТКА СЛОВА "ХАБАРИТЬ" =======
async def handle_habarit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Проверяем, что update.message существует и это не личный чат
    if not update.message or update.message.chat.type == "private":
        return
    
    text = update.message.text.lower()
    if "хабарить" in text:
        await dig(update, context)

# ======= myloot =======
async def myloot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.message.chat.type == "private":
        await update.message.reply_text("Я работаю только в чатах!")
        return
    user = update.effective_user
    bunker_file = get_bunker_file(update.effective_chat.id)
    bunker_data = load_data(bunker_file)
    if str(user.id) in bunker_data:
        await update.message.reply_text(f"Твой улов: {bunker_data[str(user.id)]['gp5']} ГП-5")
    else:
        await update.message.reply_text("Ты еще ничего не нашел! Используй /dig")

# ======= top =======
async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.message.chat.type == "private":
        await update.message.reply_text("Я работаю только в чатах!")
        return
    bunker_file = get_bunker_file(update.effective_chat.id)
    bunker_data = load_data(bunker_file)
    sorted_diggers = sorted(bunker_data.values(), key=lambda x: x["gp5"], reverse=True)[:10]
    top_list = "\n".join([f"🏅 {i+1}. {d['username']} - {d['gp5']} ГП-5" for i, d in enumerate(sorted_diggers)])
    await update.message.reply_text(f"🏆 Топ чата:\n{top_list}")

# ======= global_top =======
async def global_top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.message.chat.type == "private":
        await update.message.reply_text("Я работаю только в чатах!")
        return
    all_users = {}
    for filename in os.listdir(CHATS_DIR):
        if filename.startswith("bunker_") and filename.endswith(".json"):
            chat_data = load_data(os.path.join(CHATS_DIR, filename))
            for user_id, data in chat_data.items():
                if user_id not in all_users or data["gp5"] > all_users[user_id]["gp5"]:
                    all_users[user_id] = data
    sorted_diggers = sorted(all_users.values(), key=lambda x: x["gp5"], reverse=True)[:10]
    top_list = "\n".join([f"🌍 {i+1}. {d['username']} - {d['gp5']} ГП-5" for i, d in enumerate(sorted_diggers)])
    await update.message.reply_text(f"🔥 Мировой рейтинг диггеров:\n{top_list}")

# ======= secret_command =======
async def secret_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.message.chat.type == "private":
        await update.message.reply_text("Я работаю только в чатах!")
        return
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("Неизвестная команда")
        return
    try:
        amount = int(context.args[0])
        target_user_id = int(context.args[1])
    except (IndexError, ValueError):
        await update.message.reply_text("Использование: /secretgive <количество> <ID пользователя>")
        return
    bunker_file = get_bunker_file(update.effective_chat.id)
    bunker_data = load_data(bunker_file)
    user_found = False
    if str(target_user_id) in bunker_data:
        bunker_data[str(target_user_id)]["gp5"] += amount
        save_data(bunker_data, bunker_file)
        user_found = True
        await update_global_stats(target_user_id, bunker_data[str(target_user_id)]["gp5"], bunker_data[str(target_user_id)]["username"])
    else:
        user_data = await find_user_in_chats(target_user_id)
        if user_data:
            chat_id = user_data["chat_id"]
            bunker_file = get_bunker_file(chat_id)
            bunker_data = load_data(bunker_file)
            bunker_data[str(target_user_id)]["gp5"] += amount
            save_data(bunker_data, bunker_file)
            user_found = True
            await update_global_stats(target_user_id, bunker_data[str(target_user_id)]["gp5"], bunker_data[str(target_user_id)]["username"])
    if user_found:
        await update.message.reply_text(f"Добавлено {amount} ГП-5 пользователю {target_user_id}")
    else:
        await update.message.reply_text(f"Пользователь {target_user_id} не найден ни в одном чате")

# ======= reset_cooldown =======
async def reset_cooldown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.message.chat.type == "private":
        await update.message.reply_text("Я работаю только в чатах!")
        return
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("Ты не вожатый группы!")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("Ответь на сообщение диггера!")
        return
    target_user = update.message.reply_to_message.from_user
    bunker_file = get_bunker_file(update.effective_chat.id)
    bunker_data = load_data(bunker_file)
    if str(target_user.id) in bunker_data:
        bunker_data[str(target_user.id)]["last_dig"] = None
        save_data(bunker_data, bunker_file)
        await update.message.reply_text(f"Таймер для {target_user.full_name} сброшен!")
    else:
        await update.message.reply_text("Этот диггер еще не делал вылазок!")

# ======= chat_stats =======
async def chat_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.message.chat.type == "private":
        await update.message.reply_text("Я работаю только в чатах!")
        return
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("Неизвестная команда")
        return
    chats_data = load_data(CHATS_LIST_FILE)
    total_private = total_group = users_private = users_group = 0
    for chat_id in chats_data:
        try:
            chat_info = await context.bot.get_chat(chat_id)
            bunker_file = get_bunker_file(chat_id)
            bunker_data = load_data(bunker_file)
            if chat_info.type == "private":
                total_private += 1
                users_private += len(bunker_data)
            else:
                total_group += 1
                users_group += len(bunker_data)
        except:
            pass
    stats_text = (
        f"📊 Статистика бота:\n"
        f"Групповых чатов: {total_group}\n"
        f"Участников в группах: {users_group}\n"
        f"Личных чатов: {total_private}\n"
        f"Участников в личных чатах: {users_private}\n"
        f"Всего чатов: {total_group + total_private}\n"
        f"Всего участников: {users_group + users_private}"
    )
    await update.message.reply_text(stats_text)

# ======= post_to_all =======
async def post_to_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.message.chat.type == "private":
        await update.message.reply_text("Я работаю только в чатах!")
        return
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("Неизвестная команда")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("Ответьте на сообщение, которое нужно разослать!")
        return
    message = update.message.reply_to_message
    chats_data = load_data(CHATS_LIST_FILE)
    total_chats = len(chats_data)
    successful = 0
    progress_msg = await update.message.reply_text(f"📤 Рассылка начата... 0/{total_chats}")
    for i, chat_id in enumerate(chats_data.keys()):
        try:
            if message.text:
                await context.bot.send_message(chat_id=chat_id, text=message.text)
            elif message.photo:
                await context.bot.send_photo(chat_id=chat_id, photo=message.photo[-1].file_id, caption=message.caption)
            elif message.video:
                await context.bot.send_video(chat_id=chat_id, video=message.video.file_id, caption=message.caption)
            successful += 1
        except:
            pass
        if i % 5 == 0:
            await progress_msg.edit_text(f"📤 Рассылка... {i+1}/{total_chats}")
    await progress_msg.edit_text(f"✅ Рассылка завершена! Отправлено в {successful}/{total_chats} чатов.")

# ======= ПРОМОКОДЫ =======
def load_promos():
    return load_data(PROMO_FILE)

def save_promos(promos):
    save_data(promos, PROMO_FILE)

async def promoadd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("Неизвестная команда")
        return
    try:
        amount = int(context.args[0])
        uses = int(context.args[1])
        code = context.args[2]
    except (IndexError, ValueError):
        await update.message.reply_text("Использование: /promoadd <ГП-5> <кол-во использований> <код>")
        return
    promos = load_promos()
    promos[code] = {
        "amount": amount,
        "max_uses": uses,
        "remaining_uses": uses,
        "used_by": []
    }
    save_promos(promos)
    await update.message.reply_text(f"Промокод {code} создан: {amount} ГП-5, {uses} использований")

async def promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    try:
        code = context.args[0]
    except IndexError:
        await update.message.reply_text("Использование: /promo <код>")
        return
    promos = load_promos()
    if code not in promos:
        await update.message.reply_text("Промокод не найден!")
        return
    promo_data = promos[code]
    user_id = str(user.id)
    
    # Проверяем, использовал ли уже пользователь этот промокод
    if user_id in promo_data["used_by"]:
        await update.message.reply_text("Вы уже использовали этот промокод!")
        return
    
    # Проверяем, остались ли использования
    if promo_data["remaining_uses"] <= 0:
        await update.message.reply_text("Промокод закончился.")
        return
    
    # Добавляем ГП-5 пользователю
    bunker_file = get_bunker_file(update.effective_chat.id)
    bunker_data = load_data(bunker_file)
    if user_id not in bunker_data:
        bunker_data[user_id] = {"gp5": 0, "last_dig": None, "username": user.full_name, "last_loot_type": None}
    
    bunker_data[user_id]["gp5"] += promo_data["amount"]
    bunker_data[user_id]["username"] = user.full_name
    save_data(bunker_data, bunker_file)
    
    # Обновляем глобальные статистики
    await update_global_stats(user.id, bunker_data[user_id]["gp5"], user.full_name)
    
    # Обновляем данные промокода
    promo_data["used_by"].append(user_id)
    promo_data["remaining_uses"] -= 1
    save_promos(promos)
    
    await update.message.reply_text(f"Промокод активирован! Вы получили {promo_data['amount']} ГП-5. Всего у тебя: {bunker_data[user_id]['gp5']} ГП-5")

async def promoinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("Неизвестная команда")
        return
    
    promos = load_promos()
    if not promos:
        await update.message.reply_text("Нет активных промокодов")
        return
    
    info_text = "📊 Информация о промокодах:\n\n"
    for code, data in promos.items():
        info_text += f"🔹 {code}:\n"
        info_text += f"   ГП-5: {data['amount']}\n"
        info_text += f"   Использований: {data['max_uses'] - data['remaining_uses']}/{data['max_uses']}\n"
        info_text += f"   Осталось: {data['remaining_uses']}\n"
        info_text += f"   Использовали: {len(data['used_by'])} пользователей\n\n"
    
    await update.message.reply_text(info_text)

# ======= МЕНЮ =======
async def ahelp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await admin_help(update, context)

# ======= MAIN =======
def main():
    # Проверка соответствия сообщений
    print("Проверка соответствия сообщений картинкам:")
    for msg, img in MESSAGE_IMAGES.items():
        print(f"'{msg}' -> {img}")
    
    application = Application.builder().token(TOKEN).build()

    # Основные команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("ahelp", ahelp))
    application.add_handler(CommandHandler("dig", dig))
    application.add_handler(CommandHandler("myloot", myloot))
    application.add_handler(CommandHandler("top", top))
    application.add_handler(CommandHandler("global_top", global_top))
    application.add_handler(CommandHandler("secretgive", secret_command))
    application.add_handler(CommandHandler("resetcooldown", reset_cooldown))
    application.add_handler(CommandHandler("chatstats", chat_stats))
    application.add_handler(CommandHandler("post", post_to_all))
    application.add_handler(CommandHandler("promoadd", promoadd))
    application.add_handler(CommandHandler("promo", promo))
    application.add_handler(CommandHandler("promoinfo", promoinfo))
    
    # Обработка слова "хабарить"
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_habarit))

    print("Бот запущен")
    application.run_polling()

if __name__ == "__main__":
    main()