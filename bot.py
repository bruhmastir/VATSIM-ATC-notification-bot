import traceback
import config
import discord # type: ignore
import asyncio
import os
import importlib
from database import init_db
from monitor import monitor_airports
from dotenv import load_dotenv # type: ignore
import sys
import finder

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
OWNER_ID = int(os.getenv("BOT_OWNER_ID"))
BOT_STATUS_CHANNEL_ID = int(os.getenv("BOT_STATUS_CHANNEL_ID"))

# Initialize database
init_db()

# Initialize Discord Client
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
client = discord.Client(intents=intents, status=f"Listening to {config.PREFIX}help")
finder.find_bot_name(client)
bot_name = finder.bot_name

command_prefix = f"{finder.find_prefix(bot_name)}"

# Dynamically load command modules
commands = {}
command_prefix = f"{command_prefix}"
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
    finder.find_bot_name(client)
    bot_name = finder.bot_name

    logging.info(f"Logged in as {client.user} {discord.utils.utcnow()}")
    command_prefix = f"{finder.find_prefix(bot_name)}"
    logging.info(f"Command prefix: {command_prefix}, bot name lower: {bot_name.lower()}, does bot name start with dev? {bot_name.lower().startswith('dev')}")

    bot_status_channel = await client.fetch_channel(BOT_STATUS_CHANNEL_ID)
    await bot_status_channel.send(f"**Bot online at {discord.utils.utcnow()} UTC.**\n")#Please note that seeing this message does not mean the bot was offline. The Discord API may change the connection anytime, thus generating this message.")
    await client.change_presence(status=discord.Status.online, activity=discord.Activity(type=discord.ActivityType.listening, name=f"{command_prefix}help"))

    await monitor_airports(client, interval=60)

@client.event
async def on_message(message):
    finder.find_bot_name(client)
    bot_name = finder.bot_name

    message_time = discord.utils.utcnow()
    if message.author == client.user:
        return
    command_prefix = f"{finder.find_prefix(bot_name)}"
    
    
    if message.content.startswith(command_prefix):
        logging.info(f"Command received: {message.content}")
        command_name = message.content[len(command_prefix):].split()[0]
        if command_name in commands:
            importlib.reload(commands[command_name])
            await commands[command_name].handle(message, client)
        elif command_name == "reload":
            if message.author.id == OWNER_ID:
                load_commands()
                await message.channel.send("Commands reloaded successfully.")
        exec_time = discord.utils.utcnow() - message_time
        logging.info(f"Command {command_name} executed in {exec_time.total_seconds()} seconds.")

@client.event
async def on_error(event, *args, **kwargs):
    from alerts import send_errors

    error_message = traceback.format_exc()  # Capture full traceback
    logging.error(f"Error in {event}:\n{error_message}")
    await send_errors(event, client, error_message) #send the error message, not sys.exc_info()

@client.event
async def on_disconnect():
    logging.error(f"Bot disconnected at {discord.utils.utcnow()}")
    bot_status_channel = await client.fetch_channel(BOT_STATUS_CHANNEL_ID)
    await bot_status_channel.send(f"Bot disconnected at {discord.utils.utcnow()} UTC")

# Start the bot
client.run(TOKEN)
