import asyncio
import sqlite3

import config
import finder

bot_name = finder.bot_name
PREFIX = f"{finder.find_prefix(bot_name)}"

description = "Opt out of receiving alerts for specific ATC positions at an airport."
usage = f"`{PREFIX}optout [ICAO] [position1] [position2] ...`"
quickstart_optional = True
prerequisite = f"register"

VALID_POSITIONS = {"DEL", "GND", "TWR", "APP", "DEP", "CTR"}

# ✅ Ensure table exists on startup
def setup_database():
    conn = sqlite3.connect("vatsim_bot.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_opt_outs (
            user_id INTEGER,
            icao TEXT,
            position TEXT,
            PRIMARY KEY (user_id, icao, position),
            FOREIGN KEY (user_id) REFERENCES user_ratings(user_id)
        )
    """)
    conn.commit()
    conn.close()

setup_database()

async def handle(message, client):
    user_id = message.author.id
    command_parts = message.content.split()
    usage = f"{PREFIX}optout <ICAO> <POSITION(S)>"

    def check_author(m):
        return m.author == message.author and m.channel == message.channel

    # Step 1: Get ICAO
    if len(command_parts) >= 2:
        icao = command_parts[1].strip().upper()
    else:
        await message.channel.send("🛫 **Which airport ICAO code would you like to opt out from?**")
        try:
            reply = await client.wait_for("message", timeout=60, check=check_author)
            icao = reply.content.strip().upper()
        except asyncio.TimeoutError:
            await message.channel.send("⏱️ **Command timed out. Please try again.**")
            return

    # Step 2: Get positions
    if len(command_parts) >= 3:
        positions = {p.strip().upper() for p in command_parts[2:]}
    else:
        await message.channel.send("🎯 **Which positions would you like to opt out from? (e.g. DEL GND TWR)**")
        try:
            reply = await client.wait_for("message", timeout=60, check=check_author)
            positions = {p.strip().upper() for p in reply.content.split()}
        except asyncio.TimeoutError:
            await message.channel.send("⏱️ **Command timed out. Please try again.**")
            return

    # Validate positions
    invalid_positions = positions - VALID_POSITIONS
    if invalid_positions:
        await message.channel.send(f"❌ **Invalid positions: {', '.join(invalid_positions)}.** Choose from: DEL, GND, TWR, APP, DEP, CTR.")
        return

    # Insert into DB
    conn = sqlite3.connect("vatsim_bot.db")
    cursor = conn.cursor()
    for position in positions:
        cursor.execute(
            "INSERT OR IGNORE INTO user_opt_outs (user_id, icao, position) VALUES (?, ?, ?)",
            (user_id, icao, position)
        )
    conn.commit()
    conn.close()

    await message.channel.send(f"✅ **You will no longer receive alerts for {', '.join(positions)} at {icao}.**")
    