import sqlite3

import config


description = "Remove opt-in again to receive alerts for specific ATC positions again."
usage = f"{config.PREFIX}optin <ICAO> <position1> [position2] ..."

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

    for position in positions:
        cursor.execute("DELETE FROM user_opt_outs WHERE user_id = ? AND icao = ? AND position = ?", 
                       (user_id, icao, position))

    conn.commit()
    conn.close()
    
    await message.channel.send(f"You will now receive alerts for {', '.join(positions)} at {icao}.")
