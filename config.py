import os

# Bot configuration
DEFAULT_PREFIX = "!"
COMMAND_PREFIX = os.getenv("COMMAND_PREFIX", DEFAULT_PREFIX)

# Environment configuration
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Bot constants
BOT_DESCRIPTION = "A Discord bot with raid protection features"
BOT_VERSION = "1.0.0"

# Feature configuration
RAID_MODE_COOLDOWN = 5  # Cooldown in seconds between raid mode commands

# Default activity status
DEFAULT_ACTIVITY = "for raids | !raidmode help"
