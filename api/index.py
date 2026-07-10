import sys
import os

# Add the project root to the Python path so all imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app

# Create the Flask application for Vercel
app = create_app("production")

# Vercel expects the WSGI callable to be named `app`
# No need for app.run() — Vercel handles serving automatically
