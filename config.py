import os
from dotenv import load_dotenv
import logging

# Load environment variables from .env file (if present)
load_dotenv()

# Application environment: development | production
# In production set APP_ENV=production
APP_ENV = os.getenv('APP_ENV', 'development').lower()

# Google Gemini API Configuration
# IMPORTANT: Do NOT hardcode your API key in the repo.
# Provide GEMINI_API_KEY via environment variables (or a local .env during development).
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')

# Flask Configuration
FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY', '')
FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

# Server Configuration
HOST = os.getenv('HOST', '0.0.0.0')
PORT = int(os.getenv('PORT', 5000))

# Logging helper
logger = logging.getLogger(__name__)


def _require_env_vars():
	"""Fail fast if required secrets are missing in production."""
	missing = []
	if APP_ENV == 'production':
		if not GEMINI_API_KEY:
			missing.append('GEMINI_API_KEY')
		if not FLASK_SECRET_KEY:
			missing.append('FLASK_SECRET_KEY')

	if missing:
		msg = f"Missing required environment variables for production: {', '.join(missing)}"
		# Log the error and raise so the app won't start with insecure config
		logger.error(msg)
		raise RuntimeError(msg)


# Run validation on import so incorrect deployments fail fast
try:
	_require_env_vars()
except RuntimeError:
	# Re-raise to make the error visible to callers; don't mask it
	raise
