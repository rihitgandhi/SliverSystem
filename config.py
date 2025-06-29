import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Google Gemini API Configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')

# Flask Configuration
FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')
FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'

# Server Configuration
HOST = os.getenv('HOST', '0.0.0.0')
PORT = int(os.getenv('PORT', 5000)) 