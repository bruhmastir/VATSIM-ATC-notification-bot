import config
import discord  # type: ignore
import sqlite3
from vatsim import get_vatsim_data
import coords

# Command metadata
description = "Recommend airports where you can control based on traffic and active ATC."
usage = "!recommend"

async def handle(message, client):
    user_id = message.author.id
    conn = sqlite3.connect("vatsim_bot.db")
    cursor = conn.cursor()

    # Fetch user ATC rating, tier, and allowed airports (if Unrestricted)
    cursor.execute("SELECT atc_rating, tier, unrestricted_airports FROM user_ratings WHERE user_id = ?", (user_id,))
    rating_data = cursor.fetchone()
    
    if not rating_data:
        await message.channel.send("❌ **You have not set your ATC rating. Use `!setrating` first.**")
        conn.close()
        return

    atc_rating, tier, unrestricted_airports = rating_data

    # Fetch user's opted-out positions
    cursor.execute("SELECT icao, position FROM user_opt_outs WHERE user_id = ?", (user_id,))
    opted_out_positions = cursor.fetchall()
    conn.close()

    # Convert opted-out positions into a dictionary for quick lookup
    opt_out_dict = {}
    for icao, position in opted_out_positions:
        if icao not in opt_out_dict:
            opt_out_dict[icao] = set()
        opt_out_dict[icao].add(position)

    # Fetch live VATSIM data
    data = get_vatsim_data()
    if not data:
        await message.channel.send("❌ **Failed to retrieve VATSIM data. Try again later.**")
        return

    airport_recommendations = []

    # Process airport traffic & ATC coverage
    for airport in config.SUPPORTED_AIRPORTS:
        # icao = airport.get("flight_plan", {}).get("departure")
        # if not icao:
        #     continue
        print(airport, "----------------------------------------------------------------")
        icao = airport

        # If user is Unrestricted, skip airports they are not allowed to control
        if tier == "Unrestricted": 
            if unrestricted_airports:
                allowed_airports = unrestricted_airports.split(",")
                if icao not in allowed_airports:
                    continue  # Skip this airport
            else:
                message.channel.send("You have no approved airports set. Please use !setrating to set your rating and approved airports")
                

        # Get airport traffic
        airport_lat, airport_lon = coords.get_airport_coords(icao)
        num_aircraft = sum(
            1 for p in data["pilots"]
            if p.get("groundspeed", 1) <= 40
            and abs(p.get("latitude", 0) - airport_lat) < 0.1
            and abs(p.get("longitude", 0) - airport_lon) < 0.1
        )

        # Get active ATC at the airport
        atc_units = [c["callsign"] for c in data["controllers"] if icao in c["callsign"]]
        atc_active = {
            "CTR": any("CTR" in callsign for callsign in atc_units),
            "APP": any("APP" in callsign or "DEP" in callsign for callsign in atc_units),
            "TWR": any("TWR" in callsign for callsign in atc_units),
            "GND": any("GND" in callsign for callsign in atc_units),
            "DEL": any("DEL" in callsign for callsign in atc_units),
        }

        # Determine the best position the user can control, considering opt-outs
        possible_positions = {
            "C1": ["CTR", "APP", "TWR", "GND", "DEL"],
            "S3": ["APP", "TWR", "GND", "DEL"],
            "S2": ["TWR", "GND", "DEL"],
            "S1": ["GND", "DEL"],
        }

        print(atc_active)
        print(atc_units)
        recommended_position = ""
        for position in possible_positions[atc_rating]:
            print(position)
            if not atc_active[position] and (icao not in opt_out_dict or position not in opt_out_dict[icao]):
                recommended_position += f"{position} "
                print(f"recommended: ", position)
                # break

        if recommended_position:
            airport_recommendations.append((icao, num_aircraft, recommended_position))

    # Sort by highest traffic & lowest ATC coverage
    airport_recommendations.sort(key=lambda x: (-x[1], x[2]))

    # Build embed response
    embed = discord.Embed(title="🌍 **Recommended Airports to Control**", color=discord.Color.green())
    embed.set_footer(text="Based on live traffic and ATC availability")

    if not airport_recommendations:
        embed.description = "✅ No recommendations found. You might want to check later!"
    else:
        for icao, traffic, position in airport_recommendations[:5]:  # Show top 5 recommendations
            embed.add_field(
                name=f"**{icao}** ({traffic} aircraft)",
                value=f"📌 **Recommended Positions:** `{position}`",
                inline=False
            )

    await message.channel.send(embed=embed)
