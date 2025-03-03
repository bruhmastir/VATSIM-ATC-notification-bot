import discord
import sqlite3

# Command metadata
description = "Set or update your quiet hours."
usage = "!setquiet"

async def handle(message, client):
    user_id = message.author.id
    conn = sqlite3.connect("vatsim_bot.db")
    cursor = conn.cursor()

    await message.channel.send("Enter quiet hours (UTC) in the format HH:MM-HH:MM:")
    def check(m): return m.author == message.author and m.channel == message.channel
    quiet_response = await client.wait_for("message", check=check)
    
    try:
        start, end = quiet_response.content.split("-")
        cursor.execute("REPLACE INTO user_quiet_hours (user_id, start_time, end_time) VALUES (?, ?, ?)",
                       (user_id, start.strip(), end.strip()))
        conn.commit()
        await message.channel.send("Quiet hours updated.")
    except ValueError:
        await message.channel.send("Invalid time format. Use HH:MM-HH:MM (UTC)")
    
    conn.close()
