bot_name = None

def find_bot_name(client):
    global bot_name
    bot_name = str(client.user)
    # return bot_name