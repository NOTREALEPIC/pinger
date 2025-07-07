import os
import random
import asyncio
import aiohttp
import discord
import pytz
import threading
from flask import Flask
from datetime import datetime
from discord.ext import commands, tasks
from dotenv import load_dotenv

# Load env variables
load_dotenv()
TOKEN = os.getenv("TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
MESSAGE_ID = int(os.getenv("MESSAGE_ID"))

# Hardcoded Render URLs to ping
URLS = [
    "https://ego-c9gi.onrender.com/",
    "https://notepicbot.onrender.com",
    "https://render-test-ush9.onrender.com",
    "https://render-test-ush9.onrender.com"
]

# Discord bot setup
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Timezone and start time
IST = pytz.timezone("Asia/Kolkata")
START_TIME = datetime.now(IST).replace(hour=6, minute=0, second=0, microsecond=0)

# Flask server to keep bot alive
app = Flask(__name__)

@app.route('/')
def home():
    return "Uptime Bot is Running!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def start_flask():
    thread = threading.Thread(target=run_flask)
    thread.start()

# Ping Render URLs every 2–5 mins
@tasks.loop(seconds=0)
async def ping_render_urls():
    delay = random.randint(120, 300)
    await asyncio.sleep(delay)
    async with aiohttp.ClientSession() as session:
        tasks = [ping_url(session, url) for url in URLS]
        await asyncio.gather(*tasks)

async def ping_url(session, url):
    try:
        async with session.get(url) as response:
            print(f"[Ping] {url} - {response.status}")
    except Exception as e:
        print(f"[Ping Error] {url} - {e}")

# Update embed every 55 seconds
@tasks.loop(seconds=55)
async def update_uptime_embed():
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print("❌ Channel not found.")
        return

    try:
        message = await channel.fetch_message(MESSAGE_ID)
    except discord.NotFound:
        print("❌ Message not found.")
        return

    now = datetime.now(IST)
    uptime = now - START_TIME
    days = uptime.days
    hours, rem = divmod(uptime.seconds, 3600)
    minutes, seconds = divmod(rem, 60)

    embed = discord.Embed(
        title="🟢 **UPTIME MONITOR**",
        color=discord.Color.green()
    )
    embed.add_field(name="Start Time (IST)", value=START_TIME.strftime("%I:%M:%S %p"), inline=True)
    embed.add_field(name="Uptime", value=f"{days:02}:{hours:02}:{minutes:02}:{seconds:02}", inline=True)
    embed.add_field(name="Last Update (IST)", value=now.strftime("%I:%M:%S %p"), inline=False)

    await message.edit(embed=embed)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    if not ping_render_urls.is_running():
        ping_render_urls.start()
    if not update_uptime_embed.is_running():
        update_uptime_embed.start()

# Start everything
start_flask()
bot.run(TOKEN)
