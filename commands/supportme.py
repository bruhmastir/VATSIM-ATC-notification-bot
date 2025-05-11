import logging
import discord  # type: ignore
import sqlite3
from monitor_atc import get_aircraft_counts
from vatsim import get_vatsim_data
import config
from alerts import check_quiet_hours, send_alerts
import finder

bot_name = finder.bot_name
PREFIX = finder.find_prefix(bot_name)

# Command metadata
description = "Request support from other controllers"
usage = f"`{PREFIX}supportme [ICAO] [Facility]`"
# long_description = f"{description}. If you do not provide arguments, you will interactively request support and you can NOT choose a facility. Provide [ICAO] and [Facility] arguments for better results. If you do not select a facility, the second highest position that you can control is what will be the basis for the alerts sent to evryone. For example, if an S3 requests support without facility specification, S2 and above will be alerted. All alerts require that minimum traffic of the amount of the alerted user's support threshold that was set during registration(and could have been edited through {PREFIX}edit)"
long_description = (  
    f"{description}. If no arguments are provided, support is requested interactively, and a facility cannot be specified. "
    f"To specify a facility, use `[ICAO] [Facility]` as arguments. If no facility is given, the **second-highest** position "
    f"you can control is used (e.g., an S3 will alert S2 and below).\n\n"
    f"Alerts require the **minimum traffic meet the support threshold** set by the alerted user. "
    f"This threshold is configured during registration and can be modified using `{PREFIX}edit`."
)

quickstart_optional = True
prerequisite = f"setrating"


# ATC Facility Hierarchy
FACILITY_HIERARCHY = {
    "CTR": ["C1"],
    "APP": ["C1", "S3"],
    "DEP": ["C1", "S3"],
    "TWR": ["C1", "S3", "S2"],
    "GND": ["C1", "S3", "S2", "S1"],
    "DEL": ["C1", "S3", "S2", "S1"]
}

# Define the second-highest facility for each ATC rating
SECOND_HIGHEST_CONTROL = {
    "C1": "APP",  # C1 defaults to APP instead of CTR
    "S3": "TWR",  # S3 defaults to TWR instead of APP
    "S2": "GND",  # S2 defaults to GND instead of TWR
    "S1": "DEL"   # S1 defaults to DEL instead of GND
}

# async def handle(message, client):
#     user_id = message.author.id
#     time = discord.utils.utcnow()
#     args = message.content.split()[1:]  # Extract arguments after f"{PREFIX}supportme"

#     # ✅ Ensure user has an ATC rating set
#     conn = sqlite3.connect("vatsim_bot.db")
#     cursor = conn.cursor()
#     cursor.execute("SELECT atc_rating FROM user_ratings WHERE user_id = ?", (user_id,))
#     user_rating = cursor.fetchone()
#     if not user_rating:
#         await message.channel.send(f"You have not set your ATC rating. Use {PREFIX}setrating first.")
#         conn.close()
#         return
#     user_rating = user_rating[0]

#     # ✅ Validate ICAO argument
#     if len(args) < 1:
#         await message.channel.send(f"Usage: `{PREFIX}supportme <ICAO> [Facility] [-b]` where entries in [] are optional")
#         conn.close()
#         return
#     icao = args[0].strip().upper()
#     if icao not in config.SUPPORTED_AIRPORTS:
#         await message.channel.send(f"Invalid ICAO code. `{icao}` is not in the supported airports list.")
#         conn.close()
#         return

#     # ✅ Extract facility & check if -b flag is included
#     requested_facility = args[1].strip().upper() if len(args) > 1 and args[1].upper() in FACILITY_HIERARCHY else SECOND_HIGHEST_CONTROL.get(user_rating, "DEL")
#     broad_alert = False #"-b" in args  # Check if -b flag exists

#     # ✅ Fetch VATSIM data
#     vatsim_data = get_vatsim_data()
#     atc_units = [c['callsign'] for c in vatsim_data['controllers'] if icao in c['callsign']]
#     # atc_active = {facility: any(fac in callsign for callsign in atc_units) for facility in FACILITY_HIERARCHY.keys()}

#     # ✅ Count aircraft still on the ground
#     num_aircraft = get_aircraft_counts(vatsim_data).get(icao, 0)

#     # ✅ Fetch opted-out positions for this user & airport
#     cursor.execute("SELECT position FROM user_opt_outs WHERE user_id = ? AND icao = ?", (user_id, icao))
#     opted_out_positions = {row[0] for row in cursor.fetchall()}  # Convert to set for fast lookup


#     # ✅ Get users who meet the `support_threshold`
#     cursor.execute("""
#         SELECT user_id, atc_rating, alert_preference, support_threshold 
#         FROM user_preferences 
#         JOIN user_ratings USING (user_id)
#         WHERE icao = ?
#     """, (icao,))
#     users = cursor.fetchall()

#     if not users:
#         await message.channel.send(f"No controllers are registered for {icao}.")
#         conn.close()
#         return


#     # Check what are the requested facilities
#     requested_facilities = [requested_facility]
#     requested_ratings = FACILITY_HIERARCHY[requested_facility]
#     # requested_ratings = config.ATC_RATING_CONVERSIONS[requested_facility]
#     if broad_alert:
#         requested_facilities.append(FACILITY_HIERARCHY[f] for f in FACILITY_HIERARCHY.keys() if f < requested_facility)
#     logging.debug(f"{requested_facilities}")

