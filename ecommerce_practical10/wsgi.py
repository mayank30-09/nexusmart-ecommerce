"""
wsgi.py - WSGI application entry point for Gunicorn production deployment.
"""
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from app import app

if __name__ == "__main__":
    app.run()
