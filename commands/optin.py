import sqlite3

import config
import finder

bot_name = finder.bot_name
PREFIX = finder.find_prefix(bot_name)


description = "Remove opt-in again to receive alerts for specific ATC positions again."
usage = f"`{PREFIX}optin <ICAO> <position1> [position2] ...`"
quickstart_optional = True
prerequisite = f"{PREFIX}optout"


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
