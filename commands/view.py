import discord  # type: ignore
import sqlite3
import random
import config
import logging
from discord.ui import View, Button  # type: ignore

# Command metadata
description = "View your registered airports, thresholds, quiet hours, rating information, and opted-out positions."
usage = f"{config.PREFIX}view"

# Randomized colors for embeds
EMBED_COLORS = [discord.Color.blue(), discord.Color.green(), discord.Color.purple(), discord.Color.orange(), discord.Color.teal()]

class ViewPreferences(View):
    def __init__(self, pages, user_id, page=0):
        super().__init__()
        self.pages = pages
        self.page = page
        self.user_id = user_id
        self.max_page = len(pages) - 1
        self.update_buttons()

    def update_buttons(self):
        """Dynamically update buttons based on the current page."""
        self.clear_items()
        if self.page == 0:
            self.add_item(Button(label="⏮ First", style=discord.ButtonStyle.primary, custom_id="first", disabled=True))
            self.add_item(Button(label="⬅ Previous", style=discord.ButtonStyle.primary, custom_id="prev", disabled=True))
            self.add_item(Button(label="Next ➡", style=discord.ButtonStyle.primary, custom_id="next"))
            self.add_item(Button(label="Last ⏭", style=discord.ButtonStyle.primary, custom_id="last"))
        elif self.page == self.max_page:
            self.add_item(Button(label="⏮ First", style=discord.ButtonStyle.primary, custom_id="first"))
            self.add_item(Button(label="⬅ Previous", style=discord.ButtonStyle.primary, custom_id="prev"))
            self.add_item(Button(label="Next ➡", style=discord.ButtonStyle.primary, custom_id="next", disabled=True))
            self.add_item(Button(label="Last ⏭", style=discord.ButtonStyle.primary, custom_id="last", disabled=True))
        else:
            self.add_item(Button(label="⏮ First", style=discord.ButtonStyle.primary, custom_id="first"))
            self.add_item(Button(label="⬅ Previous", style=discord.ButtonStyle.primary, custom_id="prev"))
            self.add_item(Button(label="Next ➡", style=discord.ButtonStyle.primary, custom_id="next"))
            self.add_item(Button(label="Last ⏭", style=discord.ButtonStyle.primary, custom_id="last"))
            

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Handles button interactions."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("⛔ You can't control this menu!", ephemeral=True)
            return False

        button_id = interaction.data["custom_id"]

        if button_id == "next":
            self.page += 1
        elif button_id == "prev":
            self.page -= 1
        elif button_id == "first":
            self.page = 0
        elif button_id == "last":
            self.page = self.max_page

        self.update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.page], view=self)
        return True


async def handle(message, client):
    args = message.content.split()
    user_id = message.author.id
    mentioned_user = message.mentions[0] if len(args) > 1 and message.mentions else None
    if mentioned_user:
        user_id = mentioned_user.id
    
    conn = sqlite3.connect("vatsim_bot.db")
    cursor = conn.cursor()

    # Fetch user preferences
    cursor.execute("""
        SELECT icao, primary_threshold, staff_up_threshold, cooldown, alert_preference, support_threshold 
        FROM user_preferences WHERE user_id = ?
    """, (user_id,))
    registered_airports = cursor.fetchall()

    # Fetch user ATC rating and training details
    cursor.execute("SELECT atc_rating, tier FROM user_ratings WHERE user_id = ?", (user_id,))
    user_rating = cursor.fetchone()
    
    cursor.execute("SELECT training_rating, training_tier, training_airport FROM user_training WHERE user_id = ?", (user_id,))
    training_info = cursor.fetchone()
    
    cursor.execute("SELECT start_time, end_time FROM user_quiet_hours WHERE user_id = ?", (user_id,))
    quiet_hours = cursor.fetchone()

    cursor.execute("SELECT icao, position FROM user_opt_outs WHERE user_id = ?", (user_id,))
    opted_out_positions = cursor.fetchall()
    conn.close()

    username = mentioned_user.display_name if mentioned_user else message.author.display_name
    
    positions = {}
    for icao, position in opted_out_positions:
        if icao in positions:
            positions[icao].append(position)
        else:
            positions[icao] = [position]
    opt_out_count = len(positions)
    
    pages = []
    constant_pages = 3
    num_pages = constant_pages + len(registered_airports)
    j = 1

    # Page 1: Summary
    embed = discord.Embed(title=f"🛫 {username}'s ATC Preferences", color=discord.Color.gold())
    if user_rating:
        embed.add_field(name="🎖️ __Current Rating & Tier__", value=f"**{user_rating[0]} {user_rating[1]}**", inline=False)
    embed.add_field(name="📊 __Registered Airports__", value=f"**{len(registered_airports)}**", inline=True)
    embed.add_field(name="🚫 __Airports with Opt-Outs__", value=f"**{opt_out_count}**", inline=True)
    if quiet_hours and quiet_hours[0] != "NA":
        embed.add_field(name="🕰️ __Quiet Hours__", value=f"**Start:** __{quiet_hours[0]} UTC__  |  **End:** __{quiet_hours[1]} UTC__", inline=False)
    else:
        embed.add_field(name="🕰️ __Quiet Hours__", value="🚫 __None (24/7 Alerts)__", inline=False)
    embed.set_footer(text=f"Page {j}/{num_pages}")
    pages.append(embed)

    # Page 2: Opt-Outs
    embed = discord.Embed(title="🚫 __Opted-Out Positions__", color=discord.Color.red())
    opt_out_text = "\n".join(f"**{icao}** → __{', '.join(positions[icao])}__" for icao in positions)
    embed.add_field(name="Excluded Facilities", value=opt_out_text if opt_out_text else "None", inline=False)
    j += 1
    embed.set_footer(text=f"Page {j}/{num_pages}")
    pages.append(embed)

    # Page 3: Rating & Training Details
    embed = discord.Embed(title="🎯 __ATC Rating & Training Details__", color=discord.Color.blue())
    if user_rating:
        embed.add_field(name="🏅 __Current Rating & Tier__", value=f"**{user_rating[0]} {user_rating[1]}**", inline=False)
    if training_info:
        embed.add_field(name="🎯 __Training Towards__", value=f"**{training_info[0]} {training_info[1]}**", inline=True)
        embed.add_field(name="📍 __Training Airport__", value=f"**{training_info[2]}**" if training_info[1] == "Unrestricted" else "**OMDB**", inline=True)
    j += 1
    embed.set_footer(text=f"Page {j}/{num_pages}")
    pages.append(embed)

    # Pages 4+: Per-Airport Details
    for i, (icao, primary, staff_up, cooldown, alert_preference, support) in enumerate(registered_airports, start=1 + j):
        embed_color = random.choice(EMBED_COLORS)
        embed = discord.Embed(title=f"🏢 __{icao} Monitoring Preferences__", color=embed_color)
        embed.add_field(name="📌 __Primary Threshold__", value=f"**{primary}**", inline=True)
        embed.add_field(name="📊 __Staff-Up Threshold__", value=f"**{staff_up}**", inline=True)
        embed.add_field(name="⏳ __Cooldown__", value=f"**{cooldown} min**", inline=True)
        embed.add_field(name="🔔 __Alert Preference__", value=f"**{alert_preference.upper()}**", inline=True)
        embed.add_field(name="🆘 __Support Threshold__", value=f"**{support}**", inline=True)
        embed.set_footer(text=f"Page {i}/{num_pages}")
        pages.append(embed)

    # Send paginated message
    view = ViewPreferences(pages, user_id)
    await message.channel.send(embed=pages[0], view=view)
