import logging
import config
import os
import sys
import discord # type: ignore
import dotenv # type: ignore
from alerts import send_errors, get_tag_by_name
from monitor import bot_name

# Command metadata
description = "Report a bug to the developers."
usage = f"{config.PREFIX}reportbug <description>"
quickstart_optional = True


dotenv.load_dotenv(".env")
FORUM_CHANNEL_ID = int(os.getenv("FORUM_CHANNEL_ID" if not bot_name.lower().startswith("dev") else "DEV_FORUM_CHANNEL_ID"))  # Forum channel ID


async def handle(message, client):
    forum = await client.fetch_channel(FORUM_CHANNEL_ID)
    bot_report_tag = await get_tag_by_name(forum, "Reported through bot") # if not str(client.user).lower().startswith("dev") else "Dev bot report")
    report_tag = await get_tag_by_name(forum, "Reported")
    tags = [bot_report_tag, report_tag]
    report_as_list = message.content.split()[1:]
    if not report_as_list:
        await message.channel.send("Bug report failed. Please try again and provide a description of the bug you want to report.")
        return
    report = " ".join(report_as_list)
    embed = discord.Embed(title=f"Report by {message.author.display_name}", description=f"Reporting user ID: {message.author.id}\nContent: {message.content}", color=discord.Color.red())
    embed.set_author(name=message.author.display_name, icon_url=message.author.avatar.url)
    await forum.create_thread(name=f"{report[:-1] if len(report)<=100 else report[:99]}", embed=embed, reason="New error report", applied_tags=tags)