#     # ✅ Find controllers to alert (only if their support_threshold is met)
#     to_alert = []
#     for user_id, atc_rating, alert_preference, support_threshold in users:
#         eligible_facilities = requested_facilities
#         logging.debug("atc rating %s", atc_rating)
#         logging.debug("eligible1 %s", eligible_facilities)
#         if num_aircraft >= support_threshold:  # Ensure traffic meets their threshold
#             logging.debug("Passed threshold")
#             # ✅ Fetch opted-out positions for this user & airport
#             cursor.execute("SELECT position FROM user_opt_outs WHERE user_id = ? AND icao = ?", (user_id, icao))
#             opted_out_positions = {row[0] for row in cursor.fetchall()}  # Convert to set for fast lookup
#             if atc_rating in requested_ratings:
#                 logging.debug("passed rating in requested facilities")
#             # if atc_rating in FACILITY_HIERARCHY[requested_facility] or (broad_alert and any(atc_rating in FACILITY_HIERARCHY[f] for f in FACILITY_HIERARCHY.keys() if f <= requested_facility)):
#                 # ✅ Fetch opted-out positions for this user & airport
#                 cursor.execute("SELECT position FROM user_opt_outs WHERE user_id = ? AND icao = ?", (user_id, icao))
#                 opted_out_positions = {row[0] for row in cursor.fetchall()}  # Convert to set for fast lookup
#                 for facility in opted_out_positions:
#                     if facility in eligible_facilities:
#                         eligible_facilities.remove(facility)
#                 logging.debug("eligible %s", eligible_facilities)
#                 in_quiet_hours = await check_quiet_hours(user_id, time)
#                 if eligible_facilities and not in_quiet_hours:
#                     to_alert.append((user_id, alert_preference))

#     logging.debug("to alert %s", to_alert if to_alert else "")
#     if not to_alert:
#         await message.channel.send(f"No available controllers meet the support threshold for {requested_facility} at {icao}.")
#         conn.close()
#         return

#     # ✅ Send alerts
#     message_text = f"🚨 {message.author.display_name} is requesting **{requested_facility}** at **{icao}**!"
#     if broad_alert: # TODO: Change below text location
#         message_text += " (Also notifying controllers for lower positions)"

#     users_to_alert_channel = []
#     users_to_alert_dm = []
#     for user_id, alert_preference in to_alert:
#         user = await client.fetch_user(user_id)
#         try:
#             if alert_preference == "dm":
#                 users_to_alert_dm.append(user_id)
#                 # await user.send(message_text)
#             else:
#                 # await message.channel.send(f"<@{user_id}> {message_text}")
#                 users_to_alert_channel.append(user_id)
#         except discord.Forbidden:
#             logging.error(f"Could not send DM to {user_id}, falling back to channel message.")
#             users_to_alert_channel.append(user_id)
#             # await message.channel.send(f"<@{user_id}> {message_text}")
    
#     await send_alerts(icao, users_to_alert_channel, users_to_alert_dm, client, message_text)

#     await message.channel.send(f"Support request for {requested_facility} at {icao} has been sent.")
#     conn.close()

async def handle(message, client):
    user_id = message.author.id
    time = discord.utils.utcnow()
    args = message.content.split()[1:]

    if len(args) != 2:
        await message.channel.send(f"Usage: `{PREFIX}supportme <ICAO> <FACILITY>`")
        return

    icao, requested_facility = args[0].strip().upper(), args[1].strip().upper()

    if icao not in config.SUPPORTED_AIRPORTS or requested_facility not in FACILITY_HIERARCHY:
        await message.channel.send("❌ Invalid ICAO or facility.")
        return

    conn = sqlite3.connect("vatsim_bot.db")
    cursor = conn.cursor()

    cursor.execute("SELECT atc_rating FROM user_ratings WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        await message.channel.send(f"You have not set your ATC rating. Use `{PREFIX}setrating` first.")
        conn.close()
        return
    user_rating = row[0]

    vatsim_data = get_vatsim_data()
    num_aircraft = get_aircraft_counts(vatsim_data).get(icao, 0)

    requested_ratings = FACILITY_HIERARCHY[requested_facility]

    cursor.execute("""
        SELECT user_id, atc_rating, alert_preference, support_threshold
        FROM user_preferences
        JOIN user_ratings USING (user_id)
        WHERE icao = ?
    """, (icao,))
    users = cursor.fetchall()

    to_alert = []
    for target_id, target_rating, alert_pref, threshold in users:
        if num_aircraft < threshold or target_rating not in requested_ratings:
            continue

        cursor.execute("SELECT position FROM user_opt_outs WHERE user_id = ? AND icao = ?", (target_id, icao))
        opted_out = {row[0] for row in cursor.fetchall()}

        if requested_facility in opted_out:
            continue

        if await check_quiet_hours(target_id, time):
            continue

        to_alert.append((target_id, alert_pref))

    if not to_alert:
        await message.channel.send(f"No available controllers meet the support threshold for **{requested_facility}** at **{icao}**.")
        conn.close()
        return

    message_text = f"🚨 {message.author.display_name} is requesting **{requested_facility}** at **{icao}**!"
    users_dm, users_mention = [], []

    for target_id, alert_pref in to_alert:
        user = await client.fetch_user(target_id)
        try:
            if alert_pref == "dm":
                users_dm.append(target_id)
            else:
                users_mention.append(target_id)
        except discord.Forbidden:
            users_mention.append(target_id)

    await send_alerts(icao, users_mention, users_dm, client, message_text)
    await message.channel.send(f"Support request for **{requested_facility}** at **{icao}** has been sent.")
    conn.close()
