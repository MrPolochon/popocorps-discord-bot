#!/usr/bin/env python3
"""
Health Monitor for PopoCorps Bot
Monitors bot health and automatically restarts if needed
"""

import asyncio
import logging
import time
import psutil
import os
from datetime import datetime, timedelta

class HealthMonitor:
    """Monitor bot health and performance"""
    
    def __init__(self):
        self.last_heartbeat = time.time()
        self.error_count = 0
        self.restart_count = 0
        self.max_errors = 5
        self.max_memory_mb = 500
        self.check_interval = 30  # seconds
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - HealthMonitor - %(levelname)s - %(message)s'
        )
        
    def update_heartbeat(self):
        """Update the last heartbeat timestamp"""
        self.last_heartbeat = time.time()
        
    def check_memory_usage(self):
        """Check if memory usage is within limits"""
        try:
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            if memory_mb > self.max_memory_mb:
                logging.warning(f"High memory usage: {memory_mb:.1f}MB")
                return False
            return True
        except Exception as e:
            logging.error(f"Error checking memory: {e}")
            return True
            
    def check_heartbeat(self):
        """Check if bot is responding (heartbeat within last 60 seconds)"""
        time_since_heartbeat = time.time() - self.last_heartbeat
        if time_since_heartbeat > 60:
            logging.error(f"No heartbeat for {time_since_heartbeat:.1f} seconds")
            return False
        return True
        
    def log_error(self, error):
        """Log an error and increment error count"""
        self.error_count += 1
        logging.error(f"Error #{self.error_count}: {error}")
        
        if self.error_count >= self.max_errors:
            logging.critical(f"Too many errors ({self.error_count}), restart recommended")
            return True
        return False
        
    def reset_error_count(self):
        """Reset error count after successful operation"""
        if self.error_count > 0:
            logging.info(f"Resetting error count (was {self.error_count})")
            self.error_count = 0
            
    def get_health_status(self):
        """Get comprehensive health status"""
        return {
            "healthy": self.check_heartbeat() and self.check_memory_usage(),
            "last_heartbeat": datetime.fromtimestamp(self.last_heartbeat).isoformat(),
            "error_count": self.error_count,
            "restart_count": self.restart_count,
            "memory_usage_mb": self._get_memory_usage(),
            "uptime_seconds": time.time() - self.last_heartbeat
        }
        
    def _get_memory_usage(self):
        """Get current memory usage in MB"""
        try:
            process = psutil.Process(os.getpid())
            return round(process.memory_info().rss / 1024 / 1024, 1)
        except:
            return 0

# Global health monitor instance
health_monitor = HealthMonitor()