import discord  # type: ignore
import sqlite3
from config import SUPPORTED_AIRPORTS, PREFIX  # Import supported airports and prefix from config.py

# Command metadata
description = "Set your current training status towards a new ATC rating or tier."
usage = f"`{PREFIX}settraining [rating] [tier] [airport]`"
quickstart_optional = False
prerequisite = f"setrating"

VALID_RATINGS = {"S1", "S2", "S3", "C1"}
VALID_TIERS = {"T1": "Tier 1", "U": "Unrestricted"}  # Short forms mapped to full name

async def handle(message, client):
    user_id = message.author.id
    conn = sqlite3.connect("vatsim_bot.db")
    cursor = conn.cursor()

    # Parse arguments
    command_parts = message.content.split()
    rating, tier, airport = None, None, None

    if len(command_parts) == 4:  # Full argument usage
        rating = command_parts[1].strip().upper()
        tier = command_parts[2].strip().upper()
        airport = command_parts[3].strip().upper()

    # Interactive mode if args are missing/invalid
    def check(m): return m.author == message.author and m.channel == message.channel

    # Step 1: Rating
    while rating not in VALID_RATINGS:
        await message.channel.send("🎖️ **Enter the rating you're training towards (S1, S2, S3, C1):**")
        rating_response = await client.wait_for("message", check=check)
        rating = rating_response.content.strip().upper()
        if rating == "CANCEL":
            await message.channel.send("🚫 **Training setup cancelled.**")
            conn.close()
            return

    # Step 2: Tier
    while tier not in VALID_TIERS:
        await message.channel.send("📊 **Enter your training tier (T1 for Tier 1, U for Unrestricted):**")
        tier_response = await client.wait_for("message", check=check)
        tier = tier_response.content.strip().upper()
        if tier == "CANCEL":
            await message.channel.send("🚫 **Training setup cancelled.**")
            conn.close()
            return

    # Step 3: Airport (only needed for Unrestricted)
    if tier == "T1":
        airport = "OMDB"  # Auto-set for Tier 1
    while tier == "U" and (airport not in SUPPORTED_AIRPORTS):
        await message.channel.send("🛫 **Enter the airport where you are training:**")
        airport_response = await client.wait_for("message", check=check)
        airport = airport_response.content.strip().upper()
        if airport == "CANCEL":
            await message.channel.send("🚫 **Training setup cancelled.**")
            conn.close()
            return

    # ✅ Store training status in the database
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_training (
            user_id INTEGER PRIMARY KEY,
            training_rating TEXT,
            training_tier TEXT,
            training_airport TEXT
        )
    """)
    cursor.execute("REPLACE INTO user_training (user_id, training_rating, training_tier, training_airport) VALUES (?, ?, ?, ?)",
                   (user_id, rating, VALID_TIERS[tier], airport))
    conn.commit()
    conn.close()

    await message.channel.send(f"✅ **Training set:** You are training for **{rating}** at **{airport}** under **{VALID_TIERS[tier]}**.")
