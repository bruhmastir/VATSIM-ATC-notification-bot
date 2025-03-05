import discord  # type: ignore
import os
import importlib
from discord.ui import View, Button  # type: ignore
from config import PREFIX  # Import bot prefix from config.py

# Command metadata
description = "Show available commands and their usage."
usage = "!help"

class HelpView(View):
    def __init__(self, commands_info, page=0):
        super().__init__()
        self.commands_info = commands_info  # ✅ Now correctly formatted as a list of (name, desc, usage)
        self.page = page
        self.max_per_page = 4
        self.total_pages = (len(commands_info) - 1) // self.max_per_page + 1
        self.update_buttons()

    def update_buttons(self):
        """Dynamically update buttons based on the current page."""
        self.clear_items()
        if self.page > 0:
            self.add_item(Button(label="⏮️ First", style=discord.ButtonStyle.primary, custom_id="first"))
            self.add_item(Button(label="⬅️ Previous", style=discord.ButtonStyle.primary, custom_id="prev"))
        if self.page < self.total_pages - 1:
            self.add_item(Button(label="Next ➡️", style=discord.ButtonStyle.primary, custom_id="next"))
            self.add_item(Button(label="Last ⏭️", style=discord.ButtonStyle.primary, custom_id="last"))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Handles button interactions."""
        button_id = interaction.data["custom_id"]

        if button_id == "next":
            self.page += 1
        elif button_id == "prev":
            self.page -= 1
        elif button_id == "first":
            self.page = 0
        elif button_id == "last":
            self.page = self.total_pages - 1

        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)
        return True

    def create_embed(self):
        """Creates the embed for the help menu."""
        start = self.page * self.max_per_page
        end = start + self.max_per_page
        embed = discord.Embed(title="📜 Help Menu", description="List of available commands:", color=discord.Color.blue())

        for cmd_name, cmd_desc, cmd_usage in self.commands_info[start:end]:  # ✅ Correct unpacking
            embed.add_field(name=f"🛠️ {cmd_name}", value=f"📖 {cmd_desc}\n**Usage:** `{cmd_usage}`", inline=False)

        embed.set_footer(text=f"Page {self.page + 1}/{self.total_pages}")
        return embed

async def handle(message, client):
    """Handles the !help command with optional arguments for specific command details."""
    command_dir = "commands"
    commands_info = []

    for filename in os.listdir(command_dir):
        if filename.endswith(".py") and filename != "__init__.py":
            command_name = filename[:-3]
            module = importlib.import_module(f"commands.{command_name}")
            command_desc = getattr(module, "description", "No description available.")
            command_usage = getattr(module, "usage", f"{PREFIX}{command_name}")
            long_description = getattr(module, "long_description", command_desc)
            commands_info.append((command_name, command_desc, command_usage, long_description))  # ✅ Flattened tuple format

    args = message.content.split()

    if len(args) == 1:
        # ✅ Show the full help menu
        command_list = [(cmd[0], cmd[1], cmd[2]) for cmd in commands_info]  # ✅ Extract only relevant details
        embed = HelpView(command_list).create_embed()
        await message.channel.send(embed=embed, view=HelpView(command_list))
        return

    elif len(args) == 2:
        requested_command = args[1].lower()

        for cmd_name, cmd_desc, cmd_usage, cmd_long_desc in commands_info:
            if requested_command == cmd_name:
                embed = discord.Embed(title=f"🛠️ Help: {cmd_name}", color=discord.Color.green())
                embed.add_field(name="📖 Description", value=cmd_desc, inline=False)
                embed.add_field(name="📜 Detailed Info", value=cmd_long_desc, inline=False)
                embed.add_field(name="⚙️ Usage", value=f"```{cmd_usage}```", inline=False)
                await message.channel.send(embed=embed)
                return

        # ✅ Command not found - show error + redirect to the main help page
        embed = discord.Embed(title="❌ Command Not Found!", description=f"Use `{PREFIX}help` to see available commands.", color=discord.Color.red())
        await message.channel.send(embed=embed)

        command_list = [(cmd[0], cmd[1], cmd[2]) for cmd in commands_info]  # ✅ Extract only relevant details
        embed = HelpView(command_list).create_embed()
        await message.channel.send(embed=embed, view=HelpView(command_list))
