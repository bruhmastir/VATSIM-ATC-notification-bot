import os
# import bot
import config
import discord  # type: ignore
import sqlite3
import asyncio
import time
from vatsim import get_vatsim_data

# Command metadata
description = "Get notified and observe your training facility when it comes online."
usage = f"{config.PREFIX}observe <duration_in_hours>"
long_description = f"{description} you must have set a training plan before using this command as it specifies which airport and position to track."

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
    
    # Validate duration input
    if len(args) != 2:
        await message.channel.send(f"❌ **Usage:** `{config.PREFIX}observe <duration_in_hours>`")
        return

    try:
        duration = float(args[1])
        if duration <= 0:
            raise ValueError
    except ValueError:
        await message.channel.send("❌ **Invalid duration. Please enter a positive number of hours.**")
        return

    # Fetch user training details
    conn = sqlite3.connect("vatsim_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT training_rating, training_tier, training_airport FROM user_training WHERE user_id = ?", (user_id,))
    training_info = cursor.fetchone()
    
    if not training_info:
        await message.channel.send(f"❌ **You must set your training with `{config.PREFIX}settraining` before using `{config.PREFIX}observe`.**")
        conn.close()
        return
    
    training_rating, training_tier, training_airport = training_info
    training_facility = TRAINING_FACILITIES.get(training_rating)
    
    if not training_facility:
        await message.channel.send("❌ **Your training rating does not map to a valid facility. Contact an admin.**")
        conn.close()
        return

    conn.close()
    
    # Observation logic
    expiration_time = time.time() + (duration * 3600)  # Convert hours to seconds
    active_observations[user_id] = {
        "airport": training_airport,
        "facility": training_facility,
        "expires_at": expiration_time,
        "message": None
    }

    await message.channel.send(f"✅ **Ready to observe `{training_facility}` at `{training_airport}` for {duration} hours...**")

    # Start monitoring
    await monitor_observation(user_id, client)

async def monitor_observation(user_id, client):
    """Continuously checks for the training facility status."""
    if user_id not in active_observations:
        return
    
    user_data = active_observations[user_id]
    training_airport = user_data["airport"]
    training_facility = user_data["facility"]
    expiration_time = user_data["expires_at"]

    while time.time() < expiration_time:
        vatsim_data = get_vatsim_data()
        atc_units = [c["callsign"] for c in vatsim_data["controllers"] if training_airport in c["callsign"]]

        facility_online = any(training_facility in callsign for callsign in atc_units)

        if facility_online and user_data["message"] is None:
            # Facility came online → Send a notification
            channel = await client.fetch_channel(int(os.getenv("DISCORD_CHANNEL_ID")))
            if channel:
                message = await channel.send(f"✅ **`{training_facility}` is now online at `{training_airport}`!** <@{user_id}>")
                user_data["message"] = message
        
        elif not facility_online and user_data["message"]:
            # Facility went offline → Edit the alert
            try:
                await user_data["message"].edit(content=f"❌ **`{training_facility}` is now offline at `{training_airport}`. Too late!** <@{user_id}>")
                user_data["message"] = None
            except discord.NotFound:
                pass  # Message was deleted

        await asyncio.sleep(60 if not bot.interval else bot.interval)  # type: ignore # Check every minute

    # Remove from active observations after duration expires
    del active_observations[user_id]
    print(f"Observation ended for user {user_id}")
