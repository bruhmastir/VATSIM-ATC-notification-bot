import discord
import asyncio
import os
import importlib
from database import init_db
from monitor import monitor_airports
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
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
command_prefix = "!"
command_dir = "commands"

def load_commands():
    global commands
    commands.clear()
    for filename in os.listdir(command_dir):
        if filename.endswith(".py") and filename != "__init__.py":
            command_name = filename[:-3]  # Remove .py extension
            module = __import__(f"commands.{command_name}", fromlist=["handle", "description", "usage"])
            commands[command_name] = module
    print("Commands loaded dynamically.")

load_commands()

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    await monitor_airports(client, interval=60)

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    
    if message.content.startswith("!reload"):
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
