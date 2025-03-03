from dotenv import load_dotenv
import os
import asyncio
import sqlite3
import discord
from vatsim import get_vatsim_data
import config

alert_cooldowns = {}
supported_airports = config.SUPPORTED_AIRPORTS  # Import supported airports

async def monitor_airports(client, interval=60):
    await client.wait_until_ready()
    while not client.is_closed():
        data = get_vatsim_data()
        if not data:
            print("Failed to fetch VATSIM data.")
        else:
            conn = sqlite3.connect("vatsim_bot.db")
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT icao FROM user_preferences
            """)
            monitored_airports = [row[0] for row in cursor.fetchall() if row[0] in supported_airports]
            conn.close()
            
            for icao in monitored_airports:
                await check_airport_status(icao, data, client)
        await asyncio.sleep(interval)

async def check_airport_status(icao, data, client):
    num_departures = sum(1 for p in data['pilots'] if p.get('flight_plan') and p['flight_plan'].get('departure') == icao and p.get('groundspeed', 1) <= 40)

    conn = sqlite3.connect("vatsim_bot.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT user_id, primary_threshold, tertiary_threshold, cooldown, alert_preference, atc_rating
        FROM user_preferences JOIN user_ratings USING (user_id)
        WHERE icao = ? AND primary_threshold <= ?
    """, (icao, num_departures))
    users = cursor.fetchall()
    conn.close()

    # num_departures = sum(1 for p in data['pilots'] if p.get('flight_plan') and p['flight_plan'].get('departure') == icao and p.get('groundspeed', 1) == 0)
    atc_units = [c['callsign'] for c in data['controllers'] if icao in c['callsign']]

    atc_active = {
        "CTR": any("CTR" in callsign for callsign in atc_units),
        "APP": any("APP" in callsign or "DEP" in callsign for callsign in atc_units),
        "TWR": any("TWR" in callsign for callsign in atc_units),
        "GND": any("GND" in callsign for callsign in atc_units),
        "DEL": any("DEL" in callsign for callsign in atc_units)
    }
    
    users_to_alert_channel = []
    users_to_alert_dm = []
    missing_rating = ""
    message = ""

    for user_id, primary_threshold, tertiary_threshold, cooldown, alert_preference, atc_rating in users:
        # print(missing_rating)

        
        is_atc_active = any(atc_active.values())
        is_some_atc_missing = any(value == False for value in atc_active.values())


        # Check if exceeded primary threshold
        if num_departures >= primary_threshold and not is_atc_active:
            message = f"🚨 ATC NEEDED: {icao} has {num_departures} departures with no ATC online! 🚨"
            missing_rating = atc_rating

            
        # Check if any of the ATC facilities are unavailable and tertiary threshold is exceeded
        elif is_some_atc_missing and num_departures >= tertiary_threshold:
            missing_atc = ""
            for facility in atc_active:
                # print(facility)
                # print(atc_active)
                # print(facility.value)
                if atc_active[facility] == False:
                    missing_atc += facility
            message = f"🚨 ATC NEEDED: {icao} has {num_departures} departures with only partial ATC online. {missing_atc} is needed! 🚨"
        
        if missing_rating:
            key = (user_id, icao)
            if key in alert_cooldowns:
                last_alert_time = alert_cooldowns[key]
                if (discord.utils.utcnow() - last_alert_time).total_seconds() < cooldown * 60:
                    continue  # Skip alert if cooldown is active
            
            alert_cooldowns[key] = discord.utils.utcnow()
            
            if alert_preference == "dm":
                users_to_alert_dm.append(user_id)
            else:
                users_to_alert_channel.append(user_id)
            # await send_alerts(icao, num_departures, users_to_alert_channel, users_to_alert_dm, missing_rating, client, message)

    
    await send_alerts(icao, num_departures, users_to_alert_channel, users_to_alert_dm, missing_rating, client, message)
    print(icao, num_departures, atc_active, discord.utils.utcnow())

async def send_alerts(icao, num_departures, users_to_alert_channel, users_to_alert_dm, missing_rating, client, message):
    # message = f"🚨 ATC NEEDED: {icao} has {num_departures} departures with only lower ATC online. {missing_rating} is needed! 🚨"
    if users_to_alert_channel or users_to_alert_dm: print("send_alerts fired")
    if users_to_alert_channel:
        # channel = discord.utils.get(client.get_all_channels(), name="general")
        channel = await client.fetch_channel(int(os.getenv("DISCORD_CHANNEL_ID")))  # Replace with actual channel ID

        # print(channel)
        if channel:
            mentions = " ".join([f"<@{user_id}>" for user_id in users_to_alert_channel])
            print(f"sent alert about {icao} to {mentions} via channel")
            await channel.send(f"{message} {mentions}")
            
    
    for user_id in users_to_alert_dm:
        user = await client.fetch_user(user_id)
        try:
            await user.send(message)
            print(f"sent alert about {icao} to {user_id} via DMs")
        except discord.Forbidden:
            print(f"Could not DM {user_id}.")
