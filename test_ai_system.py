#!/usr/bin/env python3
"""
Test script to diagnose AI system issues
"""
import os
import sys
import asyncio
import discord
from discord.ext import commands
import logging

# Add current directory to path
sys.path.append('.')

from utils.guild_settings import GuildSettings
from openai import OpenAI

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def test_ai_system():
    """Test the AI system components"""
    print("🔍 Testing AI System Components...")
    
    # Test 1: Check OpenAI API Key
    print("\n1. Testing OpenAI API Key...")
    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key:
        print(f"✅ OpenAI API Key found (starts with: {openai_key[:8]}...)")
        try:
            client = OpenAI(api_key=openai_key)
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": "Test message"}],
                max_tokens=10
            )
            print("✅ OpenAI API connection successful")
        except Exception as e:
            print(f"❌ OpenAI API error: {e}")
    else:
        print("❌ OpenAI API Key not found")
    
    # Test 2: Check Guild Settings
    print("\n2. Testing Guild Settings...")
    try:
        gs = GuildSettings()
        test_guild_id = 123456789
        
        # Check if AI is enabled
        ai_enabled = gs.get_setting(test_guild_id, 'ai_chat_enabled', False)
        print(f"📊 AI Chat enabled for test guild: {ai_enabled}")
        
        # Enable AI for test
        gs.set_setting(test_guild_id, 'ai_chat_enabled', True)
        ai_enabled_after = gs.get_setting(test_guild_id, 'ai_chat_enabled', False)
        print(f"📊 AI Chat enabled after setting: {ai_enabled_after}")
        
        print("✅ Guild Settings working correctly")
    except Exception as e:
        print(f"❌ Guild Settings error: {e}")
    
    # Test 3: Check Discord Bot Token
    print("\n3. Testing Discord Bot Token...")
    discord_token = os.environ.get("DISCORD_TOKEN")
    if discord_token:
        print(f"✅ Discord Token found (starts with: {discord_token[:8]}...)")
    else:
        print("❌ Discord Token not found")
    
    # Test 4: Test Bot Instance
    print("\n4. Testing Bot Instance...")
    try:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        bot = commands.Bot(command_prefix='!', intents=intents)
        
        @bot.event
        async def on_ready():
            print(f"✅ Bot connected as {bot.user}")
            print(f"📊 Bot ID: {bot.user.id}")
            print(f"📊 Guilds: {len(bot.guilds)}")
            for guild in bot.guilds:
                print(f"   - {guild.name} (ID: {guild.id})")
            
            # Test AI system
            if bot.get_cog('AIChatSystem'):
                print("✅ AIChatSystem cog loaded")
            else:
                print("❌ AIChatSystem cog not found")
            
            await bot.close()
        
        # Try to connect briefly
        if discord_token:
            await bot.start(discord_token)
        else:
            print("❌ Cannot test bot connection - no token")
            
    except Exception as e:
        print(f"❌ Bot connection error: {e}")
    
    print("\n🔍 Diagnosis Complete")

if __name__ == "__main__":
    asyncio.run(test_ai_system())