#!/usr/bin/env python3
"""
Robust keep-alive system for 24/7 Discord bot uptime
Combines multiple strategies to maintain connection
"""

import requests
import time
import threading
import logging
from flask import Flask

# Flask app for external pinging
app = Flask(__name__)

@app.route('/')
def home():
    return {
        "status": "alive",
        "bot": "PopoCorps",
        "uptime": time.time(),
        "message": "Bot is running 24/7"
    }

@app.route('/ping')
def ping():
    return {"ping": "pong", "timestamp": time.time()}

@app.route('/health')
def health():
    return {"healthy": True, "service": "discord-bot"}

class RobustKeepAlive:
    """Advanced keep-alive system"""
    
    def __init__(self, port=8080):
        self.port = port
        self.running = True
        self.ping_urls = [
            "https://uptimerobot.com/",
            "https://httpbin.org/status/200"
        ]
        
    def start_server(self):
        """Start the keep-alive server"""
        def run_server():
            app.run(host='0.0.0.0', port=self.port, debug=False)
        
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        logging.info(f"Keep-alive server started on port {self.port}")
        
    def start_ping_service(self):
        """Start continuous ping service"""
        def ping_loop():
            while self.running:
                try:
                    # Self-ping to keep process active
                    requests.get(f"http://127.0.0.1:{self.port}/ping", timeout=5)
                    
                    # External pings to maintain network activity
                    for url in self.ping_urls:
                        try:
                            requests.get(url, timeout=3)
                        except:
                            pass  # Silent fail for external services
                            
                    time.sleep(300)  # Ping every 5 minutes
                    
                except Exception as e:
                    logging.error(f"Ping service error: {e}")
                    time.sleep(60)
        
        ping_thread = threading.Thread(target=ping_loop, daemon=True)
        ping_thread.start()
        logging.info("Continuous ping service started")
        
    def start(self):
        """Start all keep-alive services"""
        self.start_server()
        self.start_ping_service()
        
    def stop(self):
        """Stop keep-alive services"""
        self.running = False

# Global instance
keep_alive = RobustKeepAlive()

def start_keep_alive():
    """Initialize robust keep-alive system"""
    keep_alive.start()

if __name__ == "__main__":
    start_keep_alive()
    
    # Keep script running
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        keep_alive.stop()