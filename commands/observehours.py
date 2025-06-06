import logging
import os
import discord  # type: ignore
import sqlite3
import asyncio
import time
import config
from monitor_atc import get_atc_units
from alerts import send_alerts
import finder

bot_name = finder.bot_name
PREFIX = finder.find_prefix(bot_name)

# Command metadata
description = "Get notified and observe your training facility during specific hours."
usage = f"`{PREFIX}observehours <start_time> <end_time>`"
prerequisite = f"settraining"
long_description = f"{description} You must have set a training plan by using `{prerequisite}` before using this command. Time format: `HH:MM` (UTC)."
quickstart_optional = True

TRAINING_FACILITIES = {
    "S1": "GND",
    "S2": "TWR",
    "S3": "APP",
    "C1": "CTR"
}

import asyncio

async def handle(message, client):
    user_id = message.author.id
    args = message.content.split()
    usage = f"❌ **Usage:** `{PREFIX}observehours <start_time> <end_time>` (UTC, format HH:MM)"

    def check(m):
        return m.author == message.author and m.channel == message.channel

    # Prompt for missing arguments
    if len(args) >= 2:
        start_time = args[1]
    else:
        await message.channel.send("🕒 **Enter the start time (UTC) in HH:MM format:**")
        try:
            response = await client.wait_for('message', timeout=60, check=check)
            start_time = response.content.strip()
        except asyncio.TimeoutError:
            await message.channel.send("⏱️ **Timed out waiting for start time. Please try again.**")
            return

    if len(args) >= 3:
        end_time = args[2]
    else:
        await message.channel.send("🕒 **Enter the end time (UTC) in HH:MM format:**")
        try:
            response = await client.wait_for('message', timeout=60, check=check)
            end_time = response.content.strip()
        except asyncio.TimeoutError:
            await message.channel.send("⏱️ **Timed out waiting for end time. Please try again.**")
            return

    # Validate formats
    if not validate_time_format(start_time) or not validate_time_format(end_time):
        await message.channel.send("❌ **Invalid time format. Use HH:MM (UTC).**")
        return

    save_observehours(user_id, start_time, end_time)
    await message.channel.send(f"✅ **Your daily observation period is set from {start_time} to {end_time} UTC.**")

    
def validate_time_format(time_str):
    try:
        time.strptime(time_str, "%H:%M")
        return True
    except ValueError:
        return False

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
    logging.info(f"Saved observe hours for user {user_id}: {start_time} to {end_time}")