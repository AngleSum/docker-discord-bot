# docker-discord-bot
<p>A simple Discord bot script that manages a gcloud compute instance (vm)</p>
<p>Mainly used for saving running costs for a powerful compute instance using a less powerful "controller" compute instance</p>
<p>Was previously used to host a Minecraft server, so some leftover code may not apply</p>

## Requirements

  1. Set up a Compute instance for running the docker container
  2. Set up a startup script for that instance (Optional but recommended)
  3. Set up a "controller" Compute instance for running the Discord bot and controlling the main server
  4. Grant permissions (Start, shutdown other compute instance etc...) to the "controller" in Google Cloud Platform IAM
  5. Set up a bot on discord (remember the token) and add the bot to your Discord server
  6. Fill in the variables in discord-bot.py
<br><sub>If you are hosting a service, remember to set up the firewall rules in Google Cloud Platform</sub>

## Commands

### /start_server

Starts the compute instance via gcloud, a startup script for the instance is recommended  
<sub>Note: This only starts the compute instance as it would be difficult to determine whether the machine has completely started, then run <code>docker-compose up -d</code>

### /stop_server

Runs <code>docker-compose down</code> via gcloud ssh, then shuts down the compute instance via gcloud.

### /status

Returns the status of the server  
Outputs:  
- The server is **running**  
- The server is **stopped**

### Idle shutdown (<code>monitor_server()</code>, used for Minecraft server)
This was leftover code that was used to automatically shut down the server after detecting no players for x minutes, can be configured.  
If used for other games, please change the parse player number logic to be able to correctly get the number of players.
