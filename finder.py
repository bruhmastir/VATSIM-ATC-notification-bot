import config
import logging
import sqlite3

bot_name = None

def find_bot_name(client):
    global bot_name
    bot_name = str(client.user)
    logging.info(f"Bot name found: {bot_name}")
    # return bot_name

def find_prefix(bot_name):
    if not bot_name:
        logging.error("Bot name not specified. Defaulting to config.PREFIX.")
        return config.PREFIX
    return config.PREFIX if not bot_name.lower().startswith("dev") else config.DEV_PREFIX

def get_training_info(user_id):
    conn = sqlite3.connect("vatsim_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT training_rating, training_airport FROM user_training WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result