import config
import discord # type: ignore
import sqlite3

# Command metadata
description = "Remove a registered airport from monitoring."
usage = f"{config.PREFIX}remove [ICAO 1] [ICAO 2] [ICAO 3]..."
long_description = f"Remove a registered airport from monitoring. You can use {config.PREFIX}remove to remove one by one interactively, or you can use {usage} to remove as many airports as you want immediately."
quickstart_optional = True

async def handle(message, client):
    user_id = message.author.id
    args = message.content.split()[1:]

    conn = sqlite3.connect("vatsim_bot.db")
    cursor = conn.cursor()
    airports = ""

    if not args:
        await message.channel.send("Enter the ICAO code of the airport you want to remove:")
        def check(m): return m.author == message.author and m.channel == message.channel
        icao_response = await client.wait_for("message", check=check)
        icao = icao_response.content.strip().upper()
        cursor.execute("DELETE FROM user_preferences WHERE user_id = ? AND icao = ?", (user_id, icao))
        airports = icao
    else:
        icao_response = args
        icao = icao_response

        for airport in icao:
            cursor.execute("DELETE FROM user_preferences WHERE user_id = ? AND icao = ?", (user_id, airport.upper()))
            airports += f" {airport}"
    conn.commit()
    conn.close()

    await message.channel.send(f"Successfully removed{airports} from your registered airports.")
