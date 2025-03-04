# description = "Remove opt-out settings and receive alerts for a position again."
# usage = "!optin <ICAO> <position>"

# async def handle(message, client):
#     user_id = message.author.id
#     conn = sqlite3.connect("vatsim_bot.db")
#     cursor = conn.cursor()
    
#     command_parts = message.content.split()
#     if len(command_parts) < 3:
#         await message.channel.send("Usage: !optin <ICAO> <position>")
#         conn.close()
#         return
    
#     icao = command_parts[1].strip().upper()
#     position = command_parts[2].strip().upper()
    
#     if position not in VALID_POSITIONS:
#         await message.channel.send(f"Invalid position {position}. Choose from: DEL, GND, TWR, APP, DEP, CTR.")
#         conn.close()
#         return

#     # Remove from database
#     cursor.execute("DELETE FROM user_opt_outs WHERE user_id = ? AND icao = ? AND position = ?", 
#                    (user_id, icao, position))
#     conn.commit()
#     conn.close()
    
#     await message.channel.send(f"You will now receive alerts for {position} at {icao}.")











import sqlite3


description = "Remove opt-out settings and receive alerts for specific ATC positions again."
usage = "!optin <ICAO> <position1> [position2] ..."

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
        await message.channel.send("Usage: !optin <ICAO> <position1> [position2] ...")
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
