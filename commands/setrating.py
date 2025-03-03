import discord
import sqlite3

# Command metadata
description = "Set or update your ATC rating."
usage = "!setrating <S1/S2/S3/C1>"

VALID_RATINGS = {"S1", "S2", "S3", "C1"}

async def handle(message, client):
    user_id = message.author.id
    conn = sqlite3.connect("vatsim_bot.db")
    cursor = conn.cursor()
    
    await message.channel.send("Enter your ATC rating (S1, S2, S3, C1):")
    def check(m): return m.author == message.author and m.channel == message.channel
    rating_response = await client.wait_for("message", check=check)
    rating = rating_response.content.strip().upper()
    
    if rating not in VALID_RATINGS:
        await message.channel.send("Invalid ATC rating. Please enter one of: S1, S2, S3, C1.")
        return
    
    cursor.execute("REPLACE INTO user_ratings (user_id, atc_rating) VALUES (?, ?)", (user_id, rating))
    conn.commit()
    conn.close()
    
    await message.channel.send(f"Your ATC rating has been set to {rating}.")
