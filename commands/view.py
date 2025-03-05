import discord # type: ignore
import sqlite3

# Command metadata
description = "View your registered airports, thresholds, cooldowns, quiet hours, support threshold, and staff_up threshold."
usage = "!view"

async def handle(message, client):
    user_id = message.author.id
    conn = sqlite3.connect("vatsim_bot.db")
    cursor = conn.cursor()

    cursor.execute("SELECT icao, primary_threshold, staff_up_threshold, cooldown, alert_preference, support_threshold FROM user_preferences WHERE user_id = ?", (user_id,))
    registrations = cursor.fetchall()

    cursor.execute("SELECT start_time, end_time FROM user_quiet_hours WHERE user_id = ?", (user_id,))
    quiet_hours = cursor.fetchone()
    
    cursor.execute("SELECT atc_rating FROM user_ratings WHERE user_id = ?", (user_id,))
    atc_rating = cursor.fetchone()

    cursor.execute("SELECT icao, position FROM user_opt_outs WHERE user_id = ?", (user_id,))
    opted_out_positions = cursor.fetchall()


    if registrations:
        response = "**Your Registered Airports:**\n"
        for icao, primary, staff_up, cooldown, alert_preference, support_threshold in registrations:
            response += f"- **{icao}**: Primary {primary}, staff_up {staff_up}, Cooldown {cooldown} min, Alerts: {alert_preference}, Support Threshold: {support_threshold}\n"
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

    if opted_out_positions:
        response += f"\n\n**You have opted out of receiving alerts for the following airports:**\n"
        positions = {}
        positions_str = ""
        counter = 0
        for icao, position in opted_out_positions:
            if icao in positions:
                positions[icao].append(position)
            else:
                positions[icao] = [position]
            
        for icao_code in positions.keys():
            counter += 1
            positions_str = ""
            for position_1 in positions[icao_code]:
                positions_str += f"{position_1} "
            response += f"        **{counter}) Airport:** {icao_code}, **Positions:** {positions_str} \n"


    await message.channel.send(response)
    conn.close()
