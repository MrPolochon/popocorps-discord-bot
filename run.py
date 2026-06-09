#!/usr/bin/env python3
"""
Unified application runner for cloud deployment
Runs both Discord bot and Flask web server concurrently
"""

import os
import logging
import asyncio
import threading
import time
import discord
from bot import bot
from app import app, set_discord_bot
from uptime_monitor import uptime_monitor

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
    """Run the Discord bot.

    We rely on discord.py's built-in auto-reconnect for transient network
    issues, and on the host's restart policy (railway.json restartPolicyType)
    to restart the whole process on fatal errors. Re-using/closing the same
    bot instance in a manual loop is not supported by discord.py and causes a
    rapid crash loop, so we start it exactly once here.
    """
    from health_monitor import health_monitor

    logging.info("Starting Discord bot...")
    health_monitor.update_heartbeat()

    try:
        await bot.start(TOKEN)
    except discord.LoginFailure:
        logging.critical(
            "Token Discord invalide (DISCORD_TOKEN). Verifie/regenere le token "
            "dans le Developer Portal et mets-le a jour dans les variables Railway."
        )
        raise
    except discord.PrivilegedIntentsRequired:
        logging.critical(
            "Intents privilegies manquants. Active 'MESSAGE CONTENT INTENT' et "
            "'SERVER MEMBERS INTENT' dans l'onglet Bot du Developer Portal, puis redeploie."
        )
        raise
    except Exception as e:
        health_monitor.log_error(f"Bot error: {e}")
        logging.exception(f"Erreur inattendue du bot: {e}")
        raise
    finally:
        if not bot.is_closed():
            await bot.close()

def run_flask_app():
    """Run Flask web server on the port provided by the host (Railway sets $PORT)"""
    try:
        port = int(os.environ.get("PORT", 5000))
        logging.info(f"Starting Flask web server on port {port}...")
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False, threaded=True)
    except Exception as e:
        logging.error(f"Error running Flask app: {e}")

def main():
    """Main function for cloud deployment - run both services"""
    try:
        # Start Flask web server in background thread
        logging.info("Initializing Flask web server...")
        flask_thread = threading.Thread(target=run_flask_app, daemon=True, name="FlaskServer")
        flask_thread.start()
        
        # Give Flask time to initialize
        time.sleep(2)
        
        logging.info("Flask web server started on port 5000")
        logging.info("Web dashboard available at: http://0.0.0.0:5000")
        logging.info("Initializing Discord bot...")
        
        # Run Discord bot in main thread
        asyncio.run(run_discord_bot())
        
    except KeyboardInterrupt:
        logging.info("Shutting down application...")
    except Exception as e:
        logging.error(f"Critical error in main application: {e}")
        exit(1)

if __name__ == "__main__":
    main()