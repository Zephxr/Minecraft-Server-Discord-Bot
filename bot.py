import discord
from discord.ext import commands, tasks
import subprocess
import json
import os
import bot_token
import time

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

MESSAGE_DATA_FILE = 'message_data.json'

message_id = None

ADMIN_USER_IDS = bot_token.adminIDs

@tasks.loop(seconds=10)
async def update_server_status():
    global message_id
    print(message_id)
    print("Running server status update loop...")
    if message_id is None:
        print("Message ID is None, skipping update.")
        return

    channel = bot.get_channel(bot_token.channel_id)
    message = await channel.fetch_message(message_id)

    try:
        print("Fetching server status...")
        status_result = subprocess.run(['/etc/init.d/minecraft', 'status'], capture_output=True, text=True, check=True)
        server_status = status_result.stdout.strip()

        if "is running" in server_status:
            server_status = "Server is running!"
        else:
            server_status = "Server is not running."

        print("Fetching player count...")
        player_count_result = subprocess.run(['/etc/init.d/minecraft', 'playercount'], capture_output=True, text=True, check=True)
        player_count = max(0, int(player_count_result.stdout.strip()) - 1)

        print(f"Updating message with status:\n{server_status}\nPlayers: {player_count}")
        last_heartbeat = time.time()
        await message.edit(content=f'Minecraft Server Status:\n{server_status}\nPlayers: {player_count}\nIP: {bot_token.ip}\nLast Updated: {time.strftime("%m-%d %H:%M:%S", time.gmtime(last_heartbeat))}')

    except subprocess.CalledProcessError as e:
        print(f"Error fetching server status: {e.stderr}")
        await message.edit(content="Error fetching server status.")

@bot.event
async def on_ready():
    global message_id
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    channel_id = bot_token.channel_id
    if os.path.exists(MESSAGE_DATA_FILE):
        with open(MESSAGE_DATA_FILE, 'r') as f:
            data = json.load(f)
            channel_id = data['channel_id']
            message_id = data['message_id']

        channel = bot.get_channel(channel_id)
        message = await channel.fetch_message(message_id)
        print(f"Reconnected to message {message_id}.")

    else:
        print("No previous message data found. Sending a new message.")
        
        channel = bot.get_channel(channel_id)
        message = await channel.send('Minecraft Server Control:')

        start_button = discord.ui.Button(label='Start Server', style=discord.ButtonStyle.primary, custom_id='start_server')
        restart_button = discord.ui.Button(label='Restart Server', style=discord.ButtonStyle.secondary, custom_id='restart_server')
        stop_button = discord.ui.Button(label='Stop Server', style=discord.ButtonStyle.danger, custom_id='stop_server')

        view = discord.ui.View()
        view.add_item(start_button)
        view.add_item(restart_button)
        view.add_item(stop_button)

        await message.edit(view=view)

        with open(MESSAGE_DATA_FILE, 'w') as f:
            json.dump({'channel_id': channel.id, 'message_id': message.id}, f)
        print(f"Sent new message with ID {message.id}.")
        message_id = message.id
    
    update_server_status.start()

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component:
        custom_id = interaction.data.get('custom_id')

        # Check if the user is an admin (for restart and stop actions)
        if interaction.user.id not in ADMIN_USER_IDS:
            if custom_id in ['restart_server', 'stop_server']:
                await interaction.response.send_message('You do not have permission to perform this action.', ephemeral=True)
                return

        if custom_id == 'start_server':
            await interaction.response.send_message('Starting Minecraft server...', ephemeral=True)
            try:
                result = subprocess.run(['/etc/init.d/minecraft', 'start'], capture_output=True, text=True, check=True)
                await interaction.channel.send(f'Success: {result.stdout}', ephemeral=True)
            except subprocess.CalledProcessError as e:
                await interaction.channel.send(f'Error starting server: {e.stderr}', ephemeral=True)
        elif custom_id == 'restart_server':
            await interaction.response.send_message('Restarting Minecraft server...', ephemeral=True)
            try:
                result = subprocess.run(['/etc/init.d/minecraft', 'restart'], capture_output=True, text=True, check=True)
                await interaction.channel.send(f'Success: {result.stdout}', ephemeral=True)
            except subprocess.CalledProcessError as e:
                await interaction.channel.send(f'Error restarting server: {e.stderr}', ephemeral=True)
        elif custom_id == 'stop_server':
            await interaction.response.send_message('Stopping Minecraft server...', ephemeral=True)
            try:
                result = subprocess.run(['/etc/init.d/minecraft', 'stop'], capture_output=True, text=True, check=True)
                await interaction.channel.send(f'Success: {result.stdout}', ephemeral=True)
            except subprocess.CalledProcessError as e:
                await interaction.channel.send(f'Error stopping server: {e.stderr}', ephemeral=True)

bot.run(bot_token.bot_token)
