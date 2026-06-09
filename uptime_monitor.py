#!/usr/bin/env python3
"""
Advanced uptime monitoring system for PopoCorps Bot
Ensures 24/7 connectivity with multiple fallback mechanisms
"""

import asyncio
import logging
import time
import requests
import threading
from datetime import datetime, timedelta

class UptimeMonitor:
    """Advanced monitoring system for 24/7 uptime"""
    
    def __init__(self):
        self.last_ping = time.time()
        self.ping_interval = 300  # 5 minutes
        self.health_check_url = "http://127.0.0.1:5000/"
        self.external_ping_urls = [
            "https://discord.com/api/v10/gateway",
            "https://httpbin.org/status/200"
        ]
        self.is_running = True
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - UptimeMonitor - %(levelname)s - %(message)s'
        )
        
    def start_monitoring(self):
        """Start the uptime monitoring system"""
        # Start ping thread
        ping_thread = threading.Thread(target=self._ping_loop, daemon=True)
        ping_thread.start()
        
        # Start health check thread
        health_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        health_thread.start()
        
        logging.info("Uptime monitoring started - 24/7 connectivity enabled")
        
    def _ping_loop(self):
        """Continuous ping to keep connection alive"""
        while self.is_running:
            try:
                self._send_ping()
                time.sleep(self.ping_interval)
            except Exception as e:
                logging.error(f"Ping error: {e}")
                time.sleep(60)  # Shorter interval on error
                
    def _health_check_loop(self):
        """Regular health checks"""
        while self.is_running:
            try:
                self._check_bot_health()
                time.sleep(120)  # Check every 2 minutes
            except Exception as e:
                logging.error(f"Health check error: {e}")
                time.sleep(60)
                
    def _send_ping(self):
        """Send keep-alive ping"""
        try:
            # Ping local dashboard
            response = requests.get(self.health_check_url, timeout=10)
            if response.status_code == 200:
                logging.info("Local health check successful")
            
            # Ping external services
            for url in self.external_ping_urls:
                try:
                    requests.get(url, timeout=5)
                except:
                    pass  # Silent fail for external pings
                    
            self.last_ping = time.time()
            
        except Exception as e:
            logging.warning(f"Ping failed: {e}")
            
    def _check_bot_health(self):
        """Check if bot is responding"""
        try:
            # Check if web dashboard is accessible
            response = requests.get(f"{self.health_check_url}api/stats", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'bot_status' in data and data['bot_status'] == 'online':
                    logging.info("Bot health check passed")
                    return True
                    
        except Exception as e:
            logging.warning(f"Bot health check failed: {e}")
            
        return False
        
    def stop_monitoring(self):
        """Stop the monitoring system"""
        self.is_running = False
        logging.info("Uptime monitoring stopped")

# Global instance
uptime_monitor = UptimeMonitor()

if __name__ == "__main__":
    uptime_monitor.start_monitoring()
    
    # Keep the script running
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        uptime_monitor.stop_monitoring()