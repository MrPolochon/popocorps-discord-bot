import json
import os
import logging
from datetime import datetime

from models import GuildConfig, get_db_session, create_tables, DATABASE_URL

logger = logging.getLogger(__name__)


class GuildSettings:
    """Parametres par serveur — persistes en PostgreSQL (Railway) ou fichiers locaux."""

    def __init__(self):
        self.settings_dir = "guild_settings"
        self.settings = {}
        self._use_db = not DATABASE_URL.startswith("sqlite")

        if self._use_db:
            create_tables()
        elif not os.path.exists(self.settings_dir):
            os.makedirs(self.settings_dir)

        self._load_all_settings()

    def _load_all_settings(self):
        """Charge tous les parametres depuis la base ou le disque."""
        if self._use_db:
            db = None
            try:
                db = get_db_session()
                rows = db.query(GuildConfig).all()
                for row in rows:
                    self.settings[row.guild_id] = json.loads(row.settings or "{}")
                logger.info("Loaded guild settings from database (%d guilds)", len(rows))
            except Exception as e:
                logger.error("Error loading guild settings from database: %s", e)
            finally:
                if db:
                    db.close()
            return

        try:
            for guild_id in os.listdir(self.settings_dir):
                if guild_id.isdigit():
                    self._load_guild_settings(int(guild_id))
        except Exception as e:
            logger.error("Error loading guild settings: %s", e)

    def _load_guild_settings(self, guild_id):
        """Charge les parametres d'un serveur."""
        if self._use_db:
            db = None
            try:
                db = get_db_session()
                row = db.query(GuildConfig).filter(GuildConfig.guild_id == guild_id).first()
                if row:
                    self.settings[guild_id] = json.loads(row.settings or "{}")
                    logger.info("Loaded settings for guild %s from database", guild_id)
            except Exception as e:
                logger.error("Error loading settings for guild %s: %s", guild_id, e)
            finally:
                if db:
                    db.close()
            return

        try:
            file_path = os.path.join(self.settings_dir, str(guild_id), "settings.json")
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    self.settings[guild_id] = json.load(f)
                    logger.info("Loaded settings for guild %s", guild_id)
        except Exception as e:
            logger.error("Error loading settings for guild %s: %s", guild_id, e)

    def _save_guild_settings(self, guild_id):
        """Sauvegarde les parametres d'un serveur."""
        data = self.settings.get(guild_id, {})
        if self._use_db:
            db = None
            try:
                db = get_db_session()
                row = db.query(GuildConfig).filter(GuildConfig.guild_id == guild_id).first()
                payload = json.dumps(data)
                if row:
                    row.settings = payload
                    row.updated_at = datetime.utcnow()
                else:
                    db.add(GuildConfig(guild_id=guild_id, settings=payload))
                db.commit()
                logger.info("Saved settings for guild %s to database", guild_id)
            except Exception as e:
                if db:
                    db.rollback()
                logger.error("Error saving settings for guild %s: %s", guild_id, e)
            finally:
                if db:
                    db.close()
            return

        try:
            guild_dir = os.path.join(self.settings_dir, str(guild_id))
            if not os.path.exists(guild_dir):
                os.makedirs(guild_dir)
            file_path = os.path.join(guild_dir, "settings.json")
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f)
            logger.info("Saved settings for guild %s", guild_id)
        except Exception as e:
            logger.error("Error saving settings for guild %s: %s", guild_id, e)

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
        logger.info("Updated log channel for guild %s to %s", guild_id, channel_id)

    def reload_guild_settings(self, guild_id):
        """Force reload settings for a guild from storage."""
        self._load_guild_settings(guild_id)
        logger.info("Reloaded settings for guild %s", guild_id)

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
        return bool(guild_settings.get("log_channel") or guild_settings.get("announcement_channel"))

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
            if guild_id in self.settings:
                del self.settings[guild_id]

            if self._use_db:
                db = None
                try:
                    db = get_db_session()
                    row = db.query(GuildConfig).filter(GuildConfig.guild_id == guild_id).first()
                    if row:
                        db.delete(row)
                        db.commit()
                    logger.info("Reset all settings for guild %s in database", guild_id)
                except Exception as e:
                    if db:
                        db.rollback()
                    logger.error("Error resetting settings for guild %s: %s", guild_id, e)
                finally:
                    if db:
                        db.close()
            else:
                guild_dir = os.path.join(self.settings_dir, str(guild_id))
                if os.path.exists(guild_dir):
                    import shutil
                    shutil.rmtree(guild_dir)
                    logger.info("Reset all settings for guild %s", guild_id)

        except Exception as e:
            logger.error("Error resetting settings for guild %s: %s", guild_id, e)


# Instance unique partagee par tout le bot et le dashboard
guild_settings = GuildSettings()
