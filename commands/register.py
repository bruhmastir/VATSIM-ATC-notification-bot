import discord # type: ignore
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
    
        
        await message.channel.send(f"Set staff_up threshold for {icao}:")
        staff_up_response = await client.wait_for("message", check=check)
        if staff_up_response.content.strip().upper() == "CANCEL":
            await message.channel.send("Registration process cancelled.")
            conn.close()
            return
        if not is_valid_number(staff_up_response.content):
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
            cursor.execute("REPLACE INTO user_preferences (user_id, icao, primary_threshold, staff_up_threshold, cooldown, alert_preference, support_threshold) VALUES (?, ?, ?, ?, ?, ?, ?)",
                           (user_id, icao, int(primary_response.content), int(staff_up_response.content), int(cooldown_response.content), alert_preference, int(support_threshold_response.content)))
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
