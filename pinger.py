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

# Timezone
IST = pytz.timezone("Asia/Kolkata")
START_TIME = None

# Lock to prevent race conditions
embed_lock = asyncio.Lock()

# Discord bot setup
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

# Render URLs with display names
RENDER_BOTS = {
    "EGO BOT": "https://ego-c9gi.onrender.com/",
    "NOTTHEREALEPIC": "https://notepicbot.onrender.com",
    "RENDER TEST": "https://render-test-ush9.onrender.com",
    "NIIMMAI": "https://pinger-xiz2.onrender.com",
    "EPIC GIVEAWAY BOT": "https://epicgiveawaybot.onrender.com"
}
bot_statuses = {name: "🔄 CHECKING..." for name in RENDER_BOTS}

# Update embed every 10 seconds
@tasks.loop(seconds=10)
async def update_uptime_embed():
    async with embed_lock:
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
        uptime = now - START_TIME if START_TIME else timedelta(0)
        if uptime.total_seconds() < 0:
            uptime = timedelta(seconds=0)

        # Format time
        start_str = START_TIME.strftime("%I:%M:%S %p")
        now_str = now.strftime("%I:%M:%S %p")
        days = uptime.days
        hours, rem = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(rem, 60)
        uptime_str = f"{days:02}:{hours:02}:{minutes:02}:{seconds:02}"

        # Build status text
        status_lines = []
        for name, status in bot_statuses.items():
            status_lines.append(f"{name.ljust(20)} ```{status}```")
        status_block = "\n".join(status_lines)

        # Create embed
        embed = discord.Embed(
            title="<a:GTALoading:1160144515621986325> UPTIME MONITOR",
            color=discord.Color.green()
        )
        embed.description = (
            f"START         ```{start_str}```\n"
            f"UPTIME        ```{uptime_str}```\n"
            f"LAST UPDATE   ```{now_str}```\n\n"
            f"{status_block}"
        )
        embed.set_footer(
            text="Updating every 10 sec",
            icon_url="https://cdn.discordapp.com/emojis/1160144515621986325.gif"
        )

        await message.edit(embed=embed)
        print(f"✅ Embed updated at {now_str}")

# Ping every URL & update status
@tasks.loop(seconds=60)
async def ping_render_urls():
    async with embed_lock:
        async with aiohttp.ClientSession() as session:
            for name, url in RENDER_BOTS.items():
                try:
                    async with session.get(url, timeout=5) as response:
                        if response.status == 200:
                            bot_statuses[name] = "ONLINE"
                        else:
                            bot_statuses[name] = "OFFLINE"
                except Exception:
                    bot_statuses[name] = "OFFLINE"

# Permission check
def is_admin_or_mod(interaction: discord.Interaction):
    if not interaction.guild or not interaction.user:
        return False
    if interaction.user.guild_permissions.administrator:
        return True
    allowed_roles = ["ROOT", "MOD"]
    user_roles = [role.name.upper() for role in interaction.user.roles]
    return any(role in user_roles for role in allowed_roles)

# /saym command
@bot.tree.command(name="saym", description="Send a dummy embed to a specified channel")
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

# Handle permission error
@saym.error
async def saym_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message("❌ You don’t have permission to use this command.", ephemeral=True)

# on_ready setup
@bot.event
async def on_ready():
    global START_TIME
    START_TIME = datetime.now(IST)
    print(f"✅ Logged in as {bot.user} at {START_TIME.strftime('%I:%M:%S %p')}")

    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching,
        name="A heart for bots, not humans... 100% synthetic love 💘⚙️"
    ))

    await bot.tree.sync()
    if not ping_render_urls.is_running():
        ping_render_urls.start()
    if not update_uptime_embed.is_running():
        update_uptime_embed.start()

# Start Flask and bot
start_flask()
bot.run(TOKEN)
