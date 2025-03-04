# import discord
# import sqlite3

# # Command metadata
# description = "Register an airport for monitoring and set thresholds. Requires ATC rating to be set first."
# usage = "!register"

# async def handle(message, client):
#     user_id = message.author.id
#     conn = sqlite3.connect("vatsim_bot.db")
#     cursor = conn.cursor()
    
#     # Check if user has set ATC rating
#     cursor.execute("SELECT atc_rating FROM user_ratings WHERE user_id = ?", (user_id,))
#     user_rating = cursor.fetchone()
#     if not user_rating:
#         await message.channel.send("You must set your ATC rating first using !setrating before registering an airport.")
#         conn.close()
#         return
    
#     while True:
#         await message.channel.send("Enter the ICAO code of the airport you want to monitor:")
#         def check(m): return m.author == message.author and m.channel == message.channel
#         icao_response = await client.wait_for("message", check=check)
#         icao = icao_response.content.strip().upper()

#         await message.channel.send(f"Set primary threshold for {icao}:")
#         primary_response = await client.wait_for("message", check=check)
#         await message.channel.send(f"Set  threshold for {icao}:")
#         response = await client.wait_for("message", check=check)
#         await message.channel.send(f"Set tertiary threshold for {icao} (minimum departures needed before you are alerted when lower ATC is online):")
#         tertiary_response = await client.wait_for("message", check=check)
#         await message.channel.send(f"Set cooldown time in minutes for {icao}:")
#         cooldown_response = await client.wait_for("message", check=check)
        
#         await message.channel.send("Do you want to receive alerts in the channel or in your DMs? (Type `channel` or `dm`)")
#         alert_preference_response = await client.wait_for("message", check=check)
#         alert_preference = alert_preference_response.content.strip().lower()
#         if alert_preference not in ["channel", "dm"]:
#             await message.channel.send("Invalid choice. Defaulting to channel alerts.")
#             alert_preference = "channel"
        
#         await message.channel.send(f"Set support threshold for {icao} (minimum departures needed before you will be called for help at {icao}):")
#         support_threshold_response = await client.wait_for("message", check=check)
        
#         try:
#             cursor.execute("REPLACE INTO user_preferences (user_id, icao, primary_threshold, tertiary_threshold, cooldown, alert_preference, support_threshold) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
#                            (user_id, icao, int(primary_response.content), int(response.content), int(tertiary_response.content), int(cooldown_response.content), alert_preference, int(support_threshold_response.content)))
#             conn.commit()
#         except ValueError:
#             await message.channel.send(f"Invalid values for {icao}, registration skipped.")
#             continue

#         await message.channel.send("Do you want to add another airport? (yes/no)")
#         add_more_response = await client.wait_for("message", check=check)
#         if add_more_response.content.lower() != "yes":
#             break

#     cursor.execute("SELECT * FROM user_quiet_hours WHERE user_id = ?", (user_id,))
#     if not cursor.fetchone():
#         await message.channel.send("You haven't set quiet hours yet. Enter quiet hours (UTC) in the format HH:MM-HH:MM or type `NA` to always receive alerts:")
#         quiet_response = await client.wait_for("message", check=check)
#         try:
#             if quiet_response.content.strip().upper() == "NA":
#                 cursor.execute("INSERT INTO user_quiet_hours (user_id, start_time, end_time) VALUES (?, ?, ?)",
#                                (user_id, "NA", "NA"))
#             else:
#                 start, end = quiet_response.content.split("-")
#                 cursor.execute("INSERT INTO user_quiet_hours (user_id, start_time, end_time) VALUES (?, ?, ?)",
#                                (user_id, start.strip(), end.strip()))
#             conn.commit()
#         except ValueError:
#             await message.channel.send("Invalid time format. Use HH:MM-HH:MM (UTC) or type `NA` to always receive alerts.")
    
#     await message.channel.send("Registration complete!")
#     conn.close()
























import discord
import sqlite3
from config import SUPPORTED_AIRPORTS  # Import supported airports from config.py

