from datetime import datetime, timedelta
import logging
import os
import sqlite3
import config
import discord # type: ignore
import dotenv # type: ignore
import finder
from monitor_atc import get_atc_units

# Facility mapping based on training level
TRAINING_FACILITIES = {
    "S1": "GND",
    "S2": "TWR",
    "S3": "APP",
    "C1": "CTR"
}


bot_name = finder.bot_name

dotenv.load_dotenv(".env")

DEVELOPER_ROLE_ID = int(os.getenv("DEVELOPER_ROLE_ID"))  # Bot owner ID

# async def get_developer_role(client):
#     global developer
#     developer = await client.guilds.fetch_role(DEVELOPER_ROLE_ID) #TODO: Change this to fetch the role
#     # client.gui

async def get_tag_by_name(channel: discord.ForumChannel, tag_name: str):
    """Finds a tag in a forum channel by its name."""
    for tag in channel.available_tags:  # Loop through all available tags
        if tag.name.lower() == tag_name.lower():
            return tag
    return None  # Return None if the tag is not found


async def send_errors(message, client, error):
    bot_name = finder.bot_name
    FORUM_CHANNEL_ID = int(os.getenv("FORUM_CHANNEL_ID" if not bot_name.lower().startswith("dev") else "DEV_FORUM_CHANNEL_ID"))  # Forum channel ID

    """Send an error message to the user."""
    forum = await client.fetch_channel(FORUM_CHANNEL_ID)
    bot_report_tag = await get_tag_by_name(forum, "Error raised by bot")# if not str(client.user).lower().startswith("dev") else "Dev bot error")
    mention = f"<@&{DEVELOPER_ROLE_ID}>"
    embed = discord.Embed(title=f"Error report: {message}", description=f"Description: {error}", color=discord.Color.red())
    await forum.create_thread(name=f"{message[:-1] if len(message)<=100 else message[:99]}", content=f"{mention}, {datetime.now()}",embed=embed, reason="New error report", applied_tags=[bot_report_tag])


