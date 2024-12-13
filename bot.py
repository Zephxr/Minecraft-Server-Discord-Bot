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
        
        # Check if playercount is valid
        try:
            if "running server" in player_count_result.stdout.strip() or "Could not determine player count" in player_count_result.stdout.strip():
                player_count = 0  # No players if the server isn't running properly
            else:
                player_count = max(0, int(player_count_result.stdout.strip()))  # Safely convert to int if valid
        except ValueError:
            player_count = 0  # Fallback if there’s an issue parsing the player count
        
        print(f"Updating message with status:\n{server_status}\nPlayers: {player_count}")
        last_heartbeat = time.time()
        await message.edit(content=f'Minecraft Server Status:\n{server_status}\nPlayers: {player_count}\nIP: {bot_token.ip}\nLast Updated: {time.strftime("%b %d %I:%M %p", time.localtime(last_heartbeat))}')

    except Exception as e:
        print(f"Error fetching server status: {e}")
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

        try:
            if custom_id == 'start_server':
                await interaction.response.send_message('Starting Minecraft server...', ephemeral=True)
                result = subprocess.run(['/etc/init.d/minecraft', 'start'], capture_output=True, text=True, check=True)
                await interaction.edit_original_response(content=f'Success: {result.stdout}')
                
            elif custom_id == 'restart_server':
                await interaction.response.send_message('Restarting Minecraft server...', ephemeral=True)
                result = subprocess.run(['/etc/init.d/minecraft', 'restart'], capture_output=True, text=True, check=True)
                await interaction.edit_original_response(content=f'Success: {result.stdout}')
                
            elif custom_id == 'stop_server':
                await interaction.response.send_message('Stopping Minecraft server...', ephemeral=True)
                result = subprocess.run(['/etc/init.d/minecraft', 'stop'], capture_output=True, text=True, check=True)
                await interaction.edit_original_response(content=f'Success: {result.stdout}')

        except subprocess.CalledProcessError as e:
            await interaction.edit_original_response(content=f'Error: {e.stderr}')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.content.startswith('!') and message.author.id in ADMIN_USER_IDS:
        command = message.content[1:].strip()
        try:
            print(f"Executing command: {command}")
            result = subprocess.run(['/etc/init.d/minecraft', 'command', command], capture_output=True, text=True, check=True)
            await message.channel.send(f'Command executed successfully:\n{result.stdout}')
        except subprocess.CalledProcessError as e:
            await message.channel.send(f'Error executing command:\n{e.stderr}')
    
    await bot.process_commands(message)

@bot.command(name="clear_chat", description="Clears all messages in the channel except the bot's message.")
@commands.has_permissions(manage_messages=True)
async def _clear_chat(ctx):
    if message_id is None:
        await ctx.send("No message data found. Please initialize the bot message first.")
        return

    if ctx.author.id in ADMIN_USER_IDS:
        try:
            # Get all messages in the channel history
            messages = await ctx.channel.history(limit=None).flatten()
        except discord.HTTPException as e:
            await ctx.send(f"Error fetching messages: {e}")
            return

        # Filter out the bot's message with buttons and delete the rest
        messages_to_delete = [msg for msg in messages if msg.id != message_id]
        deleted = await ctx.channel.purge(limit=len(messages_to_delete), check=lambda m: m in messages_to_delete)
        await ctx.send(f"Deleted {len(deleted)} messages.")
    else:
        await ctx.send("You do not have permission to use this command.")

bot.run(bot_token.bot_token)
