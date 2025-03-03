# # # import requests

# # # def get_vatsim_data():
# # #     url = "https://data.vatsim.net/v3/vatsim-data.json"
# # #     response = requests.get(url)
# # #     return response.json() if response.status_code == 200 else None

# # # def count_departures_without_atc(icao):
# # #     data = get_vatsim_data()
# # #     if not data:
# # #         print("Failed to fetch VATSIM data.")
# # #         return
    
# # #     # Get pilots on the ground at the airport
# # #     departures = [p for p in data['pilots'] if p.get('flight_plan')
# # #                   and p['flight_plan'].get('departure') == icao
# # #                   and p.get('groundspeed', 1) == 0]
    
# # #     # Get controllers covering the airport, ignoring observers (facility = 0)
# # #     atc_units = [c['callsign'] for c in data['controllers'] if icao in c.get('callsign', '') and c.get('facility', -1) > 0]
    
# # #     if len(departures) > 15 and not atc_units:
# # #         print(f"Alert: {icao} has {len(departures)} departures on the ground with no ATC!")
# # #     else:
# # #         atc_list = ', '.join(atc_units) if atc_units else "None"
# # #         print(f"{icao} is fine: {len(departures)} departures. Active ATC: {atc_list}")

# # # # Example usage
# # # icao_code = input("Enter airport ICAO (e.g., OMDB): ").strip().upper()
# # # count_departures_without_atc(icao_code)












# # import requests
# # import time

# # def get_vatsim_data():
# #     url = "https://data.vatsim.net/v3/vatsim-data.json"
# #     response = requests.get(url)
# #     return response.json() if response.status_code == 200 else None

# # def monitor_airports(icao_list, interval=60):
# #     while True:
# #         data = get_vatsim_data()
# #         if not data:
# #             print("Failed to fetch VATSIM data.")
# #         else:
# #             for icao in icao_list:
# #                 check_airport_status(icao, data)
# #         time.sleep(interval)

# # def check_airport_status(icao, data):
# #     # Get pilots on the ground at the airport
# #     departures = [p for p in data['pilots'] if p.get('flight_plan')
# #                   and p['flight_plan'].get('departure') == icao
# #                   and p.get('groundspeed', 1) == 0]
    
# #     # Get controllers covering the airport, ignoring observers (facility = 0)
# #     atc_units = [c['callsign'] for c in data['controllers'] if icao in c.get('callsign', '') and c.get('facility', -1) > 0]
    
# #     if len(departures) > 15 and not atc_units:
# #         print(f"🚨 ATC NEEDED: {icao} has {len(departures)} departures on the ground with no ATC! 🚨")
# #     else:
# #         atc_list = ', '.join(atc_units) if atc_units else "None"
# #         # print(f"{icao}: {len(departures)} departures. Active ATC: {atc_list}")

# # # List of airports to monitor
# # airports_to_monitor = ["OMDB", "OMAA", "OMSJ", "OMDW", "OMDM"]

# # # Start monitoring
# # try:
# #     monitor_airports(airports_to_monitor, interval=60)  # Check every 60 seconds
# # except KeyboardInterrupt:
# #     print("Monitoring stopped.")
































# import datetime
# import requests
# import time
# import discord
# import asyncio

# # Discord Bot Configuration
# TOKEN = "MTM0NTgwMDM1ODU2NzYxMjUzOQ.GKS210.rX4mh7ailSOfFy87KOL0J_s2m7a_ShHKNUd-F4" # Bot token
# CHANNEL_ID = 1345801890780156068 # Replace with your Discord channel ID


# # Store user preferences
# user_preferences = {}  # {user_id: {icao: {"primary_threshold": X, "secondary_threshold": Y}}}
# user_quiet_hours = {}  # {user_id: [(start, end)]}
# # Store cooldown timestamps and last alert level per user per airport
# cooldown_tracker = {}  # {(user_id, icao): cooldown_end}
# alert_level_tracker = {}  # {(user_id, icao): last_alert_level}

# # Initialize Discord Client
# intents = discord.Intents.default()
# intents.messages = True
# intents.message_content = True
# client = discord.Client(intents=intents)

# def get_vatsim_data():
#     url = "https://data.vatsim.net/v3/vatsim-data.json"
#     response = requests.get(url)
#     return response.json() if response.status_code == 200 else None

# async def monitor_airports(interval=60):
#     await client.wait_until_ready()
#     channel = client.get_channel(CHANNEL_ID)
#     if not channel:
#         print("Failed to find Discord channel.")
#         return
    
#     while not client.is_closed():
#         data = get_vatsim_data()
#         if not data:
#             print("Failed to fetch VATSIM data.")
#         else:
#             for user_id, airports in user_preferences.items():
#                 for icao, config in airports.items():
#                     await check_airport_status(user_id, icao, config, data, channel)
#         await asyncio.sleep(interval)