# Command metadata
description = "Register an airport for monitoring and set thresholds. Requires ATC rating to be set first."
usage = "!register"

def is_valid_number(value):
    try:
        return int(value) >= 0
    except ValueError:
        return False

async def handle(message, client):
    user_id = message.author.id
    conn = sqlite3.connect("vatsim_bot.db")
    cursor = conn.cursor()
    
    # Check if user has set ATC rating
    cursor.execute("SELECT atc_rating FROM user_ratings WHERE user_id = ?", (user_id,))
    user_rating = cursor.fetchone()
    if not user_rating:
        await message.channel.send("You must set your ATC rating first using !setrating before registering an airport.")
        conn.close()
        return
    
    while True:
        await message.channel.send("Enter the ICAO code of the airport you want to monitor:")
        def check(m): return m.author == message.author and m.channel == message.channel
        icao_response = await client.wait_for("message", check=check)
        icao = icao_response.content.strip().upper()
        
        if icao == "CANCEL":
            await message.channel.send("Registration process cancelled.")
            conn.close()
            return
        
        if icao not in SUPPORTED_AIRPORTS:
            await message.channel.send("Invalid ICAO code. Please enter a valid airport from the supported list.")
            continue
        
        await message.channel.send(f"Set primary threshold for {icao}:")
        primary_response = await client.wait_for("message", check=check)
        if primary_response.content.strip().upper() == "CANCEL":
            await message.channel.send("Registration process cancelled.")
            conn.close()
            return
        if not is_valid_number(primary_response.content):
            await message.channel.send("Invalid input. Please enter a valid number.")
            continue
    
        
        await message.channel.send(f"Set tertiary threshold for {icao}:")
        tertiary_response = await client.wait_for("message", check=check)
        if tertiary_response.content.strip().upper() == "CANCEL":
            await message.channel.send("Registration process cancelled.")
            conn.close()
            return
        if not is_valid_number(tertiary_response.content):
            await message.channel.send("Invalid input. Please enter a valid number.")
            continue
        
        await message.channel.send(f"Set cooldown time in minutes for {icao}:")
        cooldown_response = await client.wait_for("message", check=check)
        if cooldown_response.content.strip().upper() == "CANCEL":
            await message.channel.send("Registration process cancelled.")
            conn.close()
            return
        if not is_valid_number(cooldown_response.content):
            await message.channel.send("Invalid input. Please enter a valid number.")
            continue
        
        await message.channel.send("Do you want to receive alerts in the channel or in your DMs? (Type `channel` or `dm`)")
        alert_preference_response = await client.wait_for("message", check=check)
        alert_preference = alert_preference_response.content.strip().lower()
        if alert_preference.upper() == "CANCEL":
            await message.channel.send("Registration process cancelled.")
            conn.close()
            return
        if alert_preference not in ["channel", "dm"]:
            await message.channel.send("Invalid choice. Defaulting to channel alerts.")
            alert_preference = "channel"
        
        await message.channel.send(f"Set support threshold for {icao}:")
        support_threshold_response = await client.wait_for("message", check=check)
        if support_threshold_response.content.strip().upper() == "CANCEL":
            await message.channel.send("Registration process cancelled.")
            conn.close()
            return
        if not is_valid_number(support_threshold_response.content):
            await message.channel.send("Invalid input. Please enter a valid number.")
            continue
        
        try:
            cursor.execute("REPLACE INTO user_preferences (user_id, icao, primary_threshold, tertiary_threshold, cooldown, alert_preference, support_threshold) VALUES (?, ?, ?, ?, ?, ?, ?)",
                           (user_id, icao, int(primary_response.content), int(tertiary_response.content), int(cooldown_response.content), alert_preference, int(support_threshold_response.content)))
            conn.commit()
        except ValueError:
            await message.channel.send(f"Invalid values for {icao}, registration skipped.")
            continue
        
        await message.channel.send("Do you want to add another airport? (yes/no)")
        add_more_response = await client.wait_for("message", check=check)
        if add_more_response.content.lower() != "yes":
            break
    
    await message.channel.send("Registration complete!")
    conn.close()
