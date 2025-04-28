import discord
from discord.ext import commands, tasks
from discord import app_commands
import subprocess
import asyncio

TOKEN = "<INSERT TOKEN HERE>"
GUILD_ID = <SERVER ID HERE>
docker_compose_path = "<PATH TO docker-compose.yml>"
vm_name = "<VM NAME>"
zone = "<ZONE>"
container_name = ""
player_num_command = "<COMMAND FOR GETTING PLAYER NUMBER>" # (Used if monitor_server is used)
timeout_minutes = 5 # Number of minutes of 0 players allowed before shutting down server(Used if monitor_server() is used)
interval = 1 # Interval of checking player number (Used if monitor_server() is used)
CHANNEL_ID = <CHANNEL ID HERE> # For printing results (Used if monitor_server() is used)

zero_player_minutes = 0

intents = discord.Intents.default()
intents.message_content = True  # required to read messages

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    await bot.tree.sync()
    # monitor_server.start()

# Pings the bot for testing
@bot.tree.command(name="ping", description="ping")
async def greet(interaction: discord.Interaction):
    await interaction.response.send_message(f"pong")

# Slash command for stopping the container then the compute instance
@bot.tree.command(name="stop_server", description="Stops the container and shuts down the server")
async def stop_server(interaction: discord.Interaction):
    try:    
        # SSH into the gcloud vm and stop the docker-compose
        result_docker = subprocess.run(
            [
                "gcloud", "compute", "ssh", vm_name,
                "--zone", zone,
                "--command", f"docker-compose -f {docker_compose_path} down"
            ],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        
        # Check if the container is stopped
        if result_docker.returncode == 0:
            await interaction.response.send_message("Container stopped!")
        else:
            await interaction.response.send_message("Error: {result_docker.stderr.decode()}")
        
        # Shut down the server
        result_vm = subprocess.run(
            [
                "gcloud", "compute", "instances", "stop", vm_name,
                "--zone", zone
            ],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        
        if result_vm.returncode == 0:
            await interaction.response.send_message(f"Server stopped!")
        else:
            await interaction.response.send_message(f"Error: {result_vm.stderr.decode()}")
    
    except Exception as e:
        await interaction.response.send_message(f"Error: {str(e)}")

# Slash command that starts the compute instance only (Start script to server is preferred)
@bot.tree.command(name="start_server", description="Starts the server")
async def start_server(interaction: discord.Interaction):
    await interaction.response.send_message("Starting...")

    # Start the server
    start_vm = subprocess.run(
        ["gcloud", "compute", "instances", "start", vm_name, "--zone", zone],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # Check if the instance is started
    if start_vm.returncode == 0:
        # Get the external IP address after the VM starts
        get_ip_command = [
            "gcloud", "compute", "instances", "describe", vm_name, "--zone", zone, 
            "--format", "get(networkInterfaces[0].accessConfigs[0].natIP)"
        ] 
        result = subprocess.run(get_ip_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if result.returncode == 0:
            external_ip = result.stdout.decode().strip() # Strip to remove extra spaces/newlines
            await interaction.followup.send(f"Success! IP: {external_ip}")
        else:
            error_message = result.stderr.decode()
            await interaction.followup.send(f"Error.\n```{error_message}```")
    else:
        error_message = start_vm.stderr.decode()
        await interaction.followup.send(f"Error.\n```{error_message}```")

# Slash command that returns the server status
@bot.tree.command(name="status", description="Check server status")
async def status(interaction: discord.Interaction):

    await interaction.response.send_message("Checking server status...", ephemeral=True)

    # Run command via gcloud SSH
    status_cmd = subprocess.run(
        ["gcloud", "compute", "instances", "describe", vm_name, "--zone", zone, "--format", "get(status)"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # If command successful
    if status_cmd.returncode == 0:
        # Get the VM status
        vm_status = status_cmd.stdout.decode().strip()

        if vm_status == "RUNNING":
            await interaction.followup.send(f"The server is **running**!",ephemeral=True)
        elif vm_status == "TERMINATED":
            await interaction.followup.send(f"The server is **stopped**.",ephemeral=True)
        else:
            await interaction.followup.send(f"IDK: {vm_status}.",ephemeral=True)
    else:
        # Error in running the gcloud command
        error_message = status_cmd.stderr.decode()
        await interaction.followup.send(f"Error.\n```{error_message}```",ephemeral=True)

# Custom script for idle shutdown in a game server, remove if not applicable

@tasks.loop(minutes=interval)
async def monitor_server():
    global zero_player_minutes
    # Get player number
    docker_command = f"sudo docker exec {container_name} rcon-cli {player_num_command}"
    ssh_command = [
        "gcloud", "compute", "ssh", vm_name,
        "--zone", zone,
        "--command", docker_command
    ]

    result = subprocess.run(ssh_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    channel = bot.get_channel(CHANNEL_ID)

    # If command successful
    if result.returncode == 0:
        output = result.stdout.decode().strip()
        try:
            # Parse player number from output
            current_players = int(output.split("of")[0].split()[-1]) # PLEASE EDIT THIS (Current code is for Minecraft, not compatible with other games)
            if current_players == 0:
                zero_player_minutes += interval
                if zero_player_minutes >= timeout_minutes:
                    # Graceful shutdown
                    await channel.send("No players, stopping server.")
                    result_docker = subprocess.run(
                        [
                            "gcloud", "compute", "ssh", vm_name,
                            "--zone", zone,
                            "--command", f"docker-compose -f {docker_compose_path} down"
                        ],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE
                    )
                    if result_docker.returncode == 0:
                        await channel.send("Game server stopped!")
                    else:
                        await channel.send(f"Error: {result_docker.stderr.decode()}")
                    subprocess.run(["gcloud", "compute", "instances", "stop", vm_name, "--zone", zone])
                    zero_player_minutes = 0  # Reset counter after shutdown
            else:
                zero_player_minutes = 0
        except Exception as e:
            await channel.send(f"Error parsing player count.\nRaw output: `{output}`")
             
bot.run(TOKEN)
