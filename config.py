import os
from dotenv import load_dotenv
import logging

# Load environment variables from .env file (if present).
# override=True ensures the .env wins over any pre-existing OS env vars,
# which avoids subtle bugs when a stale value is set in the user's shell.
load_dotenv(override=True)

# Application environment: development | production
# In production set APP_ENV=production
APP_ENV = os.getenv('APP_ENV', 'development').lower()

# Azure OpenAI Configuration
# IMPORTANT: Do NOT hardcode your credentials in the repo.
# Provide AZURE_OPENAI_* values via environment variables (or a local .env during development).
AZURE_OPENAI_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT', '')
AZURE_OPENAI_API_KEY = os.getenv('AZURE_OPENAI_API_KEY', '')
AZURE_OPENAI_DEPLOYMENT = os.getenv('AZURE_OPENAI_DEPLOYMENT', '')
AZURE_OPENAI_API_VERSION = os.getenv('AZURE_OPENAI_API_VERSION', '2024-12-01-preview')

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
		if not AZURE_OPENAI_API_KEY:
			missing.append('AZURE_OPENAI_API_KEY')
		if not AZURE_OPENAI_ENDPOINT:
			missing.append('AZURE_OPENAI_ENDPOINT')
		if not AZURE_OPENAI_DEPLOYMENT:
			missing.append('AZURE_OPENAI_DEPLOYMENT')
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
