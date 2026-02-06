import json
import os
import logging
from datetime import datetime

class GuildSettings:
    """Handles guild-specific settings like log channels and announcement channels."""

    def __init__(self):
        self.settings_dir = "guild_settings"
        self.settings = {}

        # Create settings directory if it doesn't exist
        if not os.path.exists(self.settings_dir):
            os.makedirs(self.settings_dir)

        # Load existing settings
        self._load_all_settings()

    def _load_all_settings(self):
        """Load all guild settings from disk."""
        try:
            for guild_id in os.listdir(self.settings_dir):
                if guild_id.isdigit():
                    self._load_guild_settings(int(guild_id))
        except Exception as e:
            logging.error(f"Error loading guild settings: {e}")

    def _load_guild_settings(self, guild_id):
        """Load settings for a specific guild."""
        try:
            file_path = os.path.join(self.settings_dir, str(guild_id), "settings.json")
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    self.settings[guild_id] = json.load(f)
                    logging.info(f"Loaded settings for guild {guild_id}")
        except Exception as e:
            logging.error(f"Error loading settings for guild {guild_id}: {e}")

    def _save_guild_settings(self, guild_id):
        """Save settings for a specific guild."""
        try:
            # Create guild settings directory if it doesn't exist
            guild_dir = os.path.join(self.settings_dir, str(guild_id))
            if not os.path.exists(guild_dir):
                os.makedirs(guild_dir)

            # Save the settings
            file_path = os.path.join(guild_dir, "settings.json")
            with open(file_path, 'w') as f:
                json.dump(self.settings.get(guild_id, {}), f)

            logging.info(f"Saved settings for guild {guild_id}")
        except Exception as e:
            logging.error(f"Error saving settings for guild {guild_id}: {e}")

    def get_log_channel(self, guild_id):
        """Get the log channel ID for a guild."""
        guild_settings = self.settings.get(guild_id, {})
        return guild_settings.get("log_channel")

    def get_announcement_channel(self, guild_id):
        """Get the announcement channel ID for a guild."""
        guild_settings = self.settings.get(guild_id, {})
        return guild_settings.get("announcement_channel")

    def get_admin_role(self, guild_id):
        """Get the configured admin role ID for a guild."""
        guild_settings = self.settings.get(guild_id, {})
        return guild_settings.get("admin_role")

    def set_log_channel(self, guild_id, channel_id):
        """Set the log channel ID for a guild."""
        if guild_id not in self.settings:
            self.settings[guild_id] = {}

        self.settings[guild_id]["log_channel"] = channel_id
        self.settings[guild_id]["last_updated"] = datetime.now().isoformat()
        self._save_guild_settings(guild_id)
        
        # Force reload to ensure immediate update
        self._load_guild_settings(guild_id)
        logging.info(f"Updated log channel for guild {guild_id} to {channel_id}")

    def reload_guild_settings(self, guild_id):
        """Force reload settings for a guild from disk."""
        self._load_guild_settings(guild_id)
        logging.info(f"Reloaded settings for guild {guild_id}")

    def set_announcement_channel(self, guild_id, channel_id):
        """Set the announcement channel ID for a guild."""
        if guild_id not in self.settings:
            self.settings[guild_id] = {}

        self.settings[guild_id]["announcement_channel"] = channel_id
        self.settings[guild_id]["last_updated"] = datetime.now().isoformat()
        self._save_guild_settings(guild_id)

    def set_admin_role(self, guild_id, role_id):
        """Set the admin role ID for a guild."""
        if guild_id not in self.settings:
            self.settings[guild_id] = {}

        self.settings[guild_id]["admin_role"] = role_id
        self.settings[guild_id]["last_updated"] = datetime.now().isoformat()
        self._save_guild_settings(guild_id)

    def get_member_role(self, guild_id):
        """Get the configured member role ID for a guild."""
        guild_settings = self.settings.get(guild_id, {})
        return guild_settings.get("member_role")

    def set_member_role(self, guild_id, role_id):
        """Set the member role ID for a guild."""
        if guild_id not in self.settings:
            self.settings[guild_id] = {}

        self.settings[guild_id]["member_role"] = role_id
        self.settings[guild_id]["last_updated"] = datetime.now().isoformat()
        self._save_guild_settings(guild_id)

    def has_setup_completed(self, guild_id):
        """Check if a guild has completed the setup."""
        guild_settings = self.settings.get(guild_id, {})
        # Guild is considered set up if it has at least a log channel or announcement channel
        return bool(guild_settings.get("log_channel") or guild_settings.get("announcement_channel"))
    
    # Welcome/Goodbye message settings
    def set_welcome_channel(self, guild_id, channel_id):
        """Set the welcome channel for a guild."""
        if guild_id not in self.settings:
            self.settings[guild_id] = {}
        self.settings[guild_id]["welcome_channel"] = channel_id
        self.settings[guild_id]["last_updated"] = datetime.now().isoformat()
        self._save_guild_settings(guild_id)
    
    def get_welcome_channel(self, guild_id):
        """Get the welcome channel for a guild."""
        return self.settings.get(guild_id, {}).get("welcome_channel")
    
    def set_goodbye_channel(self, guild_id, channel_id):
        """Set the goodbye channel for a guild."""
        if guild_id not in self.settings:
            self.settings[guild_id] = {}
        self.settings[guild_id]["goodbye_channel"] = channel_id
        self.settings[guild_id]["last_updated"] = datetime.now().isoformat()
        self._save_guild_settings(guild_id)
    
    def get_goodbye_channel(self, guild_id):
        """Get the goodbye channel for a guild."""
        return self.settings.get(guild_id, {}).get("goodbye_channel")
    
    def set_welcome_message(self, guild_id, message):
        """Set the welcome message template for a guild."""
        if guild_id not in self.settings:
            self.settings[guild_id] = {}
        self.settings[guild_id]["welcome_message"] = message
        self.settings[guild_id]["last_updated"] = datetime.now().isoformat()
        self._save_guild_settings(guild_id)
    
    def get_welcome_message(self, guild_id):
        """Get the welcome message template for a guild."""
        return self.settings.get(guild_id, {}).get("welcome_message", "Welcome to {server_name}, {user_mention}! 🎉")
    
    def set_goodbye_message(self, guild_id, message):
        """Set the goodbye message template for a guild."""
        if guild_id not in self.settings:
            self.settings[guild_id] = {}
        self.settings[guild_id]["goodbye_message"] = message
        self.settings[guild_id]["last_updated"] = datetime.now().isoformat()
        self._save_guild_settings(guild_id)
    
    def get_goodbye_message(self, guild_id):
        """Get the goodbye message template for a guild."""
        return self.settings.get(guild_id, {}).get("goodbye_message", "Goodbye {user_name}! 👋")
    
    def set_welcome_enabled(self, guild_id, enabled):
        """Enable or disable welcome messages for a guild."""
        if guild_id not in self.settings:
            self.settings[guild_id] = {}
        self.settings[guild_id]["welcome_enabled"] = enabled
        self.settings[guild_id]["last_updated"] = datetime.now().isoformat()
        self._save_guild_settings(guild_id)
    
    def is_welcome_enabled(self, guild_id):
        """Check if welcome messages are enabled for a guild."""
        return self.settings.get(guild_id, {}).get("welcome_enabled", False)
    
    def set_goodbye_enabled(self, guild_id, enabled):
        """Enable or disable goodbye messages for a guild."""
        if guild_id not in self.settings:
            self.settings[guild_id] = {}
        self.settings[guild_id]["goodbye_enabled"] = enabled
        self.settings[guild_id]["last_updated"] = datetime.now().isoformat()
        self._save_guild_settings(guild_id)
    
    def is_goodbye_enabled(self, guild_id):
        """Check if goodbye messages are enabled for a guild."""
        return self.settings.get(guild_id, {}).get("goodbye_enabled", False)
    
    # Background and styling settings
    def set_welcome_background(self, guild_id, image_url):
        """Set the welcome background image URL."""
        if guild_id not in self.settings:
            self.settings[guild_id] = {}
        self.settings[guild_id]["welcome_background"] = image_url
        self.settings[guild_id]["last_updated"] = datetime.now().isoformat()
        self._save_guild_settings(guild_id)
    
    def get_welcome_background(self, guild_id):
        """Get the welcome background image URL."""
        return self.settings.get(guild_id, {}).get("welcome_background")
    
    def set_goodbye_background(self, guild_id, image_url):
        """Set the goodbye background image URL."""
        if guild_id not in self.settings:
            self.settings[guild_id] = {}
        self.settings[guild_id]["goodbye_background"] = image_url
        self.settings[guild_id]["last_updated"] = datetime.now().isoformat()
        self._save_guild_settings(guild_id)
    
    def get_goodbye_background(self, guild_id):
        """Get the goodbye background image URL."""
        return self.settings.get(guild_id, {}).get("goodbye_background")
    
    def set_welcome_font(self, guild_id, font_name):
        """Set the welcome message font."""
        if guild_id not in self.settings:
            self.settings[guild_id] = {}
        self.settings[guild_id]["welcome_font"] = font_name
        self.settings[guild_id]["last_updated"] = datetime.now().isoformat()
        self._save_guild_settings(guild_id)
    
    def get_welcome_font(self, guild_id):
        """Get the welcome message font."""
        return self.settings.get(guild_id, {}).get("welcome_font", "Arial")
    
    def set_goodbye_font(self, guild_id, font_name):
        """Set the goodbye message font."""
        if guild_id not in self.settings:
            self.settings[guild_id] = {}
        self.settings[guild_id]["goodbye_font"] = font_name
        self.settings[guild_id]["last_updated"] = datetime.now().isoformat()
        self._save_guild_settings(guild_id)
    
    def get_goodbye_font(self, guild_id):
        """Get the goodbye message font."""
        return self.settings.get(guild_id, {}).get("goodbye_font", "Arial")
    
    def get_setting(self, guild_id, setting_name, default=None):
        """Get a specific setting value for a guild."""
        guild_settings = self.settings.get(guild_id, {})
        return guild_settings.get(setting_name, default)
    
    def set_setting(self, guild_id, setting_name, value):
        """Set a specific setting value for a guild."""
        if guild_id not in self.settings:
            self.settings[guild_id] = {}
        
        self.settings[guild_id][setting_name] = value
        self.settings[guild_id]["last_updated"] = datetime.now().isoformat()
        self._save_guild_settings(guild_id)
    
    def get_all_settings(self, guild_id):
        """Get all settings for a guild."""
        return self.settings.get(guild_id, {})
    
    def reset_guild_settings(self, guild_id):
        """Reset all settings for a guild."""
        try:
            # Remove from memory
            if guild_id in self.settings:
                del self.settings[guild_id]
            
            # Remove files from disk
            guild_dir = os.path.join(self.settings_dir, str(guild_id))
            if os.path.exists(guild_dir):
                import shutil
                shutil.rmtree(guild_dir)
                logging.info(f"Reset all settings for guild {guild_id}")
            
        except Exception as e:
            logging.error(f"Error resetting settings for guild {guild_id}: {e}")

# Create a singleton instance
guild_settings = GuildSettings()