import logging
import discord  # type: ignore
import asyncio
import os
import importlib
import config
import finder

# Command metadata
description = "Guided setup tutorial for new users."
usage = f"{config.PREFIX}quickstart"

bot_name = finder.bot_name
prefix = finder.find_prefix(bot_name)

# ✅ Load all commands dynamically
def load_commands():
    command_dir = "commands"
    commands_info = {}
    
    for filename in os.listdir(command_dir):
        if filename.endswith(".py") and filename != "__init__.py" and filename != "quickstart.py":
            command_name = filename[:-3]
            module = importlib.import_module(f"commands.{command_name}")
            command_desc = getattr(module, "long_description", getattr(module, "description", "No description available."))
            command_usage = getattr(module, "usage", "No usage info available.")
            is_optional = getattr(module, "quickstart_optional", False) 
            prerequisite = getattr(module, "prerequisite", None) 
            commands_info[command_name] = (module.handle, command_desc, is_optional, prerequisite)
    
    return commands_info

# ✅ Load commands
COMMANDS = load_commands()

# ✅ Define the desired order of commands
COMMAND_ORDER = config.COMMAND_ORDER

async def handle(message, client):
    user = message.author
    await message.channel.send("🚀 **Welcome to the Quickstart Tutorial!** 🚀\nI will guide you through the essential commands step by step.")
    executed_commands = set()
    bot_name = finder.bot_name
    prefix = finder.find_prefix(bot_name)
    
    # ✅ Process commands in predefined order
    for command_name in COMMAND_ORDER:
        if command_name not in COMMANDS:
            continue  # Skip if command is missing
        
        command, description, optional, prerequisite = COMMANDS[command_name]
        await message.channel.send(f"**{command_name.title()}**: {description}")
        await asyncio.sleep(2)  # ✅ Delay to avoid overwhelming the user

        if prerequisite and prerequisite not in executed_commands:
            await message.channel.send(f"Since you did not run {prefix}{prerequisite}, you cannot run this command yet. Skipping this step.")
            continue
        
        if optional:
            await message.channel.send("Do you want to run this command? (yes/no)")
            try:
                response = await client.wait_for("message", check=lambda m: m.author == user, timeout=30)
                if response.content.lower() != "yes":
                    await message.channel.send("Skipping this step.")
                    continue
                else:
                    response = await message.channel.send(f"Running optional {prefix}{command_name}...")
                    await command(response, client)
                    logging.debug(f"message: {response}, content: {response.content}")
                    executed_commands.add(command_name)
                    await asyncio.sleep(1)  # ✅ Delay to avoid overwhelming the user
                    continue
            except asyncio.TimeoutError:
                await message.channel.send("Skipping due to no response.")
                continue
        
        response = await message.channel.send(f"Running {prefix}{command_name}...")
        await command(message, client)
        logging.debug(f"message: {message}, content: {message.content}")
        executed_commands.add(command_name)
        await asyncio.sleep(1)  # ✅ Delay to avoid overwhelming the user
    
    await message.channel.send("🎉 **Quickstart Tutorial Complete!** 🎉\nYou are now ready to use the bot.")
