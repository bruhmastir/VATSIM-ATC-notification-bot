from dotenv import load_dotenv  # type: ignore
import os
import asyncio
import sqlite3
import discord  # type: ignore
from vatsim import get_vatsim_data
import config
import coords

alert_cooldowns = {}
supported_airports = config.SUPPORTED_AIRPORTS  # Import supported airports
atc_rating_conversions = config.ATC_RATING_CONVERSIONS


# ✅ Ensure the `user_opt_outs` table exists at startup
def setup_database():
    conn = sqlite3.connect("vatsim_bot.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_opt_outs (
            user_id INTEGER,
            icao TEXT,
            position TEXT,
            PRIMARY KEY (user_id, icao, position),
            FOREIGN KEY (user_id) REFERENCES user_ratings(user_id)
        )
    """)
    conn.commit()
    conn.close()


setup_database()  # Run on startup


async def monitor_airports(client, interval=60):
    await client.wait_until_ready()
    while not client.is_closed():
        data = get_vatsim_data()
        if not data:
            print("Failed to fetch VATSIM data.")
        else:
            conn = sqlite3.connect("vatsim_bot.db")
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT icao FROM user_preferences")
            monitored_airports = [row[0] for row in cursor.fetchall() if row[0] in supported_airports]
            conn.close()

            for icao in monitored_airports:
                await check_airport_status(icao, data, client)
        await asyncio.sleep(interval)


async def check_airport_status(icao, data, client):
    airport_lat, airport_lon = coords.get_airport_coords(icao)
    num_aircraft = sum(
        1 for p in data["pilots"]
        if p.get("groundspeed", 1) <= 40
        and abs(p.get("latitude", 0) - airport_lat) < 0.1
        and abs(p.get("longitude", 0) - airport_lon) < 0.1
    )

    conn = sqlite3.connect("vatsim_bot.db")
    cursor = conn.cursor()

    # Fetch user preferences, thresholds, and ATC rating
    cursor.execute("""
        SELECT user_id, primary_threshold, staff_up_threshold, cooldown, alert_preference, atc_rating
        FROM user_preferences JOIN user_ratings USING (user_id)
        WHERE icao = ? AND primary_threshold <= ?
    """, (icao, num_aircraft))
    users = cursor.fetchall()

    abbreviation = coords.get_abbr(icao)
    atc_units = [
        c["callsign"] for c in data["controllers"]
        if c["callsign"] and (c["callsign"].startswith(icao) or any(abbr and c["callsign"].startswith(abbr) for abbr in abbreviation))
    ]

    atc_active = {
        "CTR": any("CTR" in callsign for callsign in atc_units),
        "APP": any("APP" in callsign or "DEP" in callsign for callsign in atc_units),
        "TWR": any("TWR" in callsign for callsign in atc_units),
        "GND": any("GND" in callsign for callsign in atc_units),
        "DEL": any("DEL" in callsign for callsign in atc_units),
    }

    is_any_atc_active = any(atc_active.values())
    is_some_atc_missing = any(not status for status in atc_active.values())

    missing_atc = [facility for facility, active in atc_active.items() if not active]
    missing_rating = [atc_rating_conversions[facility] for facility in missing_atc]

    users_to_alert_channel = []
    users_to_alert_dm = []
    message = ""

    for user_id, primary_threshold, staff_up_threshold, cooldown, alert_preference, atc_rating in users:
        print("for loop entered")
        # ✅ Fetch user's opted-out positions for this airport (one query per user)
        cursor.execute("SELECT position FROM user_opt_outs WHERE user_id = ? AND icao = ?", (user_id, icao))
        opted_out_positions = {row[0] for row in cursor.fetchall()}  # Convert to set for fast lookup
        print(opted_out_positions)

        should_alert = any(
            atc_rating == atc_rating_conversions[missing_facility] and missing_facility not in opted_out_positions
            for missing_facility in missing_atc
        ) and ((is_some_atc_missing and num_aircraft >= staff_up_threshold) or (num_aircraft >= primary_threshold and not is_any_atc_active))
        
        for missing_facility in missing_atc:
            print(should_alert, f"atc_rating == atc_rating_conversions[missing_facility] is {atc_rating == atc_rating_conversions[missing_facility]}, atc_rating_conversions[missing_facility] not in opted_out_positions is {atc_rating_conversions[missing_facility] not in opted_out_positions}, currently missing_facility is {missing_facility}, currently missing_atc is {missing_atc}")


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
    await send_alerts(icao, num_aircraft, users_to_alert_channel, users_to_alert_dm, missing_rating, client, message)
    print(icao, num_aircraft, atc_active, discord.utils.utcnow())


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
