import logging
import os
from datetime import datetime
import json
from utils.guild_settings import guild_settings

def log_raid_event(guild, user, action):
    """
    Log raid mode activity to a file.
    
    Args:
        guild: The Discord guild object
        user: The user who triggered the action
        action: The action performed (enabled/disabled)
    """
    try:
        # Create log directory if it doesn't exist
        log_dir = os.path.join("raid_data", str(guild.id), "logs")
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        # Get current timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Use display_name if available, otherwise fall back to name
        user_name = getattr(user, 'display_name', user.name)
        
        # Create log entry
        log_entry = {
            "timestamp": timestamp,
            "action": action,
            "user_id": user.id,
            "user_name": user_name,
            "guild_id": guild.id,
            "guild_name": guild.name
        }
        
        # Append to log file
        log_file = os.path.join(log_dir, f"raid_log_{datetime.now().strftime('%Y-%m')}.jsonl")
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + "\n")
            
        # Also log to console
        logging.info(f"Raid mode {action} by {user_name} in {guild.name}")
        
    except Exception as e:
        logging.error(f"Error logging raid event: {e}")
