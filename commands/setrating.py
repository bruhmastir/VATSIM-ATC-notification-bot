import config
import discord  # type: ignore
import sqlite3

# Command metadata
description = "Set or update your ATC rating. Part of getting started"
usage = f"{config.PREFIX}setrating <S1/S2/S3/C1> (or just {config.PREFIX}setrating to choose interactively)"
long_description = f"Set or update your ATC rating. If rating (i.e. S1/S2/S3/C1) is provided with the command, as in {config.PREFIX}setrating <rating>, then the first step is skipped and it moves on to ask tier of rating(i.e. Tiear 1 or Unrestricted) and if it is Unrestricted, it asks which airports are you approved on."
quickstart_optional = False

VALID_RATINGS = {"S1", "S2", "S3", "C1"}

async def handle(message, client):
    user_id = message.author.id
    conn = sqlite3.connect("vatsim_bot.db")
    cursor = conn.cursor()

    # Extract rating from command if provided (e.g., f"{config.PREFIX}setrating S3")
    parts = message.content.split()
    if len(parts) > 1:
        rating = parts[1].strip().upper()
    else:
        rating = None

    # If no rating was provided, ask the user interactively
    if rating not in VALID_RATINGS:
        await message.channel.send("Enter your ATC rating (S1, S2, S3, C1):")

        def check(m): 
            return m.author == message.author # and m.channel == message.channel
        
        rating_response = await client.wait_for("message", check=check)
        rating = rating_response.content.strip().upper()

    # Validate the rating
    if rating not in VALID_RATINGS:
        await message.channel.send("Invalid ATC rating. Please enter one of: S1, S2, S3, C1.")
        conn.close()
        return
    
    # Tiers 
    await message.channel.send("Choose your rating type: `T1` for Tier 1 (any airport) or `U` for Unrestricted (specific airports)")
    tier_response = await client.wait_for("message", check=check)
    response_tier = tier_response.content.strip().title()

    if response_tier.upper() not in ["T1", "U"]:
        await message.channel.send("Invalid choice. Please type `T1` for Tier 1 or `U` for Unrestricted.")
        return

    unrestricted_airports = None
    if response_tier == "U":
        tier = "Unrestricted"
        await message.channel.send("Enter the ICAO codes of the airports you can control, separated by commas:")
        airport_response = await client.wait_for("message", check=check)
        unrestricted_airports = airport_response.content.strip().upper()
    else:
        tier = "Tier 1"

    cursor.execute("UPDATE user_ratings SET tier = ?, unrestricted_airports = ? WHERE user_id = ?",
                   (tier, unrestricted_airports, user_id))
    conn.commit()


    # Save to database
    cursor.execute("REPLACE INTO user_ratings (user_id, atc_rating) VALUES (?, ?)", (user_id, rating))
    cursor.execute("UPDATE user_ratings SET tier = ?, unrestricted_airports = ? WHERE user_id = ?",
                   (tier, unrestricted_airports, user_id))
    conn.commit()

    conn.close()

    await message.channel.send(f"Your ATC rating has been set to {rating}, {tier}{f', {unrestricted_airports}' if tier == 'Unrestricted' else ''}.")
