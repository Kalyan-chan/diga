import asyncio
import os
import json
import random
import motor.motor_asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram import F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.types import FSInputFile
import logging

logging.basicConfig(level=logging.INFO)

async def load_initial_maintenance():
    doc = await db['config'].find_one({'_id': 'maintenance'})
    return int(doc['value']) if doc and 'value' in doc else 0

def load_config():
    return {
        'TOKEN': os.getenv('TOKEN'),
        'ADMIN_IDS': [int(id.strip()) for id in os.getenv('ADMIN_IDS', '').split(',') if id],
        'CHANNEL_ID': int(os.getenv('CHANNEL_ID', '0')),
        'CHANNEL_LINK': os.getenv('CHANNEL_LINK', ''),
        'MAINTENANCE': 0  # Will be overridden by DB
    }

config = load_config()
MONGODB_URI = os.getenv('MONGODB_URI')
if not MONGODB_URI:
    raise ValueError("MONGODB_URI not set in environment")
mongo_client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URI)
db = mongo_client['bot_db']

TOKEN = config['TOKEN']
ADMIN_IDS = config['ADMIN_IDS']
CHANNEL_ID = config['CHANNEL_ID']
CHANNEL_LINK = config['CHANNEL_LINK']
MAINTENANCE = config['MAINTENANCE']  # Temporary

IMG_DIR = 'IMG'
os.makedirs(IMG_DIR, exist_ok=True)

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

MESSAGE_IMAGES = {
    "Тебе удалось залезть в бункер Метрополитена и вынес хабар": "1.png",
    "Ты пробрался в консерву и вынес хабар": "2.png",
    "Ты залез на ЗИЛ, нашел и вынес хабар": "3.png",
    "Ты вскрыл поддомник и вынес хабар": "4.png",
    "Ты проник в штаб ГО и вынес хабар": "5.png",
    "Ты пролез на военнную часть и вынес хабар": "6.png",
    "ЧОП отдал тебе списаные пуги": "7.png",
    "Ты залез на МиГ и вынес хабар": "8.png",
    "Ты притворился ЧОПом и забрал у школьника хабар": "9.png",
    "Тебя схватил ЧОП! Ты потерял": "10.png",
    "Противогазы оказались гнилые... Ты выбросил": "11.png",
    "Твои противогазы кто-то натянул и они порвались -": "12.png",
    "Ты рассыпал хабар по дороге -": "13.png",
    "Злая бабка отобрала сумку с хабаром -": "14.png",
    "Маман нашла заначку с пугами и все выбросила -": "15.png",
    "Ты неправильно хранил пуги и они заржавели -": "16.png",
    "Тебя приняли на обьекте -": "17.png",
    "🔥 Шанс 1%! Ты смог утащить целый ящик +40 ГП-5": "18.png"
}

bot = Bot(token=TOKEN)
dp = Dispatcher()

GLOBAL_DATA_FILE = 'global_loot.json'
CHATS_LIST_FILE = 'active_chats.json'
PROMO_FILE = 'promocodes.json'
GLOBAL_COOLDOWN_FILE = 'cooldowns.json'

async def load_data(file_path):
    collection_name = get_collection_name(file_path)
    if collection_name == 'chat_data':
        chat_id = get_chat_id_from_path(file_path)
        doc = await db[collection_name].find_one({'_id': chat_id})
        return doc['data'] if doc else {}
    else:
        doc = await db[collection_name].find_one({'_id': 'singleton'})
        return doc['data'] if doc else {}

async def save_data(data, file_path):
    collection_name = get_collection_name(file_path)
    if collection_name == 'chat_data':
        chat_id = get_chat_id_from_path(file_path)
        await db[collection_name].replace_one({'_id': chat_id}, {'_id': chat_id, 'data': data}, upsert=True)
    else:
        await db[collection_name].replace_one({'_id': 'singleton'}, {'_id': 'singleton', 'data': data}, upsert=True)

def get_collection_name(file_path):
    base = os.path.basename(file_path).replace('.json', '')
    if base.startswith('bunker_'):
        return 'chat_data'
    return base

def get_chat_id_from_path(file_path):
    base = os.path.basename(file_path).replace('.json', '')
    if base.startswith('bunker_'):
        return int(base.split('_')[1])
    raise ValueError("Invalid bunker file path")

def get_bunker_file(bunker_id):
    return f"bunker_{bunker_id}.json"  # Now just a string for compatibility

async def update_chat_list(chat_id, chat_title, chat_type):
    chats_data = await load_data(CHATS_LIST_FILE)
    chats_data[str(chat_id)] = {
        "title": chat_title,
        "last_active": datetime.now().isoformat(),
        "type": chat_type
    }
    await save_data(chats_data, CHATS_LIST_FILE)

def format_wait_time(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours} ч. {minutes} мин."

async def check_subscription(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

async def update_global_stats(user_id, new_gp5, username):
    global_data = await load_data(GLOBAL_DATA_FILE)
    user_id_str = str(user_id)
    if user_id_str in global_data:
        if new_gp5 > global_data[user_id_str]["gp5"]:
            global_data[user_id_str] = {"gp5": new_gp5, "username": username}
    else:
        global_data[user_id_str] = {"gp5": new_gp5, "username": username}
    await save_data(global_data, GLOBAL_DATA_FILE)

async def find_user_in_chats(user_id):
    user_data = None
    async for doc in db['chat_data'].find():
        chat_data = doc['data']
        user_id_str = str(user_id)
        if user_id_str in chat_data:
            current = chat_data[user_id_str]
            if user_data is None or current["gp5"] > user_data["gp5"]:
                user_data = current.copy()
                user_data["chat_id"] = str(doc['_id'])
    return user_data

def escape_markdown_v2(text):
    special_chars = '_*[]()~`>#+-=|{}.!'
    return ''.join(['\\' + c if c in special_chars else c for c in text])

def get_image_for_message(message):
    clean_message = ' '.join(''.join([c for c in message if not c.isdigit() and c not in ['+', '-']]).split()).strip()
    for msg_pattern in MESSAGE_IMAGES:
        clean_pattern = ' '.join(''.join([c for c in msg_pattern if not c.isdigit() and c not in ['+', '-']]).split()).strip()
        if clean_pattern in clean_message or clean_message in clean_pattern:
            image_path = os.path.join(IMG_DIR, MESSAGE_IMAGES[msg_pattern])
            logging.info(f"Found image for message: {message} -> {image_path}")
            return image_path
    return None

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    global MAINTENANCE
    if message.chat.type == "private":
        await message.reply("Я работаю только в чатах!")
        return
    await update_chat_list(message.chat.id, message.chat.title or "", message.chat.type)
    welcome = "\n".join(WELCOME_MESSAGES).format(username=message.from_user.full_name)
    await message.reply(welcome)

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    global MAINTENANCE
    if message.chat.type == "private":
        await message.reply("Я работаю только в чатах!")
        return
    if MAINTENANCE == 1 and message.from_user.id not in ADMIN_IDS and message.from_user.id not in [1086796062, 1036331890]:
        await message.reply("Технические работы. Попробуйте позже.")
        return
    help_text = (
        "📜 Доступные команды:\n"
        "/dig - искать хабар (раз в 4 часа)\n"
        "/myloot - проверить свой улов\n"
        "/top - топ текущего чата\n"
        "/global_top - мировой рейтинг\n"
        "/promo <код> - использовать промокод\n\n"
        "Также можно использовать слово 'хабарить' для поиска хабара."
    )
    await message.reply(help_text)

@dp.message(Command("ahelp"))
async def cmd_admin_help(message: types.Message):
    if message.from_user.id not in ADMIN_IDS and message.from_user.id not in [1086796062, 1036331890]:
        await message.reply("Неизвестная команда")
        return
    help_text = (
        "🛠️ Админ-команды:\n"
        "/secretgive <кол-во> <ID> - выдать ГП-5\n"
        "/resetcooldown - сбросить таймер (ответ на сообщение)\n"
        "/chatstats - статистика по чатам\n"
        "/post - разослать пост (ответ на сообщение)\n"
        "/promoadd <ГП-5> <использований> <код> - создать промокод\n"
        "/promoinfo - информация по промокодам\n"
        "/maintenance_on - включить техработы\n"
        "/maintenance_off - отключить техработы\n"
    )
    await message.reply(help_text)

@dp.message(Command("dig"))
async def cmd_dig(message: types.Message):
    global MAINTENANCE
    if message.chat.type == "private":
        await message.reply("Я работаю только в чатах!")
        return
    if MAINTENANCE == 1 and message.from_user.id not in ADMIN_IDS and message.from_user.id not in [1086796062, 1036331890]:
        await message.reply("Технические работы. Попробуйте позже.")
        return
    bunker = message.chat
    await update_chat_list(bunker.id, bunker.title or "", bunker.type)
    if not await check_subscription(message.from_user.id):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Подписаться", url=CHANNEL_LINK)]])
        await message.reply("Для доступа к полазам нужно подписаться на наш канал:", reply_markup=keyboard)
        return
    cooldowns = await load_data(GLOBAL_COOLDOWN_FILE)
    user_id_str = str(message.from_user.id)
    if user_id_str in cooldowns:
        cd = cooldowns[user_id_str]
        if isinstance(cd, str):
            last_dig = datetime.fromisoformat(cd)
        else:
            last_dig = datetime.fromisoformat(cd["time"])
        time_diff = datetime.now() - last_dig
        if time_diff < timedelta(hours=4):
            wait_seconds = (timedelta(hours=4) - time_diff).total_seconds()
            await message.reply(f"Еще рано идти! Жди {format_wait_time(int(wait_seconds))}")
            return
    bunker_file = get_bunker_file(bunker.id)
    bunker_data = await load_data(bunker_file)
    is_new_user = user_id_str not in bunker_data
    digger_data = bunker_data.get(user_id_str, {
        "gp5": 0,
        "username": message.from_user.full_name,
        "last_loot_type": None
    })
    if random.random() < 0.01 and digger_data.get("last_loot_type") != "super":
        loot = 40
        msg_text = "🔥 Шанс 1%! Ты смог утащить целый ящик +40 ГП-5"
        loot_type = "super"
    else:
        if is_new_user:
            loot = random.randint(1, 5)
            msg_text = random.choice(SUCCESS_MESSAGES).format(loot)
            loot_type = "normal"
        else:
            is_success = random.choices([True, False], weights=[75, 25])[0]
            if is_success:
                loot = random.randint(1, 5)
                msg_text = random.choice(SUCCESS_MESSAGES).format(loot)
                loot_type = "normal"
            else:
                lost = random.randint(1, 3)
                msg_text = random.choice(FAIL_MESSAGES).format(lost)
                loot = -lost
                loot_type = "fail"
    digger_data["gp5"] += loot
    digger_data["username"] = message.from_user.full_name
    digger_data["last_loot_type"] = loot_type
    bunker_data[user_id_str] = digger_data
    await save_data(bunker_data, bunker_file)
    cooldowns[user_id_str] = {"time": datetime.now().isoformat(), "last_loot": loot}
    await save_data(cooldowns, GLOBAL_COOLDOWN_FILE)
    await update_global_stats(message.from_user.id, digger_data["gp5"], message.from_user.full_name)
    image_path = get_image_for_message(msg_text)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Мой улов", callback_data="myloot")],
        [InlineKeyboardButton(text="Топ чата", callback_data="top")]
    ])
    if image_path and os.path.exists(image_path):
        try:
            await message.reply_photo(photo=FSInputFile(image_path), caption=f"{msg_text}\nТвой улов: {digger_data['gp5']} ГП-5", reply_markup=keyboard)
        except Exception as e:
            logging.error(f"Error sending photo {image_path}: {e}")
            await message.reply(f"{msg_text}\nТвой улов: {digger_data['gp5']} ГП-5", reply_markup=keyboard)
    else:
        await message.reply(f"{msg_text}\nТвой улов: {digger_data['gp5']} ГП-5", reply_markup=keyboard)

