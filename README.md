Hi everyone! I started working on this bot back in early March 2025 because not everyone in my vACC agreed on when it was a good idea to use pings to get someone to replace you if you need to go and there was still traffic. 

This bot basically takes your preferences about the number of traffic and alerts you if there is good traffic (according to your own preference) and no ATC, or even more traffic (this is also according to your preferences) but only partial ATC is online.

You can also use a command such as !supportme OMDB TWR for example to get someone on tower and only those who think this is a good amount of traffic will be alerted. Alerts can be sent via DMs or a specific channel in the Discord server in the bot's About me. 

If you are training and want to observe the facility at which you are training, you can use !observe 3.5 to be alerted whenever that facility comes online during the next 3.5 hours. 

There are more commands so use !help to check them all. To use the bot just send it a message or join the development server and use !quickstart in the bot-commands channel.

Please do report any bugs you encounter or suggestions you would like me to implement. 
Also I need a better name so feel free to give me your ideas.
https://discord.com/users/1345800358567612539


This bot is currently designed to support Arabian vACC only. To host a similar one for your own vACC, fork this repository, update the config.py file with your supported airports, fill in the .env.example file and rename it to .env, and run python3 bot.py. you should also replace the files in vatglasses-data with the files relating to your FIRs.