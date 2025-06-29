# Configuration Template for Production
# Copy this to config.py and update with your actual values

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Keys - Use environment variables in production
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'your-api-key-here')

# Flask Configuration
FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')
FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

# Server Configuration
HOST = os.getenv('HOST', '0.0.0.0')
PORT = int(os.getenv('PORT', 5000))

# CORS Configuration
CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')

# Production Settings
if not FLASK_DEBUG:
    # Disable debug mode in production
    FLASK_DEBUG = False 