from flask import Flask
import threading
import requests
import time

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = threading.Thread(target=run)
    t.daemon = True
    t.start()

def ping_self():
    """Ping self every 5 minutes to stay alive"""
    while True:
        try:
            requests.get("http://localhost:8080")
        except:
            pass
        time.sleep(300)  # 5 minutes

if __name__ == "__main__":
    keep_alive()
    ping_self()