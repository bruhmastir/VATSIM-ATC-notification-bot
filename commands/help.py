import discord
import os
import importlib
from discord.ui import View, Button

# Command metadata
description = "Show available commands and their usage."
usage = "!help"

class HelpView(View):
    def __init__(self, commands_info, page=0):
        super().__init__()
        self.commands_info = commands_info
        self.page = page
        self.max_per_page = 10
        self.total_pages = (len(commands_info) - 1) // self.max_per_page + 1
        
        if self.total_pages > 1:
            if self.page > 0:
                self.add_item(Button(label="Previous", style=discord.ButtonStyle.primary, custom_id="prev"))
            if self.page < self.total_pages - 1:
                self.add_item(Button(label="Next", style=discord.ButtonStyle.primary, custom_id="next"))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.custom_id == "prev":
            self.page -= 1
        elif interaction.custom_id == "next":
            self.page += 1
        
        await interaction.response.edit_message(embed=self.create_embed(), view=HelpView(self.commands_info, self.page))
        return True
    
    def create_embed(self):
        start = self.page * self.max_per_page
        end = start + self.max_per_page
        embed = discord.Embed(title="Help Menu", description="List of available commands:", color=discord.Color.blue())
        for cmd in self.commands_info[start:end]:
            embed.add_field(name=cmd[0], value=f"{cmd[1]}\n**Usage:** `{cmd[2]}`", inline=False)
        embed.set_footer(text=f"Page {self.page + 1}/{self.total_pages}")
        return embed

async def handle(message, client):
    command_dir = "commands"
    commands_info = []
    
    for filename in os.listdir(command_dir):
        if filename.endswith(".py") and filename != "__init__.py":
            command_name = filename[:-3]
            module = importlib.import_module(f"commands.{command_name}")
            command_desc = getattr(module, "description", "No description available.")
            command_usage = getattr(module, "usage", "No usage info available.")
            commands_info.append((command_name, command_desc, command_usage))
    
    embed = HelpView(commands_info).create_embed()
    await message.channel.send(embed=embed, view=HelpView(commands_info))
