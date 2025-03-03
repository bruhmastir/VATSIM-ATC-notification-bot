import discord
import sqlite3

# Command metadata
description = "Set or update your support threshold. This defines the minimum traffic level at which you will be called to assist."
usage = "!setsupport <ICAO> <Threshold>"

async def handle(message, client):
    user_id = message.author.id
    conn = sqlite3.connect("vatsim_bot.db")
    cursor = conn.cursor()
    
    await message.channel.send("Enter the ICAO code for which you want to set a support threshold:")
    def check(m): return m.author == message.author and m.channel == message.channel
    icao_response = await client.wait_for("message", check=check)
    icao = icao_response.content.strip().upper()
    
    await message.channel.send(f"Enter the support threshold (minimum departures needed before you will be called for help at {icao}):")
    threshold_response = await client.wait_for("message", check=check)
    
    try:
        threshold = int(threshold_response.content)
        cursor.execute("UPDATE user_preferences SET support_threshold = ? WHERE user_id = ? AND icao = ?", (threshold, user_id, icao))
        conn.commit()
        await message.channel.send(f"Your support threshold for {icao} has been set to {threshold}.")
    except ValueError:
        await message.channel.send("Invalid input. Please enter a valid number for the threshold.")
    
    conn.close()