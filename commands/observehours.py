import os
import discord  # type: ignore
import sqlite3
import asyncio
import time
import config
from monitor import get_atc_units
from alerts import send_alerts

# Command metadata
description = "Get notified and observe your training facility during specific hours."
usage = f"{config.PREFIX}observehours <start_time> <end_time>"
long_description = f"{description} You must have set a training plan before using this command. Time format: HH:MM (UTC)."
quickstart_optional = True

TRAINING_FACILITIES = {
    "S1": "GND",
    "S2": "TWR",
    "S3": "APP",
    "C1": "CTR"
}

async def handle(message, client):
    user_id = message.author.id
    args = message.content.split()
    
    if len(args) != 3:
        await message.channel.send(f"❌ **Usage:** `{config.PREFIX}observehours <start_time> <end_time>` (UTC, format HH:MM)")
        return

    start_time, end_time = args[1], args[2]
    if not validate_time_format(start_time) or not validate_time_format(end_time):
        await message.channel.send("❌ **Invalid time format. Use HH:MM (UTC).**")
        return

    save_observehours(user_id, start_time, end_time)
    await message.channel.send(f"✅ **Your daily observation period is set from {start_time} to {end_time} UTC.**")

async def check_observehours(client):
    conn = sqlite3.connect("vatsim_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, start_time, end_time FROM user_observe_hours")
    observe_users = cursor.fetchall()
    conn.close()

    while True:
        now = time.strftime("%H:%M", time.gmtime())
        for user_id, start_time, end_time in observe_users:
            if start_time <= now < end_time:
                await start_observing(user_id, client)
        await asyncio.sleep(3600)

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

def save_observehours(user_id, start_time, end_time):
    conn = sqlite3.connect("vatsim_bot.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_observe_hours (
            user_id INTEGER PRIMARY KEY,
            start_time TEXT,
            end_time TEXT,
            FOREIGN KEY (user_id) REFERENCES user_training(user_id)
        )
    """)
    cursor.execute("REPLACE INTO user_observe_hours (user_id, start_time, end_time) VALUES (?, ?, ?)", (user_id, start_time, end_time))
    conn.commit()
    conn.close()

async def start_observing(user_id, client):
    training_info = get_training_info(user_id)
    if not training_info:
        return

    training_rating, training_airport = training_info
    training_facility = TRAINING_FACILITIES.get(training_rating)
    if not training_facility:
        return
    
    atc_units = await get_atc_units(training_airport)
    facility_online = any(training_facility in callsign for callsign in atc_units)

    if facility_online:
        channel = await client.fetch_channel(int(os.getenv("DISCORD_CHANNEL_ID")))
        if channel:
            await channel.send(f"✅ **`{training_facility}` is now online at `{training_airport}`!** <@{user_id}>")
