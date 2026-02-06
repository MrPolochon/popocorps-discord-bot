#!/usr/bin/env python3
"""
Simple diagnostic test for welcome system
"""

import sys
sys.path.append('.')

from utils.guild_settings import guild_settings
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_welcome_settings():
    """Test welcome system settings"""
    guild_id = 1202135435564810350  # Test server ID
    
    logger.info(f"Testing welcome settings for guild {guild_id}")
    
    # Check if welcome is enabled
    welcome_enabled = guild_settings.is_welcome_enabled(guild_id)
    logger.info(f"Welcome enabled: {welcome_enabled}")
    
    # Check welcome channel
    welcome_channel = guild_settings.get_welcome_channel(guild_id)
    logger.info(f"Welcome channel: {welcome_channel}")
    
    # Check welcome message
    welcome_message = guild_settings.get_welcome_message(guild_id)
    logger.info(f"Welcome message: {welcome_message}")
    
    # Check goodbye settings
    goodbye_enabled = guild_settings.is_goodbye_enabled(guild_id)
    logger.info(f"Goodbye enabled: {goodbye_enabled}")
    
    goodbye_channel = guild_settings.get_goodbye_channel(guild_id)
    logger.info(f"Goodbye channel: {goodbye_channel}")
    
    goodbye_message = guild_settings.get_goodbye_message(guild_id)
    logger.info(f"Goodbye message: {goodbye_message}")
    
    # Check if all settings are properly configured
    if welcome_enabled and welcome_channel:
        logger.info("✅ Welcome system is properly configured")
    else:
        logger.warning("❌ Welcome system configuration incomplete")
        
    if goodbye_enabled and goodbye_channel:
        logger.info("✅ Goodbye system is properly configured")
    else:
        logger.warning("❌ Goodbye system configuration incomplete")

if __name__ == "__main__":
    test_welcome_settings()