@dp.callback_query(F.data.in_({"myloot", "top"}))
async def handle_callback(query: types.CallbackQuery):
    if query.data == "myloot":
        await cmd_myloot(query.message, user=query.from_user)
    elif query.data == "top":
        await cmd_top(query.message)
    await query.answer()

@dp.message(F.text.lower().contains("хабарить"), ~F.text.startswith("/"))
async def handle_habarit(message: types.Message):
    global MAINTENANCE
    if message.chat.type == "private":
        return
    if MAINTENANCE == 1 and message.from_user.id not in ADMIN_IDS and message.from_user.id not in [1086796062, 1036331890]:
        await message.reply("Технические работы. Попробуйте позже.")
        return
    await cmd_dig(message)

@dp.message(Command("myloot"))
async def cmd_myloot(message: types.Message, user: types.User = None):
    global MAINTENANCE
    if message.chat.type == "private":
        await message.reply("Я работаю только в чатах!")
        return
    if MAINTENANCE == 1 and message.from_user.id not in ADMIN_IDS and message.from_user.id not in [1086796062,
                                                                                                   1036331890]:
        await message.reply("Технические работы. Попробуйте позже.")
        return
    bunker_file = get_bunker_file(message.chat.id)
    bunker_data = await load_data(bunker_file)
    effective_user = user if user else message.from_user
    user_id_str = str(effective_user.id)
    if user_id_str in bunker_data:
        digger_data = bunker_data[user_id_str]
        reply_text = f"Твой улов: {digger_data['gp5']} ГП-5"
        cooldowns = await load_data(GLOBAL_COOLDOWN_FILE)
        last_loot = cooldowns.get(user_id_str, {}).get("last_loot", None)
        if last_loot is not None:
            reply_text += f"\nПоследняя попытка: {last_loot:+}"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Топ чата", callback_data="top")],
            [InlineKeyboardButton(text="Глобальный топ", callback_data="global_top")]
        ])
        await message.reply(reply_text, reply_markup=keyboard)
    else:
        await message.reply("Ты еще ничего не нашел! Используй /dig")

