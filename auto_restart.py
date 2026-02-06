#!/usr/bin/env python3
"""
Auto-restart system for PopoCorps Bot
Monitors and automatically restarts the bot if it crashes
"""

import subprocess
import time
import logging
import psutil
import os
import signal
from health_monitor import health_monitor

class AutoRestart:
    """Automatic restart system for the bot"""
    
    def __init__(self):
        self.process = None
        self.restart_count = 0
        self.max_restarts = 10
        self.restart_delay = 5
        self.check_interval = 10
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - AutoRestart - %(levelname)s - %(message)s'
        )
        
    def start_bot(self):
        """Start the bot process"""
        try:
            cmd = ["python", "main.py"]
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            logging.info(f"Bot started with PID {self.process.pid}")
            return True
        except Exception as e:
            logging.error(f"Failed to start bot: {e}")
            return False
            
    def is_bot_running(self):
        """Check if bot process is still running"""
        if not self.process:
            return False
            
        # Check if process is still alive
        if self.process.poll() is not None:
            return False
            
        # Check if PID exists
        try:
            return psutil.pid_exists(self.process.pid)
        except:
            return False
            
    def stop_bot(self):
        """Stop the bot process gracefully"""
        if self.process and self.is_bot_running():
            try:
                # Try graceful shutdown first
                self.process.terminate()
                self.process.wait(timeout=10)
                logging.info("Bot stopped gracefully")
            except subprocess.TimeoutExpired:
                # Force kill if needed
                self.process.kill()
                logging.warning("Bot force killed")
            except Exception as e:
                logging.error(f"Error stopping bot: {e}")
                
    def restart_bot(self):
        """Restart the bot"""
        if self.restart_count >= self.max_restarts:
            logging.critical("Max restarts reached, giving up")
            return False
            
        self.restart_count += 1
        logging.info(f"Restarting bot (attempt {self.restart_count}/{self.max_restarts})")
        
        # Stop current process
        self.stop_bot()
        
        # Wait before restart
        time.sleep(self.restart_delay)
        
        # Start new process
        return self.start_bot()
        
    def monitor_loop(self):
        """Main monitoring loop"""
        logging.info("Starting bot monitoring...")
        
        # Initial start
        if not self.start_bot():
            logging.critical("Failed to start bot initially")
            return
            
        while True:
            try:
                time.sleep(self.check_interval)
                
                # Check if bot is running
                if not self.is_bot_running():
                    logging.warning("Bot process died, restarting...")
                    if not self.restart_bot():
                        break
                        
                # Check health status
                health_status = health_monitor.get_health_status()
                if not health_status["healthy"]:
                    logging.warning("Bot unhealthy, restarting...")
                    if not self.restart_bot():
                        break
                        
                # Reset restart count if bot has been stable
                if self.restart_count > 0 and health_status["uptime_seconds"] > 300:  # 5 minutes
                    logging.info("Bot stable, resetting restart count")
                    self.restart_count = 0
                    
            except KeyboardInterrupt:
                logging.info("Shutdown requested")
                self.stop_bot()
                break
            except Exception as e:
                logging.error(f"Monitor error: {e}")
                time.sleep(30)  # Wait longer on errors

if __name__ == "__main__":
    monitor = AutoRestart()
    monitor.monitor_loop()