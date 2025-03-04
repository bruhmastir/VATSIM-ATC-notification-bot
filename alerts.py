import os
import sqlite3
import config
import discord  # type: ignore

alert_cooldowns = {}

# ✅ Fetch users who should be alerted
def get_users_to_alert(icao, num_aircraft, missing_atc, is_any_atc_active, is_some_atc_missing):
    conn = sqlite3.connect("vatsim_bot.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT user_id, primary_threshold, staff_up_threshold, cooldown, alert_preference, atc_rating
        FROM user_preferences JOIN user_ratings USING (user_id)
        WHERE icao = ? AND primary_threshold <= ?
    """, (icao, num_aircraft))
    users = cursor.fetchall()

    users_to_alert_channel = []
    users_to_alert_dm = []
    message = ""

    for user_id, primary_threshold, staff_up_threshold, cooldown, alert_preference, atc_rating in users:
        # ✅ Fetch opted-out positions for this user & airport
        cursor.execute("SELECT position FROM user_opt_outs WHERE user_id = ? AND icao = ?", (user_id, icao))
        opted_out_positions = {row[0] for row in cursor.fetchall()}  # Convert to set for fast lookup

        should_alert = any(
            atc_rating == config.ATC_RATING_CONVERSIONS[missing_facility] and missing_facility not in opted_out_positions
            for missing_facility in missing_atc
        ) and ((is_some_atc_missing and num_aircraft >= staff_up_threshold) or (num_aircraft >= primary_threshold and not is_any_atc_active))

        if should_alert:
            key = (user_id, icao)
            if key in alert_cooldowns:
                last_alert_time = alert_cooldowns[key]
                if (discord.utils.utcnow() - last_alert_time).total_seconds() < cooldown * 60:
                    continue  # Skip alert if cooldown is active
            
            alert_cooldowns[key] = discord.utils.utcnow()

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


# ✅ Send alerts to users
async def send_alerts(icao, num_aircraft, users_to_alert_channel, users_to_alert_dm, missing_rating, client, message):
    if users_to_alert_channel or users_to_alert_dm:
        print("send_alerts fired")

    if users_to_alert_channel:
        channel = await client.fetch_channel(int(os.getenv("DISCORD_CHANNEL_ID")))
        if channel:
            mentions = " ".join([f"<@{user_id}>" for user_id in users_to_alert_channel])
            print(f"Sent alert about {icao} to {mentions} via channel")
            await channel.send(f"{message} {mentions}")

    for user_id in users_to_alert_dm:
        user = await client.fetch_user(user_id)
        try:
            await user.send(message)
            print(f"Sent alert about {icao} to {user_id} via DMs")
        except discord.Forbidden:
            print(f"Could not DM {user_id}.")
