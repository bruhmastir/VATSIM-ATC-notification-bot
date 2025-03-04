# import sqlite3

# # Command metadata
# description = "Opt out of receiving alerts for specific ATC positions at an airport."
# usage = "!optout <ICAO> <position>"

# VALID_POSITIONS = {"DEL", "GND", "TWR", "APP", "DEP", "CTR"}

# async def handle(message, client):
#     user_id = message.author.id
#     conn = sqlite3.connect("vatsim_bot.db")
#     cursor = conn.cursor()

#     # Ensure the user_opt_outs table exists
#     cursor.execute("""
#     CREATE TABLE IF NOT EXISTS user_opt_outs (
#         user_id TEXT PRIMARY KEY,
#         icao TEXT,
#         position TEXT
#     )
#     """)
#     conn.commit()
    
#     # Parse command arguments
#     command_parts = message.content.split()
#     if len(command_parts) < 3:
#         await message.channel.send("Usage: !optout <ICAO> <position>")
#         conn.close()
#         return
    
#     icao = command_parts[1].strip().upper()
#     position = command_parts[2].strip().upper()
    
#     if position not in VALID_POSITIONS:
#         await message.channel.send(f"Invalid position {position}. Choose from: DEL, GND, TWR, APP, DEP, CTR.")
#         conn.close()
#         return

#     # Insert into database (avoid duplicates with REPLACE)
#     cursor.execute("""
#         INSERT OR REPLACE INTO user_opt_outs (user_id, icao, position) VALUES (?, ?, ?)
#     """, (user_id, icao, position))
#     conn.commit()
#     conn.close()
    
#     await message.channel.send(f"You will no longer receive alerts for {position} at {icao}.")




import sqlite3

description = "Opt out of receiving alerts for specific ATC positions at an airport."
usage = "!optout <ICAO> <position1> [position2] ..."

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
        await message.channel.send("Usage: !optout <ICAO> <position1> [position2] ...")
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
