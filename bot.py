import discord
from discord.ext import commands
import logging
import os
import asyncio
from health_monitor import health_monitor

# Set up intents - including privileged intents for spam detection and member events
intents = discord.Intents.default()
# Enable necessary intents
intents.guilds = True             # For server events
intents.messages = True           # For message events
intents.message_content = True    # For spam detection (privileged intent)
intents.members = True            # For member join/leave events (privileged intent)

# Initialize bot with both slash commands and a normal prefix
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Bot event handlers
@bot.event
async def on_ready():
    """Event triggered when the bot is ready and connected to Discord."""
    if bot.user:
        logging.info(f"Bot is ready! Logged in as {bot.user} (ID: {bot.user.id})")
        logging.info(f"Connected to {len(bot.guilds)} guilds")
    else:
        logging.error("Bot user is None after ready event")
    
    # Update health monitor
    health_monitor.update_heartbeat()
    health_monitor.reset_error_count()
    
    # Set bot reference for Flask dashboard
    try:
        from app import set_discord_bot
        set_discord_bot(bot)
        logging.info("Bot reference set for web dashboard")
    except Exception as e:
        logging.warning(f"Could not set bot reference for dashboard: {e}")
        health_monitor.log_error(f"Dashboard setup error: {e}")
    
    # Set bot activity
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.playing, 
        name="Entrain de supplier MrPolochon de lui verser un salaire..."
    ))
    
    # Load cogs
    await load_extensions()
    
    # Sync slash commands
    logging.info("Syncing slash commands...")
    await bot.tree.sync()
    logging.info("Slash commands synced!")
    
@bot.command(name="ping")
async def ping(ctx):
    """Simple command to test if the bot is responding."""
    await ctx.send("Pong! Bot is working. Try using slash commands like `/raid status`")

@bot.tree.command(name="ping", description="Test if the bot is responding")
async def ping_slash(interaction: discord.Interaction):
    """Slash command to test if the bot is responding."""
    import time
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(
        f"🏓 Pong! Bot is online and responding.\n"
        f"📡 Latency: {latency}ms\n"
        f"🤖 All systems operational!"
    )

@bot.event
async def on_message(message):
    """Handle message events."""
    # Don't respond to our own messages
    if message.author == bot.user:
        return
        
    # Log mentions of the bot
    if bot.user and bot.user.mentioned_in(message):
        await message.channel.send("Hello! I'm a raid protection bot. Try using slash commands like `/raid status` or use `!ping` to test if I'm working.")
    
    # Process commands
    await bot.process_commands(message)

@bot.event
async def on_guild_join(guild):
    """Event triggered when the bot joins a new guild."""
    logging.info(f"Bot joined a new guild: {guild.name} (ID: {guild.id})")
    
    # Find a suitable channel to send welcome message
    target_channel = None
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            target_channel = channel
            break
            
    if target_channel:
        embed = discord.Embed(
            title="Raid Protection Bot",
            description="Thanks for adding me to your server! I can help protect against raids.",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Commands", 
            value="`/raid on` - Activate raid mode\n"
                  "`/raid off` - Deactivate raid mode\n"
                  "`/raid status` - Check raid mode status\n"
                  "`/raid setup` - Configure log and announcement channels", 
            inline=False
        )
        embed.add_field(
            name="Permissions", 
            value="Make sure I have the `Manage Channels` permission to function correctly.", 
            inline=False
        )
        
        await target_channel.send(embed=embed)

async def load_extensions():
    """Load all cogs for the bot."""
    try:
        await bot.load_extension('cogs.raid_mode')
        logging.info("Loaded raid_mode cog")
    except Exception as e:
        logging.error(f"Failed to load extension: {e}")
    
    try:
        await bot.load_extension('cogs.warning_system')
        logging.info("Loaded warning_system cog")
    except Exception as e:
        logging.error(f"Failed to load warning system extension: {e}")
    
    try:
        await bot.load_extension('cogs.language_config')
        logging.info("Loaded language_config cog")
    except Exception as e:
        logging.error(f"Failed to load language config extension: {e}")
    
    try:
        await bot.load_extension('cogs.audit_logger')
        logging.info("Loaded audit_logger cog")
    except Exception as e:
        logging.error(f"Failed to load audit logger extension: {e}")
    
    try:
        await bot.load_extension('cogs.continuous_spam_monitor')
        logging.info("Loaded continuous_spam_monitor cog - 24/7 spam detection active")
    except Exception as e:
        logging.error(f"Failed to load 24/7 spam monitor extension: {e}")
    
    try:
        await bot.load_extension('cogs.system_test_new')
        logging.info("Loaded system_test_new cog - /testsystem command with dropdown menu available")
    except Exception as e:
        logging.error(f"Failed to load system test extension: {e}")
    
    try:
        await bot.load_extension('cogs.chat_memory')
        logging.info("Loaded chat_memory cog - AI memory system with persistent learning active")
    except Exception as e:
        logging.error(f"Failed to load chat memory extension: {e}")
    
    try:
        await bot.load_extension('cogs.help_system')
        logging.info("Loaded help_system cog - interactive /help command available")
    except Exception as e:
        logging.error(f"Failed to load help system extension: {e}")
    
    try:
        await bot.load_extension('cogs.setup_system')
        logging.info("Loaded setup_system cog - interactive /setup command available")
    except Exception as e:
        logging.error(f"Failed to load setup system extension: {e}")
    
    try:
        await bot.load_extension('cogs.welcome_system')
        logging.info("Loaded welcome_system cog - custom welcome/goodbye messages with image generation")
    except Exception as e:
        logging.error(f"Failed to load welcome system extension: {e}")
    
    try:
        await bot.load_extension('cogs.ai_chat')
        logging.info("Loaded ai_chat cog - PopoCorps AI personality system with free AI responses")
    except Exception as e:
        logging.error(f"Failed to load AI chat extension: {e}")
    

