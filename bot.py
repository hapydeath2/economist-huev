import discord
from discord.ext import commands
import praw
import json
import os

TOKEN = os.getenv('DISCORD_TOKEN')

DATA_FILE = 'users_data.json'

SHOP_FILE = 'shop.json'

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

@bot.event
async def ready():
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

bot.run(TOKEN)