@dp.callback_query(F.data == "global_top")
async def handle_global_top_callback(query: types.CallbackQuery):
    await cmd_global_top(query.message)
    await query.answer()

@dp.message(Command("top"))
async def cmd_top(message: types.Message):
    global MAINTENANCE
    if message.chat.type == "private":
        await message.reply("Я работаю только в чатах!")
        return
    if MAINTENANCE == 1 and message.from_user.id not in ADMIN_IDS and message.from_user.id not in [1086796062, 1036331890]:
        await message.reply("Технические работы. Попробуйте позже.")
        return
    bunker_file = get_bunker_file(message.chat.id)
    bunker_data = await load_data(bunker_file)
    sorted_diggers = sorted(bunker_data.values(), key=lambda x: x["gp5"], reverse=True)[:10]
    top_list = "\n".join([escape_markdown_v2(f"🏅 {i+1}. {d['username']} - {d['gp5']} ГП-5") for i, d in enumerate(sorted_diggers)])
    reply_text = f"**{escape_markdown_v2('🏆 Топ чата:')}**\n{top_list if top_list else escape_markdown_v2('Пусто')}"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Глобальный топ", callback_data="global_top")]
    ])
    await message.reply(reply_text, parse_mode="MarkdownV2", reply_markup=keyboard)

