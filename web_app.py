#!/usr/bin/env python3
"""
Web application entry point for Flask dashboard
This file is specifically for running the web interface
"""

import os
import sys
from app import app

if __name__ == "__main__":
    # Run Flask app directly for development
    app.run(host="0.0.0.0", port=5000, debug=True)
else:
    # For production deployment with gunicorn
    application = app