# ✅ Fetch users who should be alerted
def get_users_to_alert(icao, num_aircraft, missing_atc, is_any_atc_active, is_some_atc_missing):
    conn = sqlite3.connect("vatsim_bot.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT user_id, primary_threshold, staff_up_threshold, cooldown, alert_preference, atc_rating, tier
        FROM user_preferences JOIN user_ratings USING (user_id)
        WHERE icao = ? AND primary_threshold <= ?
    """, (icao, num_aircraft))
    users = cursor.fetchall()

    users_to_alert_channel = []
    users_to_alert_dm = []
    message = ""

    for user_id, primary_threshold, staff_up_threshold, cooldown, alert_preference, atc_rating, tier in users:
        # ✅ Fetch opted-out positions for this user & airport
        cursor.execute("SELECT position FROM user_opt_outs WHERE user_id = ? AND icao = ?", (user_id, icao))
        opted_out_positions = {row[0] for row in cursor.fetchall()}  # Convert to set for fast lookup

        # Check for Tiers
        if tier == "Unrestricted":
            # allowed_airports = unrestricted_airports.split(",") if unrestricted_airports else []
            if icao in config.TIER_1_AIRPORTS:
                continue  # Skip alert if the user can't control OMDB
    
    
        time = discord.utils.utcnow()

        is_in_quiet_hours = check_quiet_hours(user_id, time)
        
        should_alert = any(
            atc_rating == config.ATC_RATING_CONVERSIONS[missing_facility] and missing_facility not in opted_out_positions
            for missing_facility in missing_atc
        ) and ((is_some_atc_missing and num_aircraft >= staff_up_threshold) or (num_aircraft >= primary_threshold and not is_any_atc_active)) and not is_in_quiet_hours

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

async def check_cooldown(user_id, icao):
    """Check if a cooldown is active for a user at an airport."""
    conn = sqlite3.connect("vatsim_bot.db")
    cursor = conn.cursor()

    cursor.execute("SELECT last_alert FROM user_cooldowns WHERE user_id = ? AND icao = ?", (user_id, icao))
    result = cursor.fetchone()

    if result:
        last_alert_time = datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S")
        cursor.execute("SELECT cooldown FROM user_preferences WHERE user_id = ? AND icao = ?", (user_id, icao))
        cooldown = cursor.fetchone()[0]

        if (datetime.now(datetime.UTC) - last_alert_time).total_seconds() < cooldown * 60:
            conn.close()
            return True  # Cooldown is still active

    conn.close()
    return False  # No active cooldown

async def set_cooldown(user_id, icao):
    """Update the cooldown timestamp in the database."""
    conn = sqlite3.connect("vatsim_bot.db")
    cursor = conn.cursor()

    now = datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("REPLACE INTO user_cooldowns (user_id, icao, last_alert) VALUES (?, ?, ?)", (user_id, icao, now))

    conn.commit()
    conn.close()


def check_quiet_hours(user_id, time):
    logging.debug("check_quiet_hours fired")
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
    conn.close()

# ✅ Send alerts to users
async def send_alerts(icao, users_to_alert_channel, users_to_alert_dm, client, message, is_cooldown=False):
    logging.debug("send_alerts fired")
    users_to_alert = users_to_alert_dm + users_to_alert_channel
    time = discord.utils.utcnow()

    # Check for cooldown if necessary and for quiet hours
    for user_id in users_to_alert:
        key = (user_id, icao)
        cooldown_active = is_cooldown and await check_cooldown(user_id, icao)
        is_in_quiet_hours = check_quiet_hours(user_id, time)

        # Check if we are during quiet hours
        if is_in_quiet_hours or cooldown_active:
            users_to_alert.remove(user_id)
            if user_id in users_to_alert_channel:
                users_to_alert_channel.remove(user_id)
            elif user_id in users_to_alert_dm:
                users_to_alert_dm.remove(user_id)


        if users_to_alert_channel or users_to_alert_dm:
            logging.debug("send_alerts fired after cooldown and quiet hours checking")

        for user_id in users_to_alert_dm:
            user = await client.fetch_user(user_id)
            try:
                await user.send(message)
                logging.info(f"Sent alert about {icao} to {user_id} via DMs")
                await set_cooldown(user_id, icao)
            except discord.Forbidden:
                logging.error(f"Could not DM {user_id}. Defaulting back to alerting on channel")
                users_to_alert_channel.append(user_id)

        if users_to_alert_channel:
            try:
                channel = await client.fetch_channel(int(os.getenv("DISCORD_CHANNEL_ID")))
                if channel:
                    from monitor_atc import get_atc_units
                    mentions = " ".join([f"<@{user_id}>" for user_id in users_to_alert_channel])
                    logging.info(f"Sent alert about {icao} to {mentions} via channel")
                    logging.debug(f"{await get_atc_units(icao)}")
                    await channel.send(f"{message} {mentions}")
                    await set_cooldown(user_id, icao)

            except Exception as e:
                logging.error(f"Could not send alert about {icao} to channel. Error: {e}")


async def send_observe_alerts(user_id, client, message):
    logging.info("send_observe_alerts fired")
    time = discord.utils.utcnow()
    is_in_quiet_hours = check_quiet_hours(user_id, time)
    if not is_in_quiet_hours:
        user = await client.fetch_user(user_id)
        try:
            await user.send(message)
            logging.info(f"Sent observe alert to {user_id} via DMs")
        except discord.Forbidden:
            logging.error(f"Could not DM {user_id}.")  # No need to remove from list since we are not sending to a channel


async def get_observers():
    current_time = datetime.now(datetime.UTC) #.time()
    current_time_str = current_time.strftime('%H:%M')
    current_datetime_str = current_time.strftime('%Y-%m-%d %H:%M:%S')
    conn = sqlite3.connect("vatsim_bot.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT user_id
        FROM user_observe_hours
        WHERE start_time <= ? AND end_time >= ?
    """,(current_time_str, current_time_str))
    observers = cursor.fetchall()

    cursor.execute("""
        SELECT user_id, start_date_time, end_date_time
        FROM temp_observe
        WHERE start_date_time <= ? AND end_date_time >= ?
    """,(current_datetime_str, current_datetime_str))
    temp_observers = cursor.fetchall()

    for obs in temp_observers:
        user_id, start_time, end_time = obs
        observers.append(obs)
        if current_time > end_time:
            cursor.execute("DELETE FROM temp_observe WHERE user_id = ?", (user_id))
    
    obs_by_airport = {}

    for observer in observers:
        user_id = observer[0]
        training_info = finder.get_training_info(user_id)
        training_rating, training_airport = training_info
        training_facility = TRAINING_FACILITIES.get(training_rating)
        if not training_facility:
            continue
        if training_airport not in obs_by_airport:
            obs_by_airport[training_airport] = [[user_id, training_facility]]
        else:
            obs_by_airport[training_airport].append([user_id, training_facility])


    conn.close()

    return obs_by_airport
