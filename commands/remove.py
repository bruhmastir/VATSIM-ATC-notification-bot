import discord
import sqlite3

# Command metadata
description = "Remove a registered airport from monitoring."
usage = "!remove"

async def handle(message, client):
    user_id = message.author.id
    conn = sqlite3.connect("vatsim_bot.db")
    cursor = conn.cursor()

    await message.channel.send("Enter the ICAO code of the airport you want to remove:")
    def check(m): return m.author == message.author and m.channel == message.channel
    icao_response = await client.wait_for("message", check=check)
    icao = icao_response.content.strip().upper()

    cursor.execute("DELETE FROM user_preferences WHERE user_id = ? AND icao = ?", (user_id, icao))
    conn.commit()
    conn.close()

    await message.channel.send(f"Successfully removed {icao} from your registered airports.")
