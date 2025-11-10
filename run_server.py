#!/usr/bin/env python3
"""
Start Flask app without auto-reload to prevent restart loops
"""
from app import app
from config import FLASK_DEBUG, HOST, PORT, GEMINI_API_KEY

if __name__ == '__main__':
    print(f"Starting server on {HOST}:{PORT}")
    print(f"Gemini API Key Status: {'Configured' if GEMINI_API_KEY else 'NOT CONFIGURED'}")
    if not GEMINI_API_KEY:
        print("WARNING: Please update .env with your Gemini API key")
    
    # Run without auto-reload to prevent restart issues
    app.run(debug=False, host=HOST, port=PORT, use_reloader=False)
