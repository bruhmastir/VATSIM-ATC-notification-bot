import config
import discord # type: ignore
import asyncio
import os
import importlib
from database import init_db
from monitor import monitor_airports
from dotenv import load_dotenv # type: ignore
import sys

# Redirect print statements to bot.log
# log_file = open("bot_prints.log", "a", encoding="utf-8", buffering=1)  # Append mode
# sys.stdout = log_file  # Redirect standard output (print statements)
# sys.stderr = log_file  # Redirect errors

import logging
from logging.handlers import TimedRotatingFileHandler

log_handler = TimedRotatingFileHandler(
    'bot.log',
    when='midnight',  # Rotate daily at midnight
    interval=1,
    backupCount=10  # Keep 7 days' worth of logs
)
logging.basicConfig(
    handlers=[log_handler],
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Print large ######## rows so that it is easier to differentiate runs in log
logging.info("############################################################################################################################")
logging.info("############################################################################################################################")
logging.info("############################################################################################################################")
logging.info("############################################################################################################################")
logging.info("############################################################################################################################")
logging.info("############################################################################################################################")

# Load environment variables
load_dotenv(".env")
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))
OWNER_ID = int(os.getenv("BOT_OWNER_ID"))  # Bot owner ID

# Initialize database
init_db()

# Initialize Discord Client
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
client = discord.Client(intents=intents)

# Dynamically load command modules
commands = {}
command_prefix = f"{config.PREFIX}"
command_dir = "commands"

def load_commands():
    global commands
    commands.clear()
    for filename in os.listdir(command_dir):
        if filename.endswith(".py") and filename != "__init__.py":
            command_name = filename[:-3]  # Remove .py extension
            module = __import__(f"commands.{command_name}", fromlist=["handle", "description", "usage"])
            commands[command_name] = module
    logging.info("Commands loaded dynamically.")

load_commands()

@client.event
async def on_ready():
    logging.info(f"Logged in as {client.user} {discord.utils.utcnow()}")
    owner = await client.fetch_user(OWNER_ID)
    await owner.send(f"Logged in as {client.user} {discord.utils.utcnow()}")
    await monitor_airports(client, interval=60)

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    
    if message.content.startswith(f"{command_prefix}reload"):
        if message.author.id != OWNER_ID:
            #await message.channel.send("You do not have permission to reload commands.")
            return
        load_commands()
        await message.channel.send("Commands reloaded successfully.")
        return
    
    if message.content.startswith(command_prefix):
        command_name = message.content[len(command_prefix):].split()[0]
        if command_name in commands:
            importlib.reload(commands[command_name])
            await commands[command_name].handle(message, client)

# Start the bot
client.run(TOKEN)
