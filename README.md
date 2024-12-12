# Requirements
- Minecraft-Init by Athenus installed managing your minecraft server
  - https://github.com/Ahtenus/minecraft-init/tree/master
- Python3
- Linux Server (WSL2 works)
- A discord bot (I won't go into detail about this, you can find tutorials online)

# Set-Up

1. Clone this repo
2. python3 -m venv venv
3. source venv/bin/activate
4. pip install discord.py
5. touch bot_token.py
6. Inside bot_token.py
   - Should be formatted like this:
   - ```
     bot_token = r"<BOT TOKEN HERE>"
     channel_id = <CHANNEL ID HERE>
     ip = "<IP HERE>"
     ```
7. python3 bot.py 