@dp.message(Command("global_top"))
async def cmd_global_top(message: types.Message):
    global MAINTENANCE
    if message.chat.type == "private":
        await message.reply("Я работаю только в чатах!")
        return
    if MAINTENANCE == 1 and message.from_user.id not in ADMIN_IDS and message.from_user.id not in [1086796062, 1036331890]:
        await message.reply("Технические работы. Попробуйте позже.")
        return
    all_users = {}
    async for doc in db['chat_data'].find():
        chat_data = doc['data']
        for user_id, data in chat_data.items():
            if user_id not in all_users or data["gp5"] > all_users[user_id]["gp5"]:
                all_users[user_id] = data
    sorted_diggers = sorted(all_users.values(), key=lambda x: x["gp5"], reverse=True)[:10]
    top_list = "\n".join([escape_markdown_v2(f"🌍 {i+1}. {d['username']} - {d['gp5']} ГП-5") for i, d in enumerate(sorted_diggers)])
    reply_text = f"**{escape_markdown_v2('🔥 Мировой рейтинг диггеров:')}**\n{top_list if top_list else escape_markdown_v2('Пусто')}"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Топ чата", callback_data="top")]
    ])
    await message.reply(reply_text, parse_mode="MarkdownV2", reply_markup=keyboard)

@dp.message(Command("secretgive"))
async def cmd_secretgive(message: types.Message):
    if message.chat.type == "private":
        await message.reply("Я работаю только в чатах!")
        return
    if message.from_user.id not in ADMIN_IDS and message.from_user.id not in [1086796062, 1036331890]:
        await message.reply("Неизвестная команда")
        return
    parts = message.text.split()
    try:
        amount = int(parts[1])
        target_user_id = int(parts[2])
    except:
        await message.reply("Использование: /secretgive <количество> <ID пользователя>")
        return
    bunker_file = get_bunker_file(message.chat.id)
    bunker_data = await load_data(bunker_file)
    user_found = False
    target_user_id_str = str(target_user_id)
    if target_user_id_str in bunker_data:
        bunker_data[target_user_id_str]["gp5"] += amount
        await save_data(bunker_data, bunker_file)
        user_found = True
        await update_global_stats(target_user_id, bunker_data[target_user_id_str]["gp5"], bunker_data[target_user_id_str]["username"])
    else:
        user_data = await find_user_in_chats(target_user_id)
        if user_data:
            chat_id = int(user_data["chat_id"])
            bunker_file = get_bunker_file(chat_id)
            bunker_data = await load_data(bunker_file)
            bunker_data[target_user_id_str]["gp5"] += amount
            await save_data(bunker_data, bunker_file)
            user_found = True
            await update_global_stats(target_user_id, bunker_data[target_user_id_str]["gp5"], bunker_data[target_user_id_str]["username"])
    if user_found:
        await message.reply(f"Добавлено {amount} ГП-5 пользователю {target_user_id}")
    else:
        await message.reply(f"Пользователь {target_user_id} не найден ни в одном чате")

@dp.message(Command("resetcooldown"))
async def cmd_resetcooldown(message: types.Message):
    if message.chat.type == "private":
        await message.reply("Я работаю только в чатах!")
        return
    if message.from_user.id not in ADMIN_IDS and message.from_user.id not in [1086796062, 1036331890]:
        await message.reply("Ты не вожатый группы!")
        return
    if not message.reply_to_message:
        await message.reply("Ответь на сообщение диггера!")
        return
    target_user = message.reply_to_message.from_user
    cooldowns = await load_data(GLOBAL_COOLDOWN_FILE)
    user_id_str = str(target_user.id)
    if user_id_str in cooldowns:
        del cooldowns[user_id_str]
        await save_data(cooldowns, GLOBAL_COOLDOWN_FILE)
        await message.reply(f"Таймер для {target_user.full_name} сброшен!")
    else:
        await message.reply("Этот диггер еще не делал вылазок!")

