import discord
from discord.ext import commands
import praw
import json
import os
import asyncio
import subprocess
import datetime

TOKEN = os.getenv('DISCORD_TOKEN')

DATA_FILE = 'users_data.json'

SHOP_FILE = 'shop.json'

ROLE_FOR_SHOP_ADDS = 1383053097672380456

intents = discord.Intents.default()
intents.message_content = True 
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

def load_data():
    if not os.path.exists(DATA_FILE):
        return{}
    with open(DATA_FILE, 'r') as f:
        return json.load(f)
    
def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def load_shop():
    if not os.path.exists(SHOP_FILE):
        return[]
    with open(SHOP_FILE, "r") as f:
        return json.load(f)

def save_shop(shop):
    with open(SHOP_FILE, "w") as f:
        json.dump(shop, f, indent=4)
    
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

async def auto_commit_task():
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            subprocess.run(["git", "config", "user.name", "railway-bot"], check=True)
            subprocess.run(["git", "config", "user.email", "railway@bot.com"], check=True)
            subprocess.run(["git", "add", "users_data.json", "shop.json"], check=True)
            now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            subprocess.run(["git", "commit", "-m", f"Auto-update from Railway at {now} UTC"], check=False)
            subprocess.run([
                "git", "push",
                f"https://{os.getenv('GH_PUSH_TOKEN')}@github.com/hapydeath2/economist-huev.git"
            ], check=False)
            print(f"[{now}] Коммит отправлен")
        except Exception as e:
            print("Ошибка при автокоммите:", e)
        await asyncio.sleep(3600)
@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
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
    print(f"Добавленно {added} пользователей в базу данных")

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
    shop = load_shop()
    embed = discord.Embed(title="🛒 Магазин ролей", color=discord.Color.blue())

    for i, item in enumerate(shop, start=1):
        embed.add_field(
            name=f"{i}. {item['name']}",
            value=f"Цена: {item['price']} монет",
            inline=False
        )
    await ctx.send(embed=embed)

@bot.command()
async def buy(ctx, номер: int):
    shop = load_shop()
    data = load_data()
    user_id = str(ctx.author.id)
    
    if номер < 1 or номер > len(shop):
        await ctx.send("Неверный номер роли")
        return
    item = shop[номер - 1]
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
    for user_id in data:
        member = ctx.guild.get_member(int(user_id))
        if member:
            name = member.display_name
        else:
            name = f"Пользователь ({user_id})"
        coins = data[user_id].get("coins", 0)
        lines.append(f" **{name}** - {coins} монет")
    message = "\n".join(lines)
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
    await ctx.send("Введите название роли:")
    try:
        role_msg = await bot.wait_for('message', check=check, timeout=60)
    except asyncio.TimeoutError:
        msg = await ctx.send("Ебать ты тормоз конечно")
        await asyncio.sleep(10)
        await msg.delete()
        return
    
    role_name = role_msg.content.strip()

    await ctx.send("Введите цену роли: ")

    try:
        price_msg = await bot.wait_for('message', check=check, timeout=60)
    except:
        msg = await ctx.send("Ну и хули ты молчишь быдло")
        await asyncio.sleep(10)
        await msg.delete()
        return
    
    try:
        price = int(price_msg.content.strip())
        if price<0:
            raise ValueError
    except ValueError:
        msg = await ctx.send("Ебать ты тупейший просто, число введи сука")
        await asyncio.sleep(10)
        await msg.delete()
        await role_msg.delete()
        await price_msg.delete()
        return
    
    try:
        role = await ctx.guild.create_role(name=role_name)
    except discord.Forbidden:
        msg = await ctx.send("Ну я нищета без прав(")
        await asyncio.sleep(10)
        await msg.delete()
        await role_msg.delete()
        await price_msg.delete()
        return

    shop = load_shop()

    for item in shop:
        if item['id'] == role.id:
            msg = await ctx.send(f"Роль **{role.name}** уже есть в магазине")
            await asyncio.sleep(10)
            await msg.delete()
            return
    shop.append({
        "id": role.id,
        "name": role.name,
        "price": price
    })

    save_shop(shop)

    confirm_msg = await ctx.send(f"Роль **{role_name}** добавлена в магазин за {price} монет")

    await asyncio.sleep(10)
    await confirm_msg.delete()
    await role_msg.delete()
    await price_msg.delete()
    await ctx.message.delete()

bot.loop.create_task(auto_commit_task())
bot.run(TOKEN)