# async def check_airport_status(user_id, icao, config, data, channel):
#     current_time = time.time()
#     current_utc = datetime.now().time()
#     cooldown_end = cooldown_tracker.get((user_id, icao), 0)
#     last_alert_level = alert_level_tracker.get((user_id, icao), 0)
    
#     # Check quiet hours
#     for start, end in user_quiet_hours.get(user_id, []):
#         if start <= current_utc <= end:
#             return  # Skip notifications during quiet hours
    
#     # Get pilots on the ground at the airport
#     departures = [p for p in data['pilots'] if p.get('flight_plan')
#                   and p['flight_plan'].get('departure') == icao
#                   and p.get('groundspeed', 1) == 0]
    
#     # Get controllers covering the airport, including top-down service
#     atc_units = [c['callsign'] for c in data['controllers'] if (
#         any(c['callsign'].startswith(icao) for _ in range(4))
#     ) and c.get('facility', -1) > 0]
    
#     num_departures = len(departures)
#     primary_threshold = config['primary_threshold']
#     secondary_threshold = config['secondary_threshold']
#     cooldown_time = 1200  # 20-minute cooldown
    
#     if num_departures > secondary_threshold and not atc_units:
#         if current_time > cooldown_end or last_alert_level < 2:
#             message = f"🚨 <@{user_id}> ATC NEEDED: {icao} has {num_departures} departures on the ground with no ATC! 🚨"
#             await channel.send(message)
#             cooldown_tracker[(user_id, icao)] = current_time + cooldown_time
#             alert_level_tracker[(user_id, icao)] = 2
#     elif num_departures > primary_threshold and not atc_units:
#         if current_time > cooldown_end or last_alert_level < 1:
#             message = f"🚨 <@{user_id}> ATC NEEDED: {icao} has {num_departures} departures on the ground with no ATC! 🚨"
#             await channel.send(message)
#             cooldown_tracker[(user_id, icao)] = current_time + cooldown_time
#             alert_level_tracker[(user_id, icao)] = 1
#     elif current_time > cooldown_end:
#         alert_level_tracker[(user_id, icao)] = 0  # Reset alert level after cooldown ends
    
#     atc_list = ', '.join(atc_units) if atc_units else "None"
#     print(f"{icao}: {num_departures} departures. Active ATC: {atc_list}")

# @client.event
# async def on_ready():
#     print(f"Logged in as {client.user}")
#     await monitor_airports(interval=60)

# @client.event
# async def on_message(message):
#     if message.author == client.user:
#         return
    
#     if message.content.startswith("!register"):
#         user_id = message.author.id
#         user_preferences[user_id] = {}

#         await message.channel.send("Enter the ICAO codes of the airports you want to monitor (comma-separated):")
#         def check(m): return m.author == message.author and m.channel == message.channel
#         icao_response = await client.wait_for("message", check=check)
#         icaos = [icao.strip().upper() for icao in icao_response.content.split(",")]

#         for icao in icaos:
#             await message.channel.send(f"Set primary threshold for {icao}:")
#             primary_response = await client.wait_for("message", check=check)
#             await message.channel.send(f"Set secondary threshold for {icao}:")
#             secondary_response = await client.wait_for("message", check=check)
#             try:
#                 user_preferences[user_id][icao] = {
#                     "primary_threshold": int(primary_response.content),
#                     "secondary_threshold": int(secondary_response.content)
#                 }
#             except ValueError:
#                 await message.channel.send(f"Invalid threshold values for {icao}, registration skipped.")
#                 continue

#         await message.channel.send("Set your quiet hours (UTC) in the format HH:MM-HH:MM, or type 'none' to skip:")
#         quiet_response = await client.wait_for("message", check=check)
#         if quiet_response.content.lower() != "none":
#             try:
#                 start, end = quiet_response.content.split("-")
#                 start_time = datetime.datetime.strptime(start.strip(), "%H:%M").time()
#                 end_time = datetime.datetime.strptime(end.strip(), "%H:%M").time()
#                 user_quiet_hours[user_id] = [(start_time, end_time)]
#             except ValueError:
#                 await message.channel.send("Invalid quiet hours format, skipping.")
        
#         await message.channel.send(f"Registration complete, {message.author.mention}!")

# # Start the bot
# client.run(TOKEN)









import requests
import time
import discord
import asyncio
import sqlite3
from datetime import datetime

# Discord Bot Configuration
TOKEN = "YOUR_DISCORD_BOT_TOKEN"  # Replace with your bot's token
CHANNEL_ID = 123456789012345678  # Replace with your Discord channel ID

# Initialize database connection
conn = sqlite3.connect("vatsim_bot.db")
cursor = conn.cursor()

# Create tables if they don't exist
cursor.execute("""
CREATE TABLE IF NOT EXISTS user_preferences (
    user_id INTEGER,
    icao TEXT,
    primary_threshold INTEGER,
    secondary_threshold INTEGER,
    cooldown INTEGER,
    PRIMARY KEY (user_id, icao)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS user_quiet_hours (
    user_id INTEGER PRIMARY KEY,
    start_time TEXT,
    end_time TEXT
)
""")

conn.commit()

# Initialize Discord Client
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
client = discord.Client(intents=intents)

def get_vatsim_data():
    url = "https://data.vatsim.net/v3/vatsim-data.json"
    response = requests.get(url)
    return response.json() if response.status_code == 200 else None

async def monitor_airports(interval=60):
    await client.wait_until_ready()
    channel = client.get_channel(CHANNEL_ID)
    if not channel:
        print("Failed to find Discord channel.")
        return
    
    while not client.is_closed():
        data = get_vatsim_data()
        if not data:
            print("Failed to fetch VATSIM data.")
        else:
            cursor.execute("SELECT user_id, icao, primary_threshold, secondary_threshold, cooldown FROM user_preferences")
            for user_id, icao, primary_threshold, secondary_threshold, cooldown in cursor.fetchall():
                config = {"primary_threshold": primary_threshold, "secondary_threshold": secondary_threshold, "cooldown": cooldown}
                await check_airport_status(user_id, icao, config, data, channel)
        await asyncio.sleep(interval)

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    await monitor_airports(interval=60)

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    
    if message.content.startswith("!register"):
        user_id = message.author.id
        while True:
            await message.channel.send("Enter the ICAO code of the airport you want to monitor:")
            def check(m): return m.author == message.author and m.channel == message.channel
            icao_response = await client.wait_for("message", check=check)
            icao = icao_response.content.strip().upper()

            await message.channel.send(f"Set primary threshold for {icao}:")
            primary_response = await client.wait_for("message", check=check)
            await message.channel.send(f"Set secondary threshold for {icao}:")
            secondary_response = await client.wait_for("message", check=check)
            await message.channel.send(f"Set cooldown time in minutes for {icao}:")
            cooldown_response = await client.wait_for("message", check=check)
            
            try:
                cursor.execute("REPLACE INTO user_preferences (user_id, icao, primary_threshold, secondary_threshold, cooldown) VALUES (?, ?, ?, ?, ?)",
                               (user_id, icao, int(primary_response.content), int(secondary_response.content), int(cooldown_response.content)))
                conn.commit()
            except ValueError:
                await message.channel.send(f"Invalid values for {icao}, registration skipped.")
                continue

            await message.channel.send("Do you want to add another airport? (yes/no)")
            add_more_response = await client.wait_for("message", check=check)
            if add_more_response.content.lower() != "yes":
                break

        cursor.execute("SELECT * FROM user_quiet_hours WHERE user_id = ?", (user_id,))
        if not cursor.fetchone():
            await message.channel.send("You haven't set quiet hours yet. Enter quiet hours (UTC) in the format HH:MM-HH:MM:")
            quiet_response = await client.wait_for("message", check=check)
            try:
                start, end = quiet_response.content.split("-")
                cursor.execute("INSERT INTO user_quiet_hours (user_id, start_time, end_time) VALUES (?, ?, ?)",
                               (user_id, start.strip(), end.strip()))
                conn.commit()
            except ValueError:
                await message.channel.send("Invalid time format. Use HH:MM-HH:MM (UTC)")
    
        await message.channel.send("Registration complete!")
    
    if message.content.startswith("!help"):
        help_text = (
            "**Available Commands:**\n"
            "`!register` - Register for airport monitoring. Adds one airport at a time.\n"
            "`!setquiet` - Set or update your quiet hours (UTC).\n"
            "`!view` - View your registered airports, thresholds, and cooldowns.\n"
            "`!remove` - Remove a registered airport from your list.\n"
            "`!help` - Show this help message."
        )
        await message.channel.send(help_text)
    
    if message.content.startswith("!setquiet"):
        user_id = message.author.id
        await message.channel.send("Enter quiet hours (UTC) in the format HH:MM-HH:MM:")
        quiet_response = await client.wait_for("message", check=lambda m: m.author == message.author)
        
        try:
            start, end = quiet_response.content.split("-")
            cursor.execute("REPLACE INTO user_quiet_hours (user_id, start_time, end_time) VALUES (?, ?, ?)",
                           (user_id, start.strip(), end.strip()))
            conn.commit()
            await message.channel.send("Quiet hours updated.")
        except ValueError:
            await message.channel.send("Invalid time format. Use HH:MM-HH:MM (UTC)")

# Discord Bot Configuration
TOKEN = "MTM0NTgwMDM1ODU2NzYxMjUzOQ.GKS210.rX4mh7ailSOfFy87KOL0J_s2m7a_ShHKNUd-F4" # Bot token
CHANNEL_ID = 1345801890780156068 # Replace with your Discord channel ID

# Start the bot
client.run(TOKEN)
