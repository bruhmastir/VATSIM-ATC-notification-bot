import discord  # type: ignore
import sqlite3
import random

# Command metadata
description = "View your registered airports, thresholds, quiet hours, and opted-out positions."
usage = "!view"

# Randomized colors for embeds
EMBED_COLORS = [discord.Color.blue(), discord.Color.green(), discord.Color.purple(), discord.Color.orange(), discord.Color.teal()]

async def handle(message, client):
    user_id = message.author.id
    conn = sqlite3.connect("vatsim_bot.db")
    cursor = conn.cursor()

    # Fetch user preferences
    cursor.execute("""
        SELECT icao, primary_threshold, staff_up_threshold, cooldown, alert_preference, support_threshold 
        FROM user_preferences WHERE user_id = ?
    """, (user_id,))
    registered_airports = cursor.fetchall()

    # Fetch user ATC rating
    cursor.execute("SELECT atc_rating FROM user_ratings WHERE user_id = ?", (user_id,))
    user_rating = cursor.fetchone()
    user_rating = user_rating[0] if user_rating else "Not Set"

    # Fetch user quiet hours
    cursor.execute("SELECT start_time, end_time FROM user_quiet_hours WHERE user_id = ?", (user_id,))
    quiet_hours = cursor.fetchone()

    # Fetch opted-out positions
    cursor.execute("SELECT icao, position FROM user_opt_outs WHERE user_id = ?", (user_id,))
    opted_out_positions = cursor.fetchall()
    conn.close()

    # Format opt-outs
    positions = {}
    for icao, position in opted_out_positions:
        if icao in positions:
            positions[icao].append(position)
        else:
            positions[icao] = [position]
    opt_out_count = len(positions)

    # If no registrations exist, return an error message
    if not registered_airports and not user_rating:
        await message.channel.send("❌ **You have not registered any airports or set your ATC rating.**")
        return

    # Pagination setup
    pages = []

    # ✅ First Page: General Information
    embed = discord.Embed(title="🛫 __**YOUR ATC MONITORING PREFERENCES**__", color=discord.Color.gold())
    embed.add_field(name="🎖️ __**ATC Rating**__", value=f"**{user_rating}**", inline=False)
    embed.add_field(name="📊 __**Registered Airports**__", value=f"**{len(registered_airports)}**", inline=True)
    embed.add_field(name="🚫 __**Airports with Opt-Outs**__", value=f"**{opt_out_count}**", inline=True)

    if quiet_hours and quiet_hours[0] != "NA":
        embed.add_field(
            name="🕰️ __**Quiet Hours**__",
            value=f"**Start:** __{quiet_hours[0]} UTC__  |  **End:** __{quiet_hours[1]} UTC__",
            inline=False
        )
    else:
        embed.add_field(name="🕰️ __**Quiet Hours**__", value="🚫 __None (You will receive alerts 24/7)__", inline=False)

    pages.append(embed)

    # ✅ Per-Airport Pages (Each airport gets a random color)
    for icao, primary, staff_up, cooldown, alert_preference, support in registered_airports:
        embed_color = random.choice(EMBED_COLORS)  # Assign a random color for variety
        embed = discord.Embed(title=f"🏢 __**{icao} MONITORING PREFERENCES**__", color=embed_color)
        embed.add_field(name="📌 __**Primary Threshold**__", value=f"**{primary}**", inline=True)
        embed.add_field(name="📊 __**Staff-Up Threshold**__", value=f"**{staff_up}**", inline=True)
        embed.add_field(name="⏳ __**Cooldown**__", value=f"**{cooldown} min**", inline=True)
        embed.add_field(name="🔔 __**Alerts**__", value=f"**{alert_preference.upper()}**", inline=True)
        embed.add_field(name="🆘 __**Support Threshold**__", value=f"**{support}**", inline=True)
        pages.append(embed)

    # ✅ Opt-Out Page
    if opted_out_positions:
        embed = discord.Embed(title="🚫 __**OPTED-OUT POSITIONS**__", color=discord.Color.red())
        opt_out_text = "\n".join(f"**{icao}** → __{', '.join(positions[icao])}__" for icao in positions)
        embed.add_field(name="Excluded Facilities", value=opt_out_text, inline=False)
        pages.append(embed)

    # Send paginated message
    current_page = 0
    message_sent = await message.channel.send(embed=pages[current_page])

    # ✅ Add navigation buttons
    await message_sent.add_reaction("⏮️")  # Jump to first page
    await message_sent.add_reaction("⬅️")   # Previous page
    await message_sent.add_reaction("➡️")   # Next page
    await message_sent.add_reaction("⏭️")  # Jump to last page

    def check(reaction, user):
        return user == message.author and reaction.message.id == message_sent.id and str(reaction.emoji) in ["⏮️", "⬅️", "➡️", "⏭️"]

    while True:
        try:
            reaction, user = await client.wait_for("reaction_add", timeout=120.0, check=check)
            if str(reaction.emoji) == "➡️":
                current_page = (current_page + 1) % len(pages)  # Cycle forward
            elif str(reaction.emoji) == "⬅️":
                current_page = (current_page - 1) % len(pages)  # Cycle backward
            elif str(reaction.emoji) == "⏮️":
                current_page = 0  # Jump to first page
            elif str(reaction.emoji) == "⏭️":
                current_page = len(pages) - 1  # Jump to last page

            await message_sent.edit(embed=pages[current_page])
            await message_sent.remove_reaction(reaction, user)  # Remove reaction after use

        except TimeoutError:
            break  # Stop waiting if the user is inactive