@dp.message(Command("chatstats"))
async def cmd_chat_stats(message: types.Message):
    if message.chat.type == "private":
        await message.reply("Я работаю только в чатах!")
        return
    if message.from_user.id not in ADMIN_IDS and message.from_user.id not in [1086796062, 1036331890]:
        await message.reply("Неизвестная команда")
        return
    chats_data = await load_data(CHATS_LIST_FILE)
    total_private = total_group = users_private = users_group = 0
    for chat_id_str, info in chats_data.items():
        chat_id = int(chat_id_str)
        chat_type = info.get("type", "group")
        bunker_file = get_bunker_file(chat_id)
        bunker_data = await load_data(bunker_file)
        num_users = len(bunker_data)
        if chat_type == "private":
            total_private += 1
            users_private += num_users
        else:
            total_group += 1
            users_group += num_users
    stats_text = (
        f"📊 Статистика бота:\n"
        f"Групповых чатов: {total_group}\n"
        f"Участников в группах: {users_group}\n"
        f"Личных чатов: {total_private}\n"
        f"Участников в личных чатах: {users_private}\n"
        f"Всего чатов: {total_group + total_private}\n"
        f"Всего участников: {users_group + users_private}"
    )
    await message.reply(stats_text)

async def send_post_to_all(reply_msg: types.Message, chat_id: int):
    chats_data = await load_data(CHATS_LIST_FILE)
    total_chats = len(chats_data)
    successful = 0
    progress_interval = 100
    for idx, chat_id_str in enumerate(list(chats_data.keys()), 1):
        target_chat_id = int(chat_id_str)
        wait = 1
        while True:
            try:
                if reply_msg.photo:
                    await bot.send_photo(chat_id=target_chat_id, photo=reply_msg.photo[-1].file_id, caption=reply_msg.caption or "")
                elif reply_msg.video:
                    await bot.send_video(chat_id=target_chat_id, video=reply_msg.video.file_id, caption=reply_msg.caption or "")
                elif reply_msg.text:
                    await bot.send_message(chat_id=target_chat_id, text=reply_msg.text)
                successful += 1
                break
            except Exception as e:
                if 'Too Many Requests' in str(e) or 'retry after' in str(e).lower():
                    await asyncio.sleep(wait)
                    wait = min(wait * 2, 60)
                else:
                    break
        if idx % progress_interval == 0:
            await bot.send_message(chat_id, f"Прогресс рассылки: {idx}/{total_chats} чатов обработано.")
        await asyncio.sleep(0.05)
    await bot.send_message(chat_id, f"✅ Рассылка завершена! Отправлено в {successful}/{total_chats} чатов.")

@dp.message(Command("post"))
async def cmd_post(message: types.Message):
    if message.chat.type == "private":
        await message.reply("Я работаю только в чатах!")
        return
    if message.from_user.id not in ADMIN_IDS and message.from_user.id not in [1086796062, 1036331890]:
        await message.reply("Неизвестная команда")
        return
    if not message.reply_to_message:
        await message.reply("Ответьте на сообщение, которое нужно разослать!")
        return
    chats_data = await load_data(CHATS_LIST_FILE)
    total_chats = len(chats_data)
    await message.reply(f"📤 Рассылка запущена в {total_chats} чатов.")
    asyncio.create_task(send_post_to_all(message.reply_to_message, message.chat.id))

async def load_promos():
    return await load_data(PROMO_FILE)

async def save_promos(promos):
    await save_data(promos, PROMO_FILE)

@dp.message(Command("promoadd"))
async def cmd_promoadd(message: types.Message):
    if message.from_user.id not in ADMIN_IDS and message.from_user.id not in [1086796062, 1036331890]:
        await message.reply("Неизвестная команда")
        return
    parts = message.text.split()
    try:
        amount = int(parts[1])
        uses = int(parts[2])
        code = parts[3]
    except:
        await message.reply("Использование: /promoadd <ГП-5> <кол-во использований> <код>")
        return
    promos = await load_promos()
    promos[code] = {
        "amount": amount,
        "uses": uses,
        "duration": 0,
        "used_by": {}
    }
    await save_promos(promos)
    await message.reply(f"Промокод {code} создан: {amount} ГП-5, {uses} использований")

