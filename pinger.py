import os
import random
import asyncio
import aiohttp
import discord
import pytz
import threading
from flask import Flask
from datetime import datetime, timedelta
from discord.ext import commands, tasks
from discord import app_commands
from dotenv import load_dotenv

# Load env variables
load_dotenv()
TOKEN = os.getenv("TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
MESSAGE_ID = int(os.getenv("MESSAGE_ID"))

# Hardcoded Render URLs
URLS = [
    "https://ego-c9gi.onrender.com/",
    "https://notepicbot.onrender.com",
    "https://render-test-ush9.onrender.com",
    "https://pinger-xiz2.onrender.com",
    "https://epicgiveawaybot.onrender.com"
]

# Timezone and start time
IST = pytz.timezone("Asia/Kolkata")
START_TIME = datetime.now(IST)  # Dynamic uptime start

# Discord bot setup with proper intents
intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Flask app for uptime
app = Flask(__name__)

@app.route('/')
def home():
    return "Uptime Bot is Running!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def start_flask():
    thread = threading.Thread(target=run_flask)
    thread.daemon = True
    thread.start()

# Ping Render URLs every 2–5 minutes
@tasks.loop(seconds=60)
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

# Update uptime embed every 10 seconds
@tasks.loop(seconds=10)
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

    if uptime.total_seconds() < 0:
        uptime = timedelta(seconds=0)  # Fix negative value

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

# Admin OR "ROOT" / "MOD" role check
def is_admin_or_mod(interaction: discord.Interaction):
    if not interaction.guild or not interaction.user:
        return False
    if interaction.user.guild_permissions.administrator:
        return True
    allowed_roles = ["ROOT", "MOD"]
    user_roles = [role.name.upper() for role in interaction.user.roles]
    return any(role in user_roles for role in allowed_roles)

# /saym command - send a dummy embed to a channel
@bot.tree.command(
    name="saym",
    description="Send a dummy embed to a specified channel (admin or mod only)"
)
@app_commands.check(is_admin_or_mod)
@app_commands.describe(channel="The channel to send the dummy embed")
async def saym(interaction: discord.Interaction, channel: discord.TextChannel):
    await interaction.response.defer(ephemeral=True)

    try:
        embed = discord.Embed(
            title="📦 Dummy Embed",
            description="This is a sample embed sent by the bot.",
            color=discord.Color.purple()
        )
        embed.set_footer(text="Sent by /saym command")

        await channel.send(embed=embed)
        await interaction.followup.send(f"✅ Embed sent to {channel.mention}.")
    except Exception as e:
        await interaction.followup.send(f"⚠️ Failed to send embed: `{e}`")

# Handle permission errors
@saym.error
async def saym_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message("❌ You don’t have permission to use this command.", ephemeral=True)

# Bot ready event
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    
    # Set bot activity
    activity = discord.Activity(type=discord.ActivityType.watching, name="A heart for bots, not humans... 100% synthetic love 💘⚙️")
    await bot.change_presence(activity=activity)

    await bot.tree.sync()

    if not ping_render_urls.is_running():
        ping_render_urls.start()

    if not update_uptime_embed.is_running():
        update_uptime_embed.start()

# Start Flask and bot
start_flask()
bot.run(TOKEN)
