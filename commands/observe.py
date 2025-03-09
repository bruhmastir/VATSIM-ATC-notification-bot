import os
import discord  # type: ignore
import sqlite3
import asyncio
import time
import config
from vatsim import get_vatsim_data
from monitor import get_atc_units
from alerts import send_alerts
import finder

bot_name = finder.bot_name
PREFIX = finder.find_prefix(bot_name)

# Command metadata
description = "Get notified and observe your training facility when it comes online."
usage = f"`{PREFIX}observe <duration_in_hours>`"
prerequisite = f"{PREFIX}settraining"
long_description = f"{description} You must have set a training plan by using `{prerequisite}` before using this command as it specifies which airport and position to track."
quickstart_optional = True

# Facility mapping based on training level
TRAINING_FACILITIES = {
    "S1": "GND",
    "S2": "TWR",
    "S3": "APP",
    "C1": "CTR"
}

active_observations = {}  # Tracks users actively observing

async def handle(message, client):
    user_id = message.author.id
    args = message.content.split()
    
    if len(args) != 2:
        await message.channel.send(f"❌ **Usage:** `{PREFIX}observe <duration_in_hours>`")
        return

    try:
        duration = float(args[1])
        if duration <= 0:
            raise ValueError
    except ValueError:
        await message.channel.send("❌ **Invalid duration. Please enter a positive number of hours.**")
        return

    training_info = get_training_info(user_id)
    if not training_info:
        await message.channel.send(f"❌ **You must set your training with `{PREFIX}settraining` before using `{PREFIX}observe`.**")
        return

    training_rating, training_airport = training_info
    training_facility = TRAINING_FACILITIES.get(training_rating)
    if not training_facility:
        await message.channel.send("❌ **Invalid training rating. Contact an admin.**")
        return
    
    expiration_time = time.time() + (duration * 3600)
    active_observations[user_id] = {
        "airport": training_airport,
        "facility": training_facility,
        "expires_at": expiration_time,
        "message": None
    }

    await message.channel.send(f"✅ **Observing `{training_facility}` at `{training_airport}` for {duration} hours...**")
    await monitor_observation(user_id, client)

async def monitor_observation(user_id, client):
    if user_id not in active_observations:
        return
    
    user_data = active_observations[user_id]
    training_airport = user_data["airport"]
    training_facility = user_data["facility"]
    expiration_time = user_data["expires_at"]

    while time.time() < expiration_time:
        atc_units = await get_atc_units(training_airport)
        facility_online = any(training_facility in callsign for callsign in atc_units)

        if facility_online and user_data["message"] is None:
            channel = await client.fetch_channel(int(os.getenv("DISCORD_CHANNEL_ID")))
            if channel:
                message = await channel.send(f"✅ **`{training_facility}` is now online at `{training_airport}`!** <@{user_id}>")
                user_data["message"] = message
        elif not facility_online and user_data["message"]:
            try:
                await user_data["message"].edit(content=f"❌ **`{training_facility}` is now offline at `{training_airport}`. Too late!** <@{user_id}>")
                user_data["message"] = None
            except discord.NotFound:
                pass

        await asyncio.sleep(60)
    
    del active_observations[user_id]


def validate_time_format(time_str):
    try:
        time.strptime(time_str, "%H:%M")
        return True
    except ValueError:
        return False

def get_training_info(user_id):
    conn = sqlite3.connect("vatsim_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT training_rating, training_airport FROM user_training WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result

