import discord
import sqlite3

# Command metadata
description = "View your registered airports, thresholds, cooldowns, quiet hours, support threshold, and tertiary threshold."
usage = "!view"

async def handle(message, client):
    user_id = message.author.id
    conn = sqlite3.connect("vatsim_bot.db")
    cursor = conn.cursor()

    cursor.execute("SELECT icao, primary_threshold, secondary_threshold, tertiary_threshold, cooldown, alert_preference, support_threshold FROM user_preferences WHERE user_id = ?", (user_id,))
    registrations = cursor.fetchall()

    cursor.execute("SELECT start_time, end_time FROM user_quiet_hours WHERE user_id = ?", (user_id,))
    quiet_hours = cursor.fetchone()
    
    cursor.execute("SELECT atc_rating FROM user_ratings WHERE user_id = ?", (user_id,))
    atc_rating = cursor.fetchone()

    if registrations:
        response = "**Your Registered Airports:**\n"
        for icao, primary, secondary, tertiary, cooldown, alert_preference, support_threshold in registrations:
            response += f"- **{icao}**: Primary {primary}, Secondary {secondary}, Tertiary {tertiary}, Cooldown {cooldown} min, Alerts: {alert_preference}, Support Threshold: {support_threshold}\n"
    else:
        response = "You have no registered airports.\n"
    
    if quiet_hours:
        response += f"\n**Your Quiet Hours (UTC):** {quiet_hours[0]} - {quiet_hours[1]}"
    else:
        response += "\n**You have not set quiet hours.**"
    
    if atc_rating:
        response += f"\n**Your ATC Rating:** {atc_rating[0]}"
    else:
        response += "\n**You have not set an ATC rating.**"
    
    await message.channel.send(response)
    conn.close()
