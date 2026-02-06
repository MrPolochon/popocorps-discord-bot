#!/bin/bash

# Production startup script for PopoCorps Bot
# Ensures all directories exist and starts the application

echo "Starting PopoCorps Bot..."

# Create necessary directories
mkdir -p raid_data
mkdir -p guild_settings
mkdir -p temp_images
mkdir -p fonts

# Set permissions
chmod +x run.py

# Start the application
echo "Launching Discord bot with web dashboard..."
python run.py