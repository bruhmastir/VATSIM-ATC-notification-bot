import datetime
import logging
import os
import discord  # type: ignore
import sqlite3
import asyncio
import time
import config
from vatsim import get_vatsim_data
from monitor_atc import get_atc_units
from alerts import send_alerts
import finder

bot_name = finder.bot_name
PREFIX = finder.find_prefix(bot_name)

# Command metadata
description = "Get notified and observe your training facility when it comes online."
usage = f"`{PREFIX}observe [duration_in_hours]`"
prerequisite = f"settraining"
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

    duration = None

    # Check if duration was provided
    if len(args) == 2:
        try:
            duration = float(args[1])
            if duration <= 0:
                raise ValueError
        except ValueError:
            await message.channel.send("❌ **Invalid duration. Please enter a positive number of hours.**")
            return
    else:
        # Prompt for duration
        await message.channel.send("🕒 **Up to how many hours from now will you be able to observe? (e.g. `1.5`)**")

        def check(m):
            return m.author == message.author and m.channel == message.channel

        try:
            response = await client.wait_for("message", timeout=60.0, check=check)
            try:
                duration = float(response.content)
                if duration <= 0:
                    raise ValueError
            except ValueError:
                await message.channel.send("❌ **Invalid duration. Please enter a positive number of hours.**")
                return
        except asyncio.TimeoutError:
            await message.channel.send("⏱️ **Observation setup timed out. Please try again.**")
            return

    training_info = finder.get_training_info(user_id)
    if not training_info:
        await message.channel.send(f"❌ **You must set your training with `{PREFIX}settraining` before using `{PREFIX}observe`.**")
        return

    training_rating, training_airport = training_info
    training_facility = TRAINING_FACILITIES.get(training_rating)
    if not training_facility:
        await message.channel.send("❌ **Invalid training rating. Contact an admin.**")
        return

    now = datetime.datetime.now(datetime.UTC)
    end_time = now + datetime.timedelta(0,(duration * 3600))

    save_observehours(user_id, now.strftime("%Y-%m-%d %H:%M:%S"), end_time.strftime("%Y-%m-%d %H:%M:%S"))

    await message.channel.send(f"✅ **Observing `{training_facility}` at `{training_airport}` for {duration} hours...**")

def save_observehours(user_id, start_time, end_time):
    conn = sqlite3.connect("vatsim_bot.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS temp_observe (
            user_id INTEGER PRIMARY KEY,
            start_date_time TEXT,
            end_date_time TEXT,
            FOREIGN KEY (user_id) REFERENCES user_training(user_id)
        )
    """)
    cursor.execute("REPLACE INTO temp_observe (user_id, start_date_time, end_date_time) VALUES (?, ?, ?)", (user_id, start_time, end_time))
    conn.commit()
    conn.close()
    logging.info(f"Saved temporary observe hours for user {user_id}: {start_time} to {end_time}")