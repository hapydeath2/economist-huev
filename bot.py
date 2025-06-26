import discord
from discord.ext import commands
import json
import os
import asyncio
import datetime

TOKEN = os.getenv('DISCORD_TOKEN')

# Базовая директория для хранения данных.
# Этот путь ТОЧНО соответствует Mount Path вашего Volume в Railway (например, '/data').
DATA_DIR = '/data'

DATA_FILE = os.path.join(DATA_DIR, 'users_data.json')
SHOP_FILE = os.path.join(DATA_DIR, 'shop.json')

ROLE_FOR_SHOP_ADDS = 1383053097672380456

OWNER_DISCORD_ID = 502834249666265089 # <-- ЗАМЕНИТЕ ЭТОТ ПЛЕЙСХОЛДЕР НА ВАШ ID!

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

def load_data():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"[{datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC] Error decoding JSON from {DATA_FILE}. Returning empty data.")
        return {}
    except Exception as e:
        print(f"[{datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC] An error occurred while loading data: {e}")
        return {}


def save_data(data):
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"[{datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC] An error occurred while saving data: {e}")

def load_shop():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(SHOP_FILE):
        return []
    try:
        with open(SHOP_FILE, "r", encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"[{datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC] Error decoding JSON from {SHOP_FILE}. Returning empty shop.")
        return []
    except Exception as e:
        print(f"[{datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC] An error occurred while loading shop: {e}")
        return []


def save_shop(shop):
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)
    try:
        with open(SHOP_FILE, "w", encoding='utf-8') as f:
            json.dump(shop, f, indent=4)
    except Exception as e:
        print(f"[{datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC] An error occurred while saving shop: {e}")

def add_user_if_needed(user_id):
    data = load_data()
    user_id = str(user_id)
    if user_id not in data:
        data[user_id] = {"coins": 0, "daily_streak":0}
        save_data(data)

def add_coins(user_id, amount):
    data = load_data()
    user_id=str(user_id)
    if user_id not in data:
        data[user_id] = {"coins": 0, "daily_streak":0}
    data[user_id]["coins"] += amount
    save_data(data)

async def send_backup_to_owner():
    await bot.wait_until_ready()
    owner = bot.get_user(OWNER_DISCORD_ID)
    if not owner:
        print(f"[{datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC] Owner user {OWNER_DISCORD_ID} not found. Cannot send backup.")
        return

    print(f"[{datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC] Attempting to send backup to owner (ID: {OWNER_DISCORD_ID}).")
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'rb') as f:
                await owner.send("Ежедневный бэкап: users_data.json", file=discord.File(f, 'users_data.json'))
        else:
            await owner.send("Ежедневный бэкап: users_data.json не найден.")

        if os.path.exists(SHOP_FILE):
            with open(SHOP_FILE, 'rb') as f:
                await owner.send("Ежедневный бэкап: shop.json", file=discord.File(f, 'shop.json'))
        else:
            await owner.send("Ежедневный бэкап: shop.json не найден.")

        print(f"[{datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC] Backup sent successfully to owner.")

    except Exception as e:
        print(f"[{datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC] Error sending backup to owner: {e}")

async def scheduled_backup_task():
    await bot.wait_until_ready()
    print(f"[{datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC] Starting scheduled backup task.")
    await asyncio.sleep(60)
    await send_backup_to_owner()

    while not bot.is_closed():
        await asyncio.sleep(24 * 60 * 60)
        await send_backup_to_owner()

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)
        print(f"Created data directory: {DATA_DIR}")

    data = load_data()
    added = 0
    for guild in bot.guilds:
        for member in guild.members:
            if member.bot:
                continue
            if str(member.id) not in data:
                data[str(member.id)] = {"coins": 0, "daily_streak":0}
                added+=1
    save_data(data)
    print(f"Добавлено {added} пользователей в базу данных")

    bot.loop.create_task(scheduled_backup_task())

@bot.event
async def on_member_join(member):
    if not member.bot:
        add_user_if_needed(member.id)

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    add_coins(message.author.id, 1)
    await bot.process_commands(message)

@bot.command()
async def shop(ctx):
    shop_items = load_shop()
    embed = discord.Embed(title="🛒 Магазин ролей", color=discord.Color.blue())

    if not shop_items:
        embed.description = "Магазин пуст. Добавьте роли с помощью команды `!addrole`."
    else:
        for i, item in enumerate(shop_items, start=1):
            embed.add_field(
                name=f"{i}. {item['name']}",
                value=f"Цена: {item['price']} монет",
                inline=False
            )
    await ctx.send(embed=embed)

@bot.command()
async def buy(ctx, номер: int):
    shop_items = load_shop()
    data = load_data()
    user_id = str(ctx.author.id)

    if номер < 1 or номер > len(shop_items):
        await ctx.send("Неверный номер роли")
        return
    item = shop_items[номер - 1]
    role = ctx.guild.get_role(item["id"])
    if not role:
        await ctx.send("Роль не найдена на сервере")
        return
    if user_id not in data or data[user_id]["coins"] < item["price"]:
        await ctx.send("Блядский нищий хуй")
        return
    if role in ctx.author.roles:
        await ctx.send("У тебя уже есть эта роль, жадный ты ублюдок")
        return
    try:
        await ctx.author.add_roles(role)
    except discord.Forbidden:
        await ctx.send("У бота прав нет нихуя чтобы выдать эту роль")
        return
    data[user_id]["coins"] -= item["price"]
    save_data(data)
    await ctx.send(f"Вы приобрели роль **{role.name}** за {item['price']} монет")

@bot.command()
async def users(ctx):
    data = load_data()

    if not data:
        await ctx.send("База данных пуста")
        return
    lines = []
    sorted_users = sorted(data.items(), key=lambda item: item[1].get("coins", 0), reverse=True)

    for user_id, user_data in sorted_users:
        member = ctx.guild.get_member(int(user_id))
        if member:
            name = member.display_name
        else:
            name = f"Пользователь ({user_id})"
        coins = user_data.get("coins", 0)
        lines.append(f" **{name}** - {coins} монет")

    message = "💰 **Балансы пользователей:**\n" + "\n".join(lines)

    if len(message) > 1900:
        chunks = [message[i:i+1900] for i in range(0, len(message), 1900)]
        for chunk in chunks:
            await ctx.send(chunk)
    else:
        await ctx.send(message)

