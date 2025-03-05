import sqlite3

import config

description = "Opt out of receiving alerts for specific ATC positions at an airport."
usage = f"{config.PREFIX}optout <ICAO> <position1> [position2] ..."

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
    conn = sqlite3.connect("vatsim_bot.db")
    cursor = conn.cursor()
    
    command_parts = message.content.split()
    if len(command_parts) < 3:
        await message.channel.send(f"Usage: {usage}")
        conn.close()
        return
    
    icao = command_parts[1].strip().upper()
    positions = {p.strip().upper() for p in command_parts[2:]}

    if not positions.issubset(VALID_POSITIONS):
        invalid_positions = positions - VALID_POSITIONS
        await message.channel.send(f"Invalid positions: {', '.join(invalid_positions)}. Choose from: DEL, GND, TWR, APP, DEP, CTR.")
        conn.close()
        return

    for position in positions:
        cursor.execute("""
            INSERT OR IGNORE INTO user_opt_outs (user_id, icao, position) VALUES (?, ?, ?)
        """, (user_id, icao, position))

    conn.commit()
    conn.close()
    
    await message.channel.send(f"You will no longer receive alerts for {', '.join(positions)} at {icao}.")
