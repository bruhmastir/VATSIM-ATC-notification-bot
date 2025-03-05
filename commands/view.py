import logging
import config
import discord  # type: ignore
import sqlite3
import random
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
    self_check = len(args) == 1 or(len(args) > 1 and message.mentions and message.mentions[0].id == message.author.id)
    user_id = message.mentions[0].id if message.mentions else message.author.id
    if not message.mentions and len(args) > 1:
        await message.channel.send(f"❌ **Incorrect usage. Correct usage: `{usage}`\n       For more details, check `{config.PREFIX}help view`**")
        return
    conn = sqlite3.connect("vatsim_bot.db")
    cursor = conn.cursor()

    # Fetch user preferences
    cursor.execute("""
        SELECT icao, primary_threshold, staff_up_threshold, cooldown, alert_preference, support_threshold 
        FROM user_preferences WHERE user_id = ?
    """, (user_id,))
    registered_airports = cursor.fetchall()

    # Fetch user ATC rating
    cursor.execute("SELECT atc_rating, tier, unrestricted_airports FROM user_ratings WHERE user_id = ?", (user_id,))
    rating_info = cursor.fetchone()
    user_rating_info = rating_info if rating_info else "Not Set"
    logging.debug(f"{user_rating_info}")
    user_rating = user_rating_info[0] if user_rating_info != "Not Set" else None
    tier = user_rating_info[1]
    unrestricted_airports = user_rating_info[2] if user_rating_info[2] else "All"
    if "," in unrestricted_airports:
        airports = ""
        for letter in unrestricted_airports:
            if letter == ",":
                airports += " , "
            else:
                airports += letter
        unrestricted_airports = airports

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
        await message.channel.send("❌ **You have not registered any airports or set your ATC rating.**" if self_check else "❌ **This user has not registered any airports or set his/her ATC rating.**")
        return

    # Pagination setup
    pages = []
    total_pages = len(pages) if len(pages) > 0 else len(registered_airports)+2
    current_page = 0
    # ✅ First Page: General Information
    embed = discord.Embed(title="🛫 __**YOUR ATC MONITORING PREFERENCES**__", color=discord.Color.gold())
    embed.add_field(name="🎖️ __**ATC Rating**__", value=f"**{user_rating}**", inline=True)
    embed.add_field(name="🎖️ __**ATC Rating Tier**__", value=f"**{tier}**", inline=True)
    embed.add_field(name="📊 __**Approved Airports**__", value=f"**{unrestricted_airports}**", inline=False)
    embed.add_field(name="📊 __**Registered Airports**__", value=f"**{len(registered_airports)}**", inline=True)
    embed.add_field(name="🚫 __**Airports with Opt-Outs**__", value=f"**{opt_out_count}**", inline=True)
    embed.set_footer(text=f"Page {1}/{total_pages}")

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
        current_page += 1
        embed_color = random.choice(EMBED_COLORS)  # Assign a random color for variety
        embed = discord.Embed(title=f"🏢 __**{icao} MONITORING PREFERENCES**__", color=embed_color)
        embed.add_field(name="📌 __**Primary Threshold**__", value=f"**{primary}**", inline=True)
        embed.add_field(name="📊 __**Staff-Up Threshold**__", value=f"**{staff_up}**", inline=True)
        embed.add_field(name="⏳ __**Cooldown**__", value=f"**{cooldown} min**", inline=True)
        embed.add_field(name="🔔 __**Alerts**__", value=f"**{alert_preference.upper()}**", inline=True)
        embed.add_field(name="🆘 __**Support Threshold**__", value=f"**{support}**", inline=True)
        embed.set_footer(text=f"Page {current_page + 1}/{total_pages}")
        pages.append(embed)

    # ✅ Opt-Out Page
    embed = discord.Embed(title="🚫 __**OPTED-OUT POSITIONS**__", color=discord.Color.red())
    opt_out_text = "\n".join(f"**{icao}** → __{', '.join(positions[icao])}__" for icao in positions) if opted_out_positions else "None"
    embed.add_field(name="Excluded Facilities", value=opt_out_text, inline=False)
    embed.set_footer(text=f"Page {current_page + 2}/{total_pages}")
    pages.append(embed)

    # Send paginated message
    view = ViewPreferences(pages, user_id)
    await message.channel.send(embed=pages[0], view=view)
