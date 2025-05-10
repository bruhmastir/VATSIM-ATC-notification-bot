import asyncio
import logging
import config
import os
import sys
import discord # type: ignore
import dotenv # type: ignore
from alerts import send_errors, get_tag_by_name
import finder

bot_name = finder.bot_name
PREFIX = finder.find_prefix(bot_name)

# Command metadata
description = "Report a bug to the developers."
usage = f"`{PREFIX}reportbug [description]`"
quickstart_optional = True


dotenv.load_dotenv(".env")
DEVELOPER_ROLE_ID = int(os.getenv("DEVELOPER_ROLE_ID"))  # Bot owner ID



async def handle(message, client):
    try:
        bot_name = finder.bot_name
        prefix = finder.find_prefix(bot_name)
        FORUM_CHANNEL_ID = int(os.getenv("FORUM_CHANNEL_ID" if not bot_name.lower().startswith("dev") else "DEV_FORUM_CHANNEL_ID"))  # Forum channel ID
        forum = await client.fetch_channel(FORUM_CHANNEL_ID)
        bot_report_tag = await get_tag_by_name(forum, "Reported through bot") # if not str(client.user).lower().startswith("dev") else "Dev bot report")
        report_tag = await get_tag_by_name(forum, "Reported")
        mention = f"<@&{DEVELOPER_ROLE_ID}>"
        tags = [bot_report_tag, report_tag]
        report_as_list = message.content.split()[1:]
        if not report_as_list:
            await message.channel.send("Bug report failed. Please try again and provide a description of the bug you want to report.")
            return
        report = " ".join(report_as_list)
        embed = discord.Embed(title=f"Report by {message.author.display_name}", description=f"Reporting user ID: {message.author.id}\nContent: {message.content}", color=discord.Color.red())
        embed.set_author(name=message.author.display_name, icon_url=message.author.avatar.url if message.author.avatar else None)
        await forum.create_thread(name=f"{report[:-1] if len(report)<=100 else report[:99]}", content=f"{mention}",embed=embed, reason="New error report", applied_tags=tags)
        await message.channel.send("Bug report submitted successfully. The developers have been notified.")
        logging.info(f"Bug report submitted by {message.author.display_name} with content: {report}")
    except Exception as e:
        logging.error(f"Error in reportbug: {e}")
        await send_errors("reportbug", client, e)
        await message.channel.send("An error occurred while submitting the bug report. The developers have been notified.")



async def handle(message, client):
    try:
        bot_name = finder.bot_name
        prefix = finder.find_prefix(bot_name)
        FORUM_CHANNEL_ID = int(os.getenv("FORUM_CHANNEL_ID" if not bot_name.lower().startswith("dev") else "DEV_FORUM_CHANNEL_ID"))
        forum = await client.fetch_channel(FORUM_CHANNEL_ID)
        bot_report_tag = await get_tag_by_name(forum, "Reported through bot")
        report_tag = await get_tag_by_name(forum, "Reported")
        tags = [bot_report_tag, report_tag]
        mention = f"<@&{DEVELOPER_ROLE_ID}>"

        report_as_list = message.content.split()[1:]

        # If no description was provided, prompt the user
        if not report_as_list:
            await message.channel.send("Please describe the bug you'd like to report:")
            def check(m):
                return m.author == message.author and m.channel == message.channel

            try:
                response = await client.wait_for("message", timeout=60.0, check=check)
                report = response.content.strip()
                if not report:
                    await message.channel.send("Bug report was empty. Cancelling.")
                    return
            except asyncio.TimeoutError:
                await message.channel.send("Bug report timed out. Please try again later.")
                return
        else:
            report = " ".join(report_as_list)

        embed = discord.Embed(
            title=f"Report by {message.author.display_name}",
            description=f"Reporting user ID: {message.author.id}\nContent: {report}",
            color=discord.Color.red()
        )
        embed.set_author(name=message.author.display_name, icon_url=message.author.avatar.url if message.author.avatar else None)

        await forum.create_thread(
            name=(report[:100] if len(report) <= 100 else report[:99]),
            content=mention,
            embed=embed,
            reason="New error report",
            applied_tags=tags
        )
        await message.channel.send("Bug report submitted successfully. The developers have been notified.")
        logging.info(f"Bug report submitted by {message.author.display_name} with content: {report}")
    except Exception as e:
        logging.error(f"Error in reportbug: {e}")
        await send_errors("reportbug", client, e)
        await message.channel.send("An error occurred while submitting the bug report. The developers have been notified.")