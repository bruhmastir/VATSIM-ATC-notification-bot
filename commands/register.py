import config
import discord  # type: ignore
import sqlite3
from config import SUPPORTED_AIRPORTS  # Import supported airports from config.py
import finder

bot_name = finder.bot_name
PREFIX = finder.find_prefix(bot_name)

# Command metadata
description = "Register an airport for monitoring and set thresholds. Requires ATC rating to be set first."
usage = f"`{PREFIX}register <ICAO> [Primary] [Staff Up] [Cooldown] [Alert Preference] [Support Threshold]`"
quickstart_optional = False

def is_valid_number(value):
    try:
        return int(value) >= 0
    except ValueError:
        return False

async def handle(message, client):
    user_id = message.author.id
    conn = sqlite3.connect("vatsim_bot.db")
    cursor = conn.cursor()

    # Check if user has set ATC rating
    cursor.execute("SELECT atc_rating FROM user_ratings WHERE user_id = ?", (user_id,))
    user_rating = cursor.fetchone()
    if not user_rating:
        await message.channel.send(f"You must set your ATC rating first using {PREFIX}setrating before registering an airport.")
        conn.close()
        return

    def check(m): return m.author == message.author and m.channel == message.channel
    args = message.content.split()[1:]  # Extract arguments after !register

    # If number of arguments is not 1 (ICAO only) or 6 (Full command), use full interactive mode
    if not (len(args) == 1 or len(args) == 6):
        args = []  # Ignore provided arguments and switch to full interactive mode

    # ✅ Ask for ICAO code (use argument if provided)
    if args:
        icao = args[0].strip().upper()
        if icao not in SUPPORTED_AIRPORTS:
            await message.channel.send("Invalid ICAO code. Enter a valid airport from the supported list.")
            icao = None  # Mark ICAO as invalid to be asked interactively
    else:
        icao = None  # No ICAO argument provided → ask interactively

    while icao is None:
        await message.channel.send("Enter the ICAO code of the airport you want to monitor:")
        icao_response = await client.wait_for("message", check=check)
        icao = icao_response.content.strip().upper()

        if icao == "CANCEL":
            await message.channel.send("Registration process cancelled.")
            conn.close()
            return

        if icao not in SUPPORTED_AIRPORTS:
            await message.channel.send("Invalid ICAO code. Please enter a valid airport from the supported list.")
            icao = None  # Reset to ensure re-asking

    # ✅ Primary threshold
    primary_threshold = int(args[1]) if len(args) == 6 and is_valid_number(args[1]) else None
    while primary_threshold is None:
        await message.channel.send(f"The primary threshold is the minimum number of aircraft that should be on the ground for you to receive an alert.\n**Set primary threshold for {icao}:**")
        response = await client.wait_for("message", check=check)
        if response.content.strip().upper() == "CANCEL":
            await message.channel.send("Registration process cancelled.")
            conn.close()
            return
        if is_valid_number(response.content):
            primary_threshold = int(response.content)
        else:
            await message.channel.send("Invalid input. Please enter a valid number.")

    # ✅ Staff Up threshold (Must be ≥ Primary threshold)
    staff_up_threshold = int(args[2]) if len(args) == 6 and is_valid_number(args[2]) else None
    while staff_up_threshold is None or staff_up_threshold < primary_threshold:
        await message.channel.send(f"The staff up threshold is the minimum number of aircraft that should be on the ground when another ATC facility is online for you to receive and alert.\n**Set staff up threshold for {icao} (must be ≥ {primary_threshold}):**")
        response = await client.wait_for("message", check=check)
        if response.content.strip().upper() == "CANCEL":
            await message.channel.send("Registration process cancelled.")
            conn.close()
            return
        if is_valid_number(response.content) and int(response.content) >= primary_threshold:
            staff_up_threshold = int(response.content)
        else:
            await message.channel.send(f"Invalid input. Must be a number ≥ {primary_threshold}.")

    # ✅ Cooldown time
    cooldown = int(args[3]) if len(args) == 6 and is_valid_number(args[3]) else None
    while cooldown is None:
        await message.channel.send(f"The cooldown is the minimum amount of time that should pass before you receive a new alert about the same airport.\n**Set cooldown time in minutes for {icao}:**")
        response = await client.wait_for("message", check=check)
        if response.content.strip().upper() == "CANCEL":
            await message.channel.send("Registration process cancelled.")
            conn.close()
            return
        if is_valid_number(response.content):
            cooldown = int(response.content)
        else:
            await message.channel.send("Invalid input. Please enter a valid number.")

    # ✅ Alert preference (channel or dm)
    alert_preference = args[4].strip().lower() if len(args) == 6 and args[4].strip().lower() in ["channel", "dm"] else None
    while alert_preference is None:
        await message.channel.send("Do you want to receive alerts in the channel or in your DMs? (Type `channel` or `dm`)")
        response = await client.wait_for("message", check=check)
        alert_preference = response.content.strip().lower()

        if alert_preference.upper() == "CANCEL":
            await message.channel.send("Registration process cancelled.")
            conn.close()
            return

        if alert_preference not in ["channel", "dm"]:
            await message.channel.send("Invalid choice. Please type `channel` or `dm`.")
            alert_preference = None

    # ✅ Support threshold
    support_threshold = int(args[5]) if len(args) == 6 and is_valid_number(args[5]) else None
    while support_threshold is None:
        await message.channel.send(f"The support threshold is the minimum number of aircraft that should be on the ground for you to receive an alert when someone uses {PREFIX}supportme \n**Set support threshold for {icao}:**")
        response = await client.wait_for("message", check=check)
        if response.content.strip().upper() == "CANCEL":
            await message.channel.send("Registration process cancelled.")
            conn.close()
            return
        if is_valid_number(response.content):
            support_threshold = int(response.content)
        else:
            await message.channel.send("Invalid input. Please enter a valid number.")

    # ✅ Store the data in the database
    try:
        cursor.execute("""
            REPLACE INTO user_preferences (user_id, icao, primary_threshold, staff_up_threshold, cooldown, alert_preference, support_threshold)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, icao, primary_threshold, staff_up_threshold, cooldown, alert_preference, support_threshold))
        conn.commit()
    except ValueError:
        await message.channel.send(f"Invalid values for {icao}, registration skipped.")
        conn.close()
        return

    # ✅ Ask if user wants to add another airport
    await message.channel.send("Do you want to add another airport? (yes/no)")
    add_more_response = await client.wait_for("message", check=check)
    if add_more_response.content.lower() == "yes":
        conn.close()
        await handle(message, client)  # Restart for new airport
    else:
        await message.channel.send("Registration complete!")
        conn.close()
