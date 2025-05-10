import asyncio
import sqlite3

import config
import finder

bot_name = finder.bot_name
PREFIX = finder.find_prefix(bot_name)


description = "Remove opt-in again to receive alerts for specific ATC positions again."
usage = f"`{PREFIX}optin [ICAO] [position1] [position2] ...`"
quickstart_optional = True
prerequisite = f"optout"


async def handle(message, client):
    user_id = message.author.id
    command_parts = message.content.split()
    usage = f"{PREFIX}optin <ICAO> <POSITION(S)>"

    VALID_POSITIONS = {"DEL", "GND", "TWR", "APP", "DEP", "CTR"}  # adjust if needed

    def check_author(m):
        return m.author == message.author and m.channel == message.channel

    # Prompt for ICAO if missing
    if len(command_parts) >= 2:
        icao = command_parts[1].strip().upper()
    else:
        await message.channel.send("🛫 **Which airport ICAO code would you like to opt into?**")
        try:
            reply = await client.wait_for("message", timeout=60, check=check_author)
            icao = reply.content.strip().upper()
        except asyncio.TimeoutError:
            await message.channel.send("⏱️ **Command timed out. Please try again.**")
            return

    # Prompt for positions if missing
    if len(command_parts) >= 3:
        positions = {p.strip().upper() for p in command_parts[2:]}
    else:
        await message.channel.send("🎯 **Which positions would you like to opt into? (e.g. DEL GND TWR)**")
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

    # Remove opt-out entries from the database
    conn = sqlite3.connect("vatsim_bot.db")
    cursor = conn.cursor()
    for position in positions:
        cursor.execute(
            "DELETE FROM user_opt_outs WHERE user_id = ? AND icao = ? AND position = ?",
            (user_id, icao, position)
        )
    conn.commit()
    conn.close()

    await message.channel.send(f"✅ **You will now receive alerts for {', '.join(positions)} at {icao}.**")
