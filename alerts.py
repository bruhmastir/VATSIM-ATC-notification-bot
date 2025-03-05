from datetime import datetime
import logging
import os
import sqlite3
import config
import discord # type: ignore
import monitor  # type: ignore

alert_cooldowns = {}

# ✅ Fetch users who should be alerted
def get_users_to_alert(icao, num_aircraft, missing_atc, is_any_atc_active, is_some_atc_missing):
    conn = sqlite3.connect("vatsim_bot.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT user_id, primary_threshold, staff_up_threshold, cooldown, alert_preference, atc_rating, tier, unrestricted_airports
        FROM user_preferences JOIN user_ratings USING (user_id)
        WHERE icao = ? AND primary_threshold <= ?
    """, (icao, num_aircraft))
    users = cursor.fetchall()

    users_to_alert_channel = []
    users_to_alert_dm = []
    message = ""

    for user_id, primary_threshold, staff_up_threshold, cooldown, alert_preference, atc_rating, tier, unrestricted_airports in users:
        # ✅ Fetch opted-out positions for this user & airport
        cursor.execute("SELECT position FROM user_opt_outs WHERE user_id = ? AND icao = ?", (user_id, icao))
        opted_out_positions = {row[0] for row in cursor.fetchall()}  # Convert to set for fast lookup

        # Check for Tiers
        if tier == "Unrestricted":
            allowed_airports = unrestricted_airports.split(",") if unrestricted_airports else []
            if icao not in allowed_airports:
                continue  # Skip alert if the user can't control this airport
        
        should_alert = any(
            atc_rating == config.ATC_RATING_CONVERSIONS[missing_facility] and missing_facility not in opted_out_positions
            for missing_facility in missing_atc
        ) and ((is_some_atc_missing and num_aircraft >= staff_up_threshold) or (num_aircraft >= primary_threshold and not is_any_atc_active))

        if should_alert:

            # Construct alert message
            if num_aircraft >= primary_threshold and not is_any_atc_active:
                message = f"🚨 ATC NEEDED: {icao} has {num_aircraft} aircraft with no ATC online! 🚨"
            elif is_some_atc_missing and num_aircraft >= staff_up_threshold:
                message = f"🚨 ATC NEEDED: {icao} has {num_aircraft} aircraft with only partial ATC online. {', '.join(missing_atc)} is needed! 🚨"

            if alert_preference == "dm":
                users_to_alert_dm.append(user_id)
            else:
                users_to_alert_channel.append(user_id)

    conn.close()
    return users_to_alert_channel, users_to_alert_dm, message

async def check_cooldown(user_id, icao, time):
    conn = sqlite3.connect("vatsim_bot.db")
    cursor = conn.cursor()
    key = (user_id, icao)
    cooldown_active = False
    if key in alert_cooldowns:
        cursor.execute("SELECT cooldown FROM user_preferences WHERE icao = ? AND user_id = ?", (icao, user_id))
        response = cursor.fetchone()
        cooldown = response[0]
        last_alert_time = alert_cooldowns[key]
        cooldown_active = (time - last_alert_time).total_seconds() < cooldown * 60
    conn.close()
    return cooldown_active

async def check_quiet_hours(user_id, time):
    conn = sqlite3.connect("vatsim_bot.db")
    cursor = conn.cursor()

    def in_between(now, start, end):
    # Convert HH:MM strings to datetime.time objects
        start_time = datetime.strptime(start, "%H:%M").time()
        end_time = datetime.strptime(end, "%H:%M").time()
        now_time = now.time()  # Convert discord timestamp to time
    
        # Check if 'now' is between 'start' and 'end'
        if start_time <= end_time:
            return start_time <= now_time < end_time
        else:
            return start_time <= now_time or now_time < end_time
        
    cursor.execute("SELECT user_id, start_time, end_time FROM user_quiet_hours WHERE user_id = ?", (user_id,))
    response = cursor.fetchone()
    # Check if we are during quiet hours
    if response:
        conn.close()
        return in_between(time, response[1], response[2])

# ✅ Send alerts to users
async def send_alerts(icao, users_to_alert_channel, users_to_alert_dm, client, message, is_cooldown=False):
    logging.debug("send_alerts fired")
    users_to_alert = users_to_alert_dm + users_to_alert_channel
    time = discord.utils.utcnow()

    # Check for cooldown if necessary and for quiet hours
    for user_id in users_to_alert:
        key = (user_id, icao)
        cooldown_active = is_cooldown and await check_cooldown(user_id, icao, time)
        is_in_quiet_hours = await check_quiet_hours(user_id, time)

        # Check if we are during quiet hours
        if is_in_quiet_hours or cooldown_active:
            users_to_alert.remove(user_id)
            if user_id in users_to_alert_channel:
                users_to_alert_channel.remove(user_id)
            else:
                users_to_alert_dm.remove(user_id)


        alert_cooldowns[key] = time


    if users_to_alert_channel or users_to_alert_dm:
        logging.debug("send_alerts fired after cooldown and quiet hours checking")

    if users_to_alert_channel:
        channel = await client.fetch_channel(int(os.getenv("DISCORD_CHANNEL_ID")))
        if channel:
            mentions = " ".join([f"<@{user_id}>" for user_id in users_to_alert_channel])
            logging.info(f"Sent alert about {icao} to {mentions} via channel")
            logging.debug(f"{await monitor.get_atc_units(icao)}")
            await channel.send(f"{message} {mentions}")

    for user_id in users_to_alert_dm:
        user = await client.fetch_user(user_id)
        try:
            await user.send(message)
            logging.info(f"Sent alert about {icao} to {user_id} via DMs")
        except discord.Forbidden:
            logging.error(f"Could not DM {user_id}.")
