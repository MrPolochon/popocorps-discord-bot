# Combined application entry point
import os
import logging
import asyncio
import threading
import time
from bot import bot
from app import app, set_discord_bot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# Get the token from environment variables
TOKEN = os.getenv('DISCORD_TOKEN')

if not TOKEN:
    logging.error("No Discord token found in environment variables. Please set the DISCORD_TOKEN environment variable.")
    exit(1)

async def run_discord_bot():
    """Run the Discord bot"""
    try:
        # Set the bot reference for the dashboard
        set_discord_bot(bot)
        logging.info("Starting Discord bot...")
        await bot.start(TOKEN)
    except Exception as e:
        logging.error(f"Error running Discord bot: {e}")
        
        # Check for specific error about privileged intents
        if "PrivilegedIntentsRequired" in str(e):
            logging.error("\n********************************************")
            logging.error("* PRIVILEGED INTENTS ERROR")
            logging.error("* You need to enable intents in the Discord Developer Portal:")
            logging.error("* 1. Go to https://discord.com/developers/applications")
            logging.error("* 2. Select your application")
            logging.error("* 3. Go to the 'Bot' tab")
            logging.error("* 4. Enable 'Message Content Intent' under 'Privileged Gateway Intents'")
            logging.error("* 5. Click 'Save Changes'")
            logging.error("********************************************\n")
        raise

def main():
    """Main function - delegates to run.py for unified deployment"""
    try:
        # Import and run the unified application
        from run import main as run_main
        run_main()
        
    except KeyboardInterrupt:
        logging.info("Shutting down application...")
    except Exception as e:
        logging.error(f"Error running the application: {e}")
        exit(1)

def run_flask_app():
    """Run Flask web server on port 5000 for local development"""
    try:
        logging.info("Starting Flask web server on port 5000...")
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    except Exception as e:
        logging.error(f"Error running Flask app: {e}")

if __name__ == "__main__":
    main()
