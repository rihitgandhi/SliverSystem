"""
Production Configuration for SliverSystem
This file contains production-specific settings
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Flask Configuration
FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-change-in-production')
FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'

# Server Configuration
HOST = os.getenv('HOST', '0.0.0.0')
PORT = int(os.getenv('PORT', 5000))

# Security Configuration
SECURE_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'X-XSS-Protection': '1; mode=block',
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
    'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' https:;"
}

# CORS Configuration
CORS_ORIGINS = [
    'https://yourdomain.com',
    'https://www.yourdomain.com',
    'http://localhost:3000',  # For development
    'http://localhost:5000'   # For development
]

# Rate Limiting
RATE_LIMIT = {
    'requests_per_minute': 60,
    'requests_per_hour': 1000
}

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Database Configuration (if needed in future)
DATABASE_URL = os.getenv('DATABASE_URL')

# Cache Configuration (if needed in future)
CACHE_TYPE = 'simple'
CACHE_DEFAULT_TIMEOUT = 300

# Error Reporting
SENTRY_DSN = os.getenv('SENTRY_DSN')

# Monitoring
ENABLE_METRICS = os.getenv('ENABLE_METRICS', 'false').lower() == 'true' 