import config
import discord  # type: ignore
import sqlite3
from config import SUPPORTED_AIRPORTS  # Import supported airports from config.py

# Command metadata
description = "Edit an existing airport registration."
long_description = "Edit your preferences for one of your registered airports. If invalid input, process cancels. [ICAO] is optional argument which can help you skip the first step."
usage = f"{config.PREFIX}edit [ICAO]"
quickstart_optional = True

async def handle(message, client):
    user_id = message.author.id
    conn = sqlite3.connect("vatsim_bot.db")
    cursor = conn.cursor()

    # Fetch user's registered airports
    cursor.execute("SELECT icao FROM user_preferences WHERE user_id = ?", (user_id,))
    user_airports = [row[0] for row in cursor.fetchall()]
    
    if not user_airports:
        await message.channel.send("❌ **Edit process cancelled due to: You have no registered airports to edit.**")
        conn.close()
        return

    # Extract ICAO from command arguments
    command_parts = message.content.split()
    if len(command_parts) > 1:
        icao = command_parts[1].strip().upper()
        if icao not in user_airports:
            await message.channel.send("❌ **Edit process cancelled due to: Invalid ICAO. Please provide an airport from your registered list.**")
            conn.close()
            return
    else:
        await message.channel.send(f"🛫 **Your registered airports:** {', '.join(user_airports)}\n✍️ Enter the ICAO code of the airport you want to edit:")
        def check(m): return m.author == message.author and m.channel == message.channel
        icao_response = await client.wait_for("message", check=check)
        icao = icao_response.content.strip().upper()

        if icao == "CANCEL":
            await message.channel.send("🚫 **Edit process cancelled.**")
            conn.close()
            return

        if icao not in user_airports:
            await message.channel.send("❌ **Edit process cancelled due to: Invalid ICAO. Please enter an airport from your registered list next time.**")
            conn.close()
            return

    # Fields to edit
    fields = {
        "1": "primary_threshold",
        "2": "staff_up_threshold",
        "3": "cooldown",
        "4": "alert_preference",
        "5": "support_threshold"
    }

    await message.channel.send(
        "**📋 What do you want to edit?**\n"
        "1️⃣ Primary Threshold\n"
        "2️⃣ Staff-Up Threshold\n"
        "3️⃣ Cooldown\n"
        "4️⃣ Alert Preference\n"
        "5️⃣ Support Threshold\n"
        "✍️ **Type the corresponding number:**"
    )

    def check(m): return m.author == message.author and m.channel == message.channel
    field_response = await client.wait_for("message", check=check)
    field_choice = field_response.content.strip().upper()

    if field_choice == "CANCEL":
        await message.channel.send("🚫 **Edit process cancelled.**")
        conn.close()
        return

    if field_choice not in fields:
        await message.channel.send("❌ **Edit process cancelled due to: Invalid choice. Please enter a valid number (1-5) next time.**")
        conn.close()
        return

    field_to_edit = fields[field_choice]
    await message.channel.send(f"✍️ Enter the **new value** for **{field_to_edit.replace('_', ' ').title()}**:")

    value_response = await client.wait_for("message", check=check)
    new_value = value_response.content.strip().upper()

    if new_value == "CANCEL":
        await message.channel.send("🚫 **Edit process cancelled.**")
        conn.close()
        return

    # Validate numeric fields
    if field_to_edit in ["primary_threshold", "staff_up_threshold", "cooldown", "support_threshold"]:
        try:
            new_value = int(new_value)
            if new_value < 0:
                raise ValueError
        except ValueError:
            await message.channel.send("❌ **Edit process cancelled due to: Invalid input. Please enter a valid positive number next time.**")
            conn.close()
            return

    # Validate alert preference field
    if field_to_edit == "alert_preference" and new_value.lower() not in ["channel", "dm"]:
        await message.channel.send("❌ **Edit process cancelled due to: Invalid choice. Type either 'channel' or 'dm' next time.**")
        conn.close()
        return

    # Validate that staff-up threshold is not lower than primary threshold
    if field_to_edit == "staff_up_threshold":
        cursor.execute("SELECT primary_threshold FROM user_preferences WHERE user_id = ? AND icao = ?", (user_id, icao))
        primary_threshold = cursor.fetchone()[0]
        if new_value < primary_threshold:
            await message.channel.send("⚠️ **Staff-Up Threshold cannot be lower than Primary Threshold. Please enter a valid value next time. Edit process now cancelled.**")
            conn.close()
            return

    # Update database
    cursor.execute(f"UPDATE user_preferences SET {field_to_edit} = ? WHERE user_id = ? AND icao = ?", (new_value, user_id, icao))
    conn.commit()
    conn.close()

    await message.channel.send(f"✅ **Successfully updated `{field_to_edit.replace('_', ' ').title()}` for `{icao}`.**")
