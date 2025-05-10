import config
import logging

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