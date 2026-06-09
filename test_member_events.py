#!/usr/bin/env python3
"""
Test to verify member events are working
"""

import discord
from discord.ext import commands
import os
import logging
import asyncio

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set up intents - including members intent
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='!test_', intents=intents)

@bot.event
async def on_ready():
    """Test if bot can see member events"""
    logger.info(f"Test bot ready! Logged in as {bot.user}")
    logger.info(f"Bot has members intent: {bot.intents.members}")
    
    # Get the test guild
    guild = bot.get_guild(1202135435564810350)
    if guild:
        logger.info(f"Found guild: {guild.name} with {guild.member_count} members")
        logger.info(f"Bot member count in guild: {len(guild.members)}")
    else:
        logger.error("Test guild not found!")
    
    await bot.close()

@bot.event
async def on_member_join(member):
    """Test member join detection"""
    logger.info(f"TEST: Member joined - {member.name} ({member.id})")

@bot.event
async def on_member_remove(member):
    """Test member leave detection"""
    logger.info(f"TEST: Member left - {member.name} ({member.id})")

async def main():
    """Run the test"""
    try:
        token = os.environ.get('DISCORD_TOKEN')
        if not token:
            logger.error("DISCORD_TOKEN not found!")
            return
        
        await bot.start(token)
        
    except Exception as e:
        logger.error(f"Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())