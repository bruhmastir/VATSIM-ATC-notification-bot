import sqlite3
import discord  # type: ignore

async def handle(message, client):
    user_id = message.author.id
    conn = sqlite3.connect("vatsim_bot.db")
    cursor = conn.cursor()

    # Delete entries from all relevant tables
    cursor.execute("DELETE FROM user_preferences WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM user_quiet_hours WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM user_ratings WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM user_opt_outs WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM user_observe_hours WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM user_cooldowns WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM user_training WHERE user_id = ?", (user_id,))

    conn.commit()
    conn.close()

    await message.channel.send("All your data has been reset.")