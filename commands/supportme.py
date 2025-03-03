import discord
import sqlite3
from vatsim import get_vatsim_data

# Command metadata
description = "Request support from controllers below your ATC rating when workload is high."
usage = "!supportme <ICAO>"

# ATC rating hierarchy
RATING_HIERARCHY = {
    "C1": ["S3", "S2", "S1"],  # Center can request APP/DEP, TWR, GND/DEL
    "S3": ["S2", "S1"],        # APP/DEP can request TWR, GND/DEL
    "S2": ["S1"],               # TWR can request GND/DEL
    "S1": ["S1"]                     # GND can request DEL
}

async def handle(message, client):
    user_id = message.author.id
    conn = sqlite3.connect("vatsim_bot.db")
    cursor = conn.cursor()
    
    # Check if ICAO code is provided in command
    command_parts = message.content.split()
    if len(command_parts) > 1:
        icao = command_parts[1].strip().upper()
    else:
        await message.channel.send("Enter the ICAO code where you need support:")
        def check(m): return m.author == message.author and m.channel == message.channel
        icao_response = await client.wait_for("message", check=check)
        icao = icao_response.content.strip().upper()
    
    # Get the user's ATC rating and username
    cursor.execute("SELECT atc_rating FROM user_ratings WHERE user_id = ?", (user_id,))
    user_rating = cursor.fetchone()
    if not user_rating:
        await message.channel.send("You have not set your ATC rating. Use !setrating first.")
        conn.close()
        return
    user_rating = user_rating[0]
    username = message.author.display_name  # Get the requester's Discord username
    
    # Fetch VATSIM data to check existing ATC coverage
    vatsim_data = get_vatsim_data()
    atc_units = [c['callsign'] for c in vatsim_data['controllers'] if icao in c['callsign']]
    
    # Determine the highest active ATC position
    atc_active = {
        "CTR": any("CTR" in callsign for callsign in atc_units),
        "APP": any("APP" in callsign or "DEP" in callsign for callsign in atc_units),
        "TWR": any("TWR" in callsign for callsign in atc_units),
        "GND": any("GND" in callsign for callsign in atc_units),
        "DEL": any("DEL" in callsign for callsign in atc_units)
    }
    
    # Determine needed position based on user rating and existing ATC
    needed_position = None
    if user_rating == "C1" and not atc_active["APP"]:
        needed_position = "APP/DEP or below"
    elif user_rating == "S3" and not atc_active["TWR"]:
        needed_position = "TWR or below"
    elif user_rating == "S2" and not atc_active["GND"]:
        needed_position = "GND/DEL"
    elif user_rating == "S1" and not atc_active["DEL"]:
        needed_position = "DEL"
    
    if needed_position is None:
        await message.channel.send(f"Support request not needed at {icao}, as the required ATC position is already online.")
        conn.close()
        return
    
    # Get eligible support ratings while considering the highest active ATC position
    eligible_ratings = []
    missing_rating = None
    if needed_position == "APP/DEP or below":
        if not atc_active["TWR"]:
            eligible_ratings.extend(["S3", "S2", "S1"])
        elif not atc_active["GND"]:
            eligible_ratings.extend(["S2", "S1"])
        missing_rating = "S3" if "S3" not in eligible_ratings else None
    elif needed_position == "TWR or below":
        if not atc_active["GND"]:
            eligible_ratings.extend(["S2", "S1"])
        missing_rating = "S2" if "S2" not in eligible_ratings else None
    elif needed_position == "GND/DEL":
        eligible_ratings.extend(["S1"])
        missing_rating = "S1" if "S1" not in eligible_ratings else None
    elif needed_position == "DEL":
        eligible_ratings.extend(["S1"])
        missing_rating = "S1" if "S1" not in eligible_ratings else None
    
    if not eligible_ratings:
        await message.channel.send(f"No {missing_rating} controllers are available to support at {icao}.")
        conn.close()
        return
    
    # Find users who meet the support threshold and their alert preferences
    cursor.execute("""
        SELECT user_id, alert_preference FROM user_preferences
        WHERE icao = ? AND support_threshold <= ? AND user_id IN (
            SELECT user_id FROM user_ratings WHERE atc_rating IN ({})
        )
    """.format(",".join(["?" for _ in eligible_ratings])), (icao, len(eligible_ratings), *eligible_ratings))
    support_users = cursor.fetchall()
    conn.close()
    
    if not support_users:
        await message.channel.send(f"No available {missing_rating} controllers meet the support threshold at this time.")
        return
    
    # Notify eligible controllers based on their alert preference
    for user_id, alert_preference in support_users:
        user = await client.fetch_user(user_id)
        message_text = f"{username} ({user_rating}) is requesting {needed_position} at {icao}!"
        
        if alert_preference == "dm":
            try:
                await user.send(message_text)
            except discord.Forbidden:
                print(f"Could not DM {user.display_name}. Falling back to channel alert.")
                await message.channel.send(f"<@{user_id}> {message_text}")
        else:
            await message.channel.send(f"<@{user_id}> {message_text}")