@bot.command()
async def addrole(ctx):
    author_roles_ids = [r.id for r in ctx.author.roles]
    if ROLE_FOR_SHOP_ADDS not in author_roles_ids:
        msg = await ctx.send("Ты че выебываешься тупиздень у тебя прав нет")
        await asyncio.sleep(10)
        await msg.delete()
        await ctx.message.delete()
        return

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    # Сохраняем сообщение бота с вопросом о названии роли
    prompt_role_name_msg = await ctx.send("Введите название роли:")
    user_role_name_reply = None # Переменная для ответа пользователя

    try:
        user_role_name_reply = await bot.wait_for('message', check=check, timeout=60)
        role_name = user_role_name_reply.content.strip()
    except asyncio.TimeoutError:
        timeout_msg = await ctx.send("Ебать ты тормоз конечно")
        await asyncio.sleep(10)
        await timeout_msg.delete()
        # Удаляем сообщения: вопрос бота, команду пользователя
        if prompt_role_name_msg: await prompt_role_name_msg.delete()
        if ctx.message: await ctx.message.delete()
        return

    # Сохраняем сообщение бота с вопросом о цене
    prompt_price_msg = await ctx.send("Введите цену роли: ")
    user_price_reply = None # Переменная для ответа пользователя

    try:
        user_price_reply = await bot.wait_for('message', check=check, timeout=60)
        price = int(user_price_reply.content.strip())
        if price < 0:
            raise ValueError
    except asyncio.TimeoutError:
        timeout_msg = await ctx.send("Ну и хули ты молчишь быдло")
        await asyncio.sleep(10)
        await timeout_msg.delete()
        # Удаляем все сообщения, связанные с текущим диалогом:
        if prompt_role_name_msg: await prompt_role_name_msg.delete()
        if user_role_name_reply: await user_role_name_reply.delete()
        if prompt_price_msg: await prompt_price_msg.delete()
        if ctx.message: await ctx.message.delete()
        return
    except ValueError:
        error_msg = await ctx.send("Ебать ты тупейший просто, число введи сука")
        await asyncio.sleep(10)
        await error_msg.delete()
        # Удаляем все сообщения, связанные с текущим диалогом:
        if prompt_role_name_msg: await prompt_role_name_msg.delete()
        if user_role_name_reply: await user_role_name_reply.delete()
        if prompt_price_msg: await prompt_price_msg.delete()
        if user_price_reply: await user_price_reply.delete() # Удаляем неверный ответ пользователя
        if ctx.message: await ctx.message.delete()
        return

    existing_role = discord.utils.get(ctx.guild.roles, name=role_name)
    if existing_role:
        response_msg = await ctx.send(f"Роль с именем **{role_name}** уже существует на сервере. Используйте ее ID для добавления в магазин.")
        await ctx.send(f"Чтобы добавить существующую роль в магазин, используйте команду `!addexistingrole <RoleID> <Price>`.")
        await asyncio.sleep(10)
        await response_msg.delete()
        # Удаляем все сообщения, связанные с текущим диалогом:
        if prompt_role_name_msg: await prompt_role_name_msg.delete()
        if user_role_name_reply: await user_role_name_reply.delete()
        if prompt_price_msg: await prompt_price_msg.delete()
        if user_price_reply: await user_price_reply.delete()
        if ctx.message: await ctx.message.delete()
        return

    try:
        role = await ctx.guild.create_role(name=role_name)
    except discord.Forbidden:
        msg = await ctx.send("Ну я нищета без прав(")
        await asyncio.sleep(10)
        await msg.delete()
        # Удаляем все сообщения, связанные с текущим диалогом:
        if prompt_role_name_msg: await prompt_role_name_msg.delete()
        if user_role_name_reply: await user_role_name_reply.delete()
        if prompt_price_msg: await prompt_price_msg.delete()
        if user_price_reply: await user_price_reply.delete()
        if ctx.message: await ctx.message.delete()
        return

    shop_items = load_shop()
    for item in shop_items:
        if item['id'] == role.id:
            msg = await ctx.send(f"Роль **{role.name}** уже есть в магазине")
            await asyncio.sleep(10)
            await msg.delete()
            # Удаляем все сообщения, связанные с текущим диалогом:
            if prompt_role_name_msg: await prompt_role_name_msg.delete()
            if user_role_name_reply: await user_role_name_reply.delete()
            if prompt_price_msg: await prompt_price_msg.delete()
            if user_price_reply: await user_price_reply.delete()
            if ctx.message: await ctx.message.delete()
            return
            
    shop_items.append({
        "id": role.id,
        "name": role.name,
        "price": price
    })

    save_shop(shop_items)

    confirm_msg = await ctx.send(f"Роль **{role_name}** добавлена в магазин за {price} монет")

    await asyncio.sleep(10) # Даем 10 секунд на прочтение подтверждения
    # Удаляем все сообщения, которые должны быть удалены после завершения процесса
    messages_to_delete = [
        confirm_msg,
        prompt_role_name_msg,
        user_role_name_reply,
        prompt_price_msg,
        user_price_reply,
        ctx.message # Изначальная команда пользователя (!addrole)
    ]

    for msg_obj in messages_to_delete:
        if msg_obj: # Проверяем, что объект сообщения существует (не None)
            try:
                await msg_obj.delete()
            except discord.NotFound:
                # Если сообщение уже удалено или не найдено, это нормально.
                pass
            except discord.Forbidden:
                # Если у бота нет прав на удаление этого сообщения.
                print(f"[{datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC] Bot does not have permissions to delete a message: {msg_obj.id}")
            except Exception as e:
                print(f"[{datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC] Error deleting message {msg_obj.id}: {e}")


@bot.command()
async def addexistingrole(ctx, role_id: int, price: int):
    author_roles_ids = [r.id for r in ctx.author.roles]
    if ROLE_FOR_SHOP_ADDS not in author_roles_ids:
        msg = await ctx.send("Ты че выебываешься тупиздень у тебя прав нет")
        await asyncio.sleep(10)
        await msg.delete()
        await ctx.message.delete()
        return

    role = ctx.guild.get_role(role_id)
    if not role:
        await ctx.send("Роль с таким ID не найдена на сервере.")
        return

    if price < 0:
        await ctx.send("Цена не может быть отрицательной.")
        return

    shop_items = load_shop()
    for item in shop_items:
        if item['id'] == role.id:
            await ctx.send(f"Роль **{role.name}** (ID: {role.id}) уже есть в магазине.")
            return

    shop_items.append({
        "id": role.id,
        "name": role.name,
        "price": price
    })
    save_shop(shop_items)
    await ctx.send(f"Существующая роль **{role.name}** (ID: {role.id}) добавлена в магазин за {price} монет.")

@bot.command()
async def manual_backup(ctx):
    if ctx.author.id != OWNER_DISCORD_ID:
        await ctx.send("У вас нет прав на эту команду.")
        return

    await ctx.send("Запускаю ручной бэкап... Проверьте свои личные сообщения.")
    await send_backup_to_owner()
    await ctx.send("Ручной бэкап завершен.")

bot.run(TOKEN)
