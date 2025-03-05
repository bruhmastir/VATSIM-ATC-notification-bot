import logging
import config
import os
import sys
import discord # type: ignore
import dotenv # type: ignore

# Command metadata
description = "Report a bug to the developers."
usage = f"{config.PREFIX}reportbug <description>"


dotenv.load_dotenv(".env")
FORUM_CHANNEL_ID = int(os.getenv("FORUM_CHANNEL_ID"))

async def get_tag_by_name(channel: discord.ForumChannel, tag_name: str):
    """Finds a tag in a forum channel by its name."""
    for tag in channel.available_tags:  # Loop through all available tags
        if tag.name.lower() == tag_name.lower():
            return tag
    return None  # Return None if the tag is not found

async def handle(message, client):
    forum = await client.fetch_channel(FORUM_CHANNEL_ID)
    tag = await get_tag_by_name(forum, "Reported through bot")
    report_as_list = message.content.split()[1:]
    if not report_as_list:
        await message.channel.send("Bug report failed. Please try again and provide a description of the bug you want to report.")
        return
    report = " ".join(report_as_list)
    embed = discord.Embed(title=f"Report by {message.author.display_name}", description=message.content, color=discord.Color.red())
    embed.set_author(name=message.author.display_name, icon_url=message.author.avatar.url)
    await forum.create_thread(name=f"{report[:-1] if len(report)<=100 else report[:99]}", embed=embed, reason="New bug report", applied_tags=[tag])
    # await forum.create_thread(name=f"Report by {message.author.display_name}", embed=embed, reason="New bug report", applied_tags=[tag])
    # await forum.create_thread(name=f"Report by {message.author.display_name}", embed=embed, message=message.content, reason="New bug report", start_message=embed)
