import telebot
from telebot import types
import os
from collections import defaultdict

TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "123456789"))
bot = telebot.TeleBot(TOKEN)

# In-memory storage
admin_levels = defaultdict(dict)   # chat_id -> {user_id: level}
prefixes = defaultdict(dict)       # chat_id -> {user_id: prefix}
banned = defaultdict(set)
muted = defaultdict(set)
warns = defaultdict(lambda: defaultdict(int))
chats_list = set()
messages_count = defaultdict(int)

permissions = {
    'add_admin': 5,
    'remove_admin': 5,
    'ban': 2,
    'unban': 2,
    'mute': 2,
    'unmute': 2,
    'warn': 1,
    'setprefix': 1,
    'removeprefix': 1,
    'changeprefix': 1,
}

def get_level(chat_id, user_id):
    if user_id == OWNER_ID:
        return 5
    return admin_levels[chat_id].get(user_id, 0)

def check_perm(chat_id, user_id, command):
    return get_level(chat_id, user_id) >= permissions.get(command, 0)

# Save chats and count messages
@bot.message_handler(func=lambda m: True, content_types=['text','photo','video','sticker','animation','voice'])
def any_message(msg):
    chats_list.add(msg.chat.id)
    messages_count[msg.chat.id] += 1
    if msg.from_user.id in banned[msg.chat.id] or msg.from_user.id in muted[msg.chat.id]:
        try:
            bot.delete_message(msg.chat.id, msg.message_id)
        except:
            pass

# OWNER command /chats
@bot.message_handler(commands=['chats'])
def chats(msg):
    if msg.from_user.id != OWNER_ID or msg.chat.type != 'private':
        return
    if not chats_list:
        return bot.reply_to(msg, "Бот пока ни в одном чате не состоит.")
    kb = types.InlineKeyboardMarkup()
    for cid in chats_list:
        try:
            chat = bot.get_chat(cid)
            name = chat.title if chat.title else chat.first_name
        except:
            name = str(cid)
        kb.add(types.InlineKeyboardButton(text=name, callback_data=f"chatinfo_{cid}"))
    bot.reply_to(msg, "Выберите чат:", reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data.startswith("chatinfo_"))
def chatinfo(call):
    if call.from_user.id != OWNER_ID:
        return bot.answer_callback_query(call.id, "Нет прав")
    cid = int(call.data.split("_")[1])
    try:
        chat = bot.get_chat(cid)
        name = chat.title if chat.title else chat.first_name
        # bot.get_chat_members_count not available in pyTelegramBotAPI, but .get_chat_members_count() is
        try:
            members = bot.get_chat_members_count(cid)
        except:
            members = "неизвестно"
    except Exception as e:
        return bot.answer_callback_query(call.id, f"Не могу получить чат: {e}")
    admins_count = len(admin_levels[cid])
    msg_count = messages_count[cid]
    text = f"**Информация о чате**\n"            f"Название: {name}\n"            f"ID: {cid}\n"            f"Участников: {members}\n"            f"Администраторов (в базе бота): {admins_count}\n"            f"Сообщений обработано: {msg_count}"
    bot.answer_callback_query(call.id)
    bot.send_message(call.from_user.id, text, parse_mode='Markdown')

# Example moderation command: /ban
@bot.message_handler(commands=['ban'])
def ban_user(msg):
    if not check_perm(msg.chat.id, msg.from_user.id, 'ban'):
        return bot.reply_to(msg, "Недостаточно прав")
    if not msg.reply_to_message:
        return bot.reply_to(msg, "Ответьте на сообщение пользователя")
    user_id = msg.reply_to_message.from_user.id
    if get_level(msg.chat.id, user_id) >= get_level(msg.chat.id, msg.from_user.id):
        return bot.reply_to(msg, "Нельзя банить админа с таким же или выше уровнем")
    banned[msg.chat.id].add(user_id)
    bot.reply_to(msg, "Пользователь забанен (сообщения будут удаляться)")

@bot.message_handler(commands=['unban'])
def unban_user(msg):
    if not check_perm(msg.chat.id, msg.from_user.id, 'unban'):
        return bot.reply_to(msg, "Недостаточно прав")
    if not msg.reply_to_message:
        return bot.reply_to(msg, "Ответьте на сообщение пользователя")
    user_id = msg.reply_to_message.from_user.id
    banned[msg.chat.id].discard(user_id)
    bot.reply_to(msg, "Пользователь разбанен")

@bot.message_handler(commands=['mute'])
def mute_user(msg):
    if not check_perm(msg.chat.id, msg.from_user.id, 'mute'):
        return bot.reply_to(msg, "Недостаточно прав")
    if not msg.reply_to_message:
        return bot.reply_to(msg, "Ответьте на сообщение пользователя")
    user_id = msg.reply_to_message.from_user.id
    if get_level(msg.chat.id, user_id) >= get_level(msg.chat.id, msg.from_user.id):
        return bot.reply_to(msg, "Нельзя замутить админа с таким же или выше уровнем")
    muted[msg.chat.id].add(user_id)
    bot.reply_to(msg, "Пользователь замьючен (сообщения будут удаляться)")

@bot.message_handler(commands=['unmute'])
def unmute_user(msg):
    if not check_perm(msg.chat.id, msg.from_user.id, 'unmute'):
        return bot.reply_to(msg, "Недостаточно прав")
    if not msg.reply_to_message:
        return bot.reply_to(msg, "Ответьте на сообщение пользователя")
    user_id = msg.reply_to_message.from_user.id
    muted[msg.chat.id].discard(user_id)
    bot.reply_to(msg, "Пользователь размьючен")

# start
print("Bot started")
bot.infinity_polling()
