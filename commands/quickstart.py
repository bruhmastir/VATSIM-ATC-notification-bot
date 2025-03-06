import discord  # type: ignore
import asyncio
import config
import commands.setrating # import handle as setrating
import commands.register # import handle as register
import commands.optout # import handle as optout
import commands.optin # import handle as optin
import commands.setquiet # import handle as setquiet
import commands.settraining # import handle as settraining
import commands.observe # import handle as observe
import commands.observehours # import handle as observehours
import commands.view # import handle as view
import commands.recommend # import handle as recommend
import commands.supportme # import handle as supportme
import commands.edit # import handle as edit
import commands.remove # import handle as remove
import commands.help # import handle as help_command
import commands.reportbug # import handle as reportbug

# Command metadata
description = "Guided setup tutorial for new users."
usage = f"{config.PREFIX}quickstart"

# Tutorial steps
TUTORIAL_STEPS = [
    (commands.setrating.handle, "Set your ATC rating (S1, S2, etc.).", False),
    (commands.register.handle, "Register an airport for monitoring.", False),
    (commands.optout.handle, "Opt out of alerts for specific positions.", True),
    (commands.optin.handle, "Opt back into alerts for previously opted-out positions.", True),
    (commands.setquiet.handle, "Set quiet hours to avoid alerts during specific times.", True),
    (commands.settraining.handle, "Set your training progress.", True),
    (commands.observe.handle, "Observe when your training facility comes online.", True),
    (commands.observehours.handle, "Automatically observe daily during a set time period.", True),
    (commands.view.handle, "View your current settings.", False),
    (commands.recommend.handle, "Get airport recommendations based on traffic and ATC availability.", True),
    (commands.supportme.handle, "Request support from other controllers.", True),
    (commands.edit.handle, "Edit your registered airport settings.", True),
    (commands.remove.handle, "Remove an airport from monitoring.", True),
    (commands.help.handle, "Show available commands and their usage.", False),
    (commands.reportbug.handle, "Report a bug to the developer.", True),
]

async def handle(message, client):
    user = message.author
    await user.send("🚀 **Welcome to the Quickstart Tutorial!** 🚀\nI will guide you through the essential commands step by step.")
    executed_commands = set()
    
    for command, description, optional in TUTORIAL_STEPS:
        await user.send(f"**{command.__name__.replace('handle', '').title()}**: {description}")
        
        if optional:
            await user.send("Do you want to run this command? (yes/no)")
            try:
                response = await client.wait_for("message", check=lambda m: m.author == user and m.channel.type == discord.ChannelType.private, timeout=30)
                if response.content.lower() != "yes":
                    await user.send("Skipping this step.")
                    continue
            except asyncio.TimeoutError:
                await user.send("Skipping due to no response.")
                continue
        
        executed_commands.add(command.__name__)
        await command(message, client)
        await asyncio.sleep(2)  # Delay to avoid overwhelming the user
    
    await user.send("🎉 **Quickstart Tutorial Complete!** 🎉\nYou are now ready to use the bot.")
