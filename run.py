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
    """Run the Discord bot with ultra-robust 24/7 reconnection system"""
    from health_monitor import health_monitor
    
    reconnect_count = 0
    max_consecutive_failures = 100  # Allow many retries
    
    while True:  # Infinite retry loop for guaranteed 24/7 uptime
        try:
            reconnect_count += 1
            logging.info(f"Starting Discord bot... (attempt #{reconnect_count})")
            health_monitor.update_heartbeat()
            
            # Reset bot connection if needed
            if not bot.is_closed():
                await bot.close()
                await asyncio.sleep(2)
            
            await bot.start(TOKEN)
            
        except discord.LoginFailure:
            logging.critical("Invalid Discord token - cannot continue")
            break
        except discord.PrivilegedIntentsRequired:
            logging.critical("Missing privileged intents - check Discord Developer Portal")
            break
        except (discord.ConnectionClosed, discord.HTTPException, discord.GatewayNotFound) as e:
            health_monitor.log_error(f"Discord connection error: {e}")
            logging.warning(f"Discord connection issue: {e} - reconnecting...")
            await asyncio.sleep(5)
            continue
        except Exception as e:
            health_monitor.log_error(f"Bot error: {e}")
            logging.error(f"Unexpected bot error: {e}")
            
            # Progressive backoff for stability
            if reconnect_count % 10 == 0:
                wait_time = min(30, reconnect_count // 10 * 5)
                logging.info(f"Progressive backoff: waiting {wait_time}s before retry")
                await asyncio.sleep(wait_time)
            else:
                await asyncio.sleep(10)
            
            # Reset counter after many successful connections
            if reconnect_count > max_consecutive_failures:
                logging.warning("Max consecutive failures reached - continuing anyway for 24/7 uptime")
                reconnect_count = 0
            
            continue

def run_flask_app():
    """Run Flask web server on configured port"""
    try:
        port = int(os.getenv("PORT", "5000"))
        logging.info("Starting Flask web server on port %s...", port)
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
        
        port = int(os.getenv("PORT", "5000"))
        logging.info("Flask web server started on port %s", port)
        logging.info("Web dashboard available at: http://0.0.0.0:%s", port)
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
