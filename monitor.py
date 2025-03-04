from dotenv import load_dotenv  # type: ignore
import os
import asyncio
import sqlite3
import discord  # type: ignore
from vatsim import get_vatsim_data
import config
import coords
from alerts import get_users_to_alert, send_alerts

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

    # ✅ Fetch users to alert and send notifications
    users_to_alert_channel, users_to_alert_dm, message = get_users_to_alert(
        icao, num_aircraft, missing_atc, is_any_atc_active, is_some_atc_missing
    )

    await send_alerts(icao, num_aircraft, users_to_alert_channel, users_to_alert_dm, missing_atc, client, message)

    print(icao, num_aircraft, atc_active, discord.utils.utcnow())
