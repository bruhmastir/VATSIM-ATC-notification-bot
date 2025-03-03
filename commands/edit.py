import discord
import sqlite3
from config import SUPPORTED_AIRPORTS  # Import supported airports from config.py

# Command metadata
description = "Edit an existing airport registration."
usage = "!edit"

async def handle(message, client):
    user_id = message.author.id
    conn = sqlite3.connect("vatsim_bot.db")
    cursor = conn.cursor()
    
    # Fetch user's registered airports
    cursor.execute("SELECT icao FROM user_preferences WHERE user_id = ?", (user_id,))
    user_airports = [row[0] for row in cursor.fetchall()]
    
    if not user_airports:
        await message.channel.send("You have no registered airports to edit.")
        conn.close()
        return
    
    await message.channel.send(f"Your registered airports: {', '.join(user_airports)}\nEnter the ICAO code of the airport you want to edit:")
    
    def check(m): return m.author == message.author and m.channel == message.channel
    icao_response = await client.wait_for("message", check=check)
    icao = icao_response.content.strip().upper()
    
    if icao == "CANCEL":
        await message.channel.send("Edit process cancelled.")
        conn.close()
        return
    
    if icao not in user_airports:
        await message.channel.send("Invalid ICAO. Please enter an airport from your registered list.")
        conn.close()
        return
    
    fields = {
        "1": "primary_threshold",
        "2": "secondary_threshold",
        "3": "tertiary_threshold",
        "4": "cooldown",
        "5": "alert_preference",
        "6": "support_threshold"
    }
    
    await message.channel.send("What do you want to edit?\n1: Primary Threshold\n2: Secondary Threshold\n3: Tertiary Threshold\n4: Cooldown\n5: Alert Preference\n6: Support Threshold\nType the corresponding number:")
    
    field_response = await client.wait_for("message", check=check)
    field_choice = field_response.content.strip()
    
    if field_choice == "CANCEL":
        await message.channel.send("Edit process cancelled.")
        conn.close()
        return
    
    if field_choice not in fields:
        await message.channel.send("Invalid choice. Please enter a valid number.")
        conn.close()
        return
    
    field_to_edit = fields[field_choice]
    await message.channel.send(f"Enter the new value for {field_to_edit.replace('_', ' ').title()}:")
    
    value_response = await client.wait_for("message", check=check)
    new_value = value_response.content.strip()
    
    if new_value == "CANCEL":
        await message.channel.send("Edit process cancelled.")
        conn.close()
        return
    
    if field_to_edit in ["primary_threshold", "secondary_threshold", "tertiary_threshold", "cooldown", "support_threshold"]:
        try:
            new_value = int(new_value)
            if new_value < 0:
                raise ValueError
        except ValueError:
            await message.channel.send("Invalid input. Please enter a valid positive number.")
            conn.close()
            return
    
    if field_to_edit == "alert_preference" and new_value.lower() not in ["channel", "dm"]:
        await message.channel.send("Invalid choice. Type either 'channel' or 'dm'.")
        conn.close()
        return
    
    cursor.execute(f"UPDATE user_preferences SET {field_to_edit} = ? WHERE user_id = ? AND icao = ?", (new_value, user_id, icao))
    conn.commit()
    conn.close()
    
    await message.channel.send(f"Successfully updated {field_to_edit.replace('_', ' ').title()} for {icao}.")
