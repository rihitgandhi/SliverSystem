#!/usr/bin/env python3
"""
Start Flask app without auto-reload to prevent restart loops
"""
from app import app
from config import FLASK_DEBUG, HOST, PORT
import ai_client

if __name__ == '__main__':
    print(f"Starting server on {HOST}:{PORT}")
    print(f"Azure OpenAI Status: {'Configured' if ai_client.is_configured() else 'NOT CONFIGURED'}")
    if not ai_client.is_configured():
        print("WARNING: Please update .env with your Azure OpenAI credentials (AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT)")

    # Run without auto-reload to prevent restart issues
    app.run(debug=False, host=HOST, port=PORT, use_reloader=False)
