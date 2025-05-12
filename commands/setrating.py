import config
import discord  # type: ignore
import sqlite3
import finder

bot_name = finder.bot_name
PREFIX = finder.find_prefix(bot_name)

# Command metadata
description = "Set or update your ATC rating. Part of getting started"
usage = f"`{PREFIX}setrating [S1/S2/S3/C1] [T1/U]`"
long_description = f"Set or update your ATC rating. If rating (i.e. S1/S2/S3/C1) is provided with the command, as in `{PREFIX}setrating <rating>`, then the first step is skipped and it moves on to ask tier of rating(i.e. Tier 1 or Unrestricted)"
quickstart_optional = False

VALID_RATINGS = {"S1", "S2", "S3", "C1"}

async def handle(message, client):
    user_id = message.author.id
    conn = sqlite3.connect("vatsim_bot.db")
    cursor = conn.cursor()

    # Extract rating from command if provided (e.g., f"{PREFIX}setrating S3")
    parts = message.content.split()
    if len(parts) > 1:
        rating = parts[1].strip().upper()
    else:
        rating = None
    if len(parts) > 2:
        tier = parts[2].strip().upper()
    else:
        tier = None
    # if len(parts) > 3:
    #     unrestricted_airports = parts[3].strip().upper()
    # else:
    #     unrestricted_airports = None
    def check(m): 
        return m.author == message.author # and m.channel == message.channel   

    # If no rating was provided, ask the user interactively
    if not rating:
        await message.channel.send("Enter your ATC rating (S1, S2, S3, C1):")


        
        rating_response = await client.wait_for("message", check=check)
        rating = rating_response.content.strip().upper()

    # Validate the rating
    if rating not in VALID_RATINGS:
        await message.channel.send("Invalid ATC rating. Please enter one of: S1, S2, S3, C1 next time.")
        conn.close()
        return
    
    # Tiers 
    await message.channel.send("Choose your rating type: `T1` for Tier 1 (any airport) or `U` for Unrestricted")
    if not tier or tier.upper() not in ["T1", "U"]:
        tier_response = await client.wait_for("message", check=check)
        tier = tier_response.content.strip().title()

    if tier.upper() not in ["T1", "U"]:
        await message.channel.send("Invalid choice. Please type `T1` for Tier 1 or `U` for Unrestricted next time.")
        return

    if tier == "U":
        tier_full = "Unrestricted"
        # if not unrestricted_airports or unrestricted_airports not in config.SUPPORTED_AIRPORTS:
        #     await message.channel.send("Enter the ICAO codes of the airports you can control, separated by commas:")
        #     airport_response = await client.wait_for("message", check=check)
        #     unrestricted_airports = airport_response.content.strip().upper()
    else:
        tier_full = "Tier 1"

    cursor.execute("UPDATE user_ratings SET tier = ? WHERE user_id = ?",
                   (tier_full, user_id))
    conn.commit()


    # Save to database
    cursor.execute("REPLACE INTO user_ratings (user_id, atc_rating) VALUES (?, ?)", (user_id, rating))
    cursor.execute("UPDATE user_ratings SET tier = ? WHERE user_id = ?",
                   (tier_full, user_id))
    conn.commit()

    conn.close()

    await message.channel.send(f"Your ATC rating has been set to {rating}, {tier_full}.")