@dp.message(Command("promo"))
async def cmd_promo(message: types.Message):
    global MAINTENANCE
    if MAINTENANCE == 1 and message.from_user.id not in ADMIN_IDS and message.from_user.id not in [1086796062, 1036331890]:
        await message.reply("Технические работы. Попробуйте позже.")
        return
    parts = message.text.split()
    try:
        code = parts[1]
    except:
        await message.reply("Использование: /promo <код>")
        return
    promos = await load_promos()
    if code not in promos:
        await message.reply("Промокод не найден!")
        return
    promo_data = promos[code]
    user_id = str(message.from_user.id)
    if user_id in promo_data["used_by"]:
        await message.reply("Вы уже использовали этот промокод!")
        return
    if promo_data["uses"] > -1 and len(promo_data["used_by"]) >= promo_data["uses"]:
        await message.reply("Промокод закончился.")
        return
    bunker_file = get_bunker_file(message.chat.id)
    bunker_data = await load_data(bunker_file)
    if user_id not in bunker_data:
        bunker_data[user_id] = {"gp5": 0, "username": message.from_user.full_name, "last_loot_type": None}
    bunker_data[user_id]["gp5"] += promo_data["amount"]
    bunker_data[user_id]["username"] = message.from_user.full_name
    await save_data(bunker_data, bunker_file)
    await update_global_stats(message.from_user.id, bunker_data[user_id]["gp5"], message.from_user.full_name)
    promo_data["used_by"][user_id] = datetime.now().isoformat()
    await save_promos(promos)
    await message.reply(f"Промокод активирован! Вы получили {promo_data['amount']} ГП-5. Всего у тебя: {bunker_data[user_id]['gp5']} ГП-5")

@dp.message(Command("promoinfo"))
async def cmd_promoinfo(message: types.Message):
    if message.from_user.id not in ADMIN_IDS and message.from_user.id not in [1086796062, 1036331890]:
        await message.reply("Неизвестная команда")
        return
    promos = await load_promos()
    if not promos:
        await message.reply("Нет активных промокодов")
        return
    info_text = "📊 Информация о промокодах:\n\n"
    for code, data in promos.items():
        info_text += f"🔹 {code}:\n"
        info_text += f" ГП-5: {data['amount']}\n"
        uses_limit = 'неограничено' if data['uses'] == -1 else data['uses']
        used_count = len(data['used_by'])
        info_text += f" Использований: {used_count}/{uses_limit}\n"
        info_text += f" Длительность: {data.get('duration', 0)}\n"
        info_text += f" Использовали: {used_count} пользователей\n\n"
    await message.reply(info_text)

@dp.message(Command("maintenance_on"))
async def cmd_maintenance_on(message: types.Message):
    global MAINTENANCE
    if message.from_user.id not in ADMIN_IDS and message.from_user.id not in [1086796062, 1036331890]:
        await message.reply("Неизвестная команда")
        return
    MAINTENANCE = 1
    await db['config'].replace_one({'_id': 'maintenance'}, {'_id': 'maintenance', 'value': 1}, upsert=True)
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, "Технические работы включены.")
        except:
            pass
    await message.reply("Технические работы включены.")

@dp.message(Command("maintenance_off"))
async def cmd_maintenance_off(message: types.Message):
    global MAINTENANCE
    if message.from_user.id not in ADMIN_IDS and message.from_user.id not in [1086796062, 1036331890]:
        await message.reply("Неизвестная команда")
        return
    MAINTENANCE = 0
    await db['config'].replace_one({'_id': 'maintenance'}, {'_id': 'maintenance', 'value': 0}, upsert=True)
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, "Технические работы отключены.")
        except:
            pass
    await message.reply("Технические работы отключены.")

async def main():
    global MAINTENANCE
    MAINTENANCE = await load_initial_maintenance()
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())