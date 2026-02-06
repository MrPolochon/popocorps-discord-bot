#!/usr/bin/env python3
"""
Test script to simulate member join/leave events for welcome system debugging
"""

import asyncio
import discord
from discord.ext import commands
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    """Test the welcome system by simulating events"""
    logger.info(f"Test bot ready! Logged in as {bot.user}")
    
    # Get a test guild
    guild = bot.get_guild(1202135435564810350)  # Your test server
    if not guild:
        logger.error("Test guild not found!")
        return
    
    logger.info(f"Found test guild: {guild.name}")
    
    # Test if welcome system cog is loaded
    welcome_cog = bot.get_cog('WelcomeSystem')
    if not welcome_cog:
        logger.error("WelcomeSystem cog not found!")
        return
    
    logger.info("WelcomeSystem cog found!")
    
    # Get the bot member (simulate it joining)
    bot_member = guild.get_member(bot.user.id)
    if bot_member:
        logger.info(f"Simulating member join for: {bot_member.name}")
        # Simulate member join event
        await welcome_cog.on_member_join(bot_member)
    
    await bot.close()

async def main():
    """Main test function"""
    try:
        # Load welcome system cog
        await bot.load_extension('cogs.welcome_system')
        logger.info("Loaded welcome_system cog")
        
        # Start the bot
        token = os.environ.get('DISCORD_TOKEN')
        if not token:
            logger.error("DISCORD_TOKEN not found!")
            return
        
        await bot.start(token)
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(main())