# Google Gemini API Fix Plan

## Issues Identified

### 1. ✅ Missing Package (FIXED)
**Problem**: The `google-generativeai` package was not installed.
**Solution**: Installed all required packages from `requirements.txt`.
```bash
pip install -r requirements.txt
```

### 2. ✅ Incorrect Model Name (FIXED)
**Problem**: The code was using outdated model names:
- `gemini-pro` (no longer available)
- `gemini-1.5-flash` (not supported)

**Solution**: Updated all references to use `gemini-2.5-flash` (stable, recommended model).

**Files Updated**:
- `app.py` - Updated 3 instances of model creation
  - Line ~95: Chat endpoint
  - Line ~280: Score endpoint
  - Line ~360: Score-details endpoint

### 3. 🔴 CRITICAL: API Key Security Issue (REQUIRES ACTION)
**Problem**: The API key in `config.py` has been reported as leaked and is now disabled.
```
Error: 403 Your API key was reported as leaked. Please use another API key.
```

**Root Cause**: 
- API key was hardcoded in `config.py` and likely committed to version control
- Google automatically disables leaked keys for security

**Required Actions**:

#### Step 1: Generate a New API Key
1. Go to https://makersuite.google.com/app/apikey (or https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API key"
4. Copy the new API key immediately (you won't be able to see it again)
5. **Delete the old leaked key** from the Google AI Studio console

#### Step 2: Secure the API Key Properly
**NEVER hardcode API keys in source files!**

**Option A: Use .env file (Recommended for development)**
1. Create a `.env` file in the project root (already supported by the code):
```env
GEMINI_API_KEY=your_new_api_key_here
FLASK_SECRET_KEY=your-secret-key-here
FLASK_DEBUG=True
HOST=0.0.0.0
PORT=5000
```

2. Add `.env` to `.gitignore`:
```gitignore
.env
config.py
*.pyc
__pycache__/
```

**Option B: Use environment variables (Recommended for production)**
```bash
# Windows PowerShell
$env:GEMINI_API_KEY="your_new_api_key_here"

# Windows Command Prompt
set GEMINI_API_KEY=your_new_api_key_here

# Linux/Mac
export GEMINI_API_KEY="your_new_api_key_here"
```

**Option C: For Render deployment**
1. Go to your Render dashboard
2. Select your service
3. Go to "Environment" tab
4. Add environment variable:
   - Key: `GEMINI_API_KEY`
   - Value: your new API key
5. Save and redeploy

#### Step 3: Remove Hardcoded Key from config.py
Update `config.py` to ONLY read from environment variables:
```python
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Google Gemini API Configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')  # No default hardcoded key!

# Flask Configuration
FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'

# Server Configuration
HOST = os.getenv('HOST', '0.0.0.0')
PORT = int(os.getenv('PORT', 5000))
```

#### Step 4: Clean Git History (If committed to git)
If the API key was committed to git:
```bash
# Remove the file from git history (but keep local copy)
git rm --cached config.py

# Add to .gitignore
echo "config.py" >> .gitignore
echo ".env" >> .gitignore

# Commit the changes
git add .gitignore
git commit -m "Remove sensitive config files from version control"

# Optional: Clean entire git history (advanced)
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch config.py" \
  --prune-empty --tag-name-filter cat -- --all
```

## Testing the Fix

After setting up the new API key, test with:
```bash
python test_gemini_direct.py
```

Expected output:
```
============================================================
Google Gemini API Test
============================================================

1. API Key Status:
   ✓ API Key Found: AIzaSy****...****

2. Configuring Gemini API...
   ✓ API Configuration Successful

3. Testing Model Creation...
   ✓ Model Created Successfully (gemini-2.5-flash)

4. Testing Content Generation...
   ✓ Content Generation Successful
   Response: Hello, I am working!

5. Testing Available Models...
   ✓ Available Models:
      - models/gemini-2.5-flash
      - models/gemini-2.5-pro
      - ...

============================================================
✓ ALL TESTS PASSED - Gemini API is working correctly!
============================================================
```

## Running the Application

Once the API key is configured:
```bash
python app.py
```

Test the endpoints:
```bash
# Health check
curl http://localhost:5000/api/health

# Chat endpoint
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, tell me about web accessibility"}'

# Score endpoint
curl -X POST http://localhost:5000/api/score \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

## Summary

### What Was Fixed:
✅ Installed missing `google-generativeai` package
✅ Updated model name from `gemini-pro` → `gemini-2.5-flash`
✅ Updated model name from `gemini-1.5-flash` → `gemini-2.5-flash`

### What You Need To Do:
🔴 **CRITICAL**: Generate a new API key (old one is leaked/disabled)
🔴 **CRITICAL**: Secure the new API key in `.env` file or environment variables
🔴 **CRITICAL**: Remove hardcoded API key from `config.py`
🔴 **IMPORTANT**: Add `.env` and `config.py` to `.gitignore`
🟡 **RECOMMENDED**: Clean git history if the key was committed

### Available Models:
- `gemini-2.5-flash` (fast, recommended) ✅ **USING THIS**
- `gemini-2.5-pro` (more powerful, slower)
- `gemini-flash-latest` (always latest version)
- `gemini-pro-latest` (always latest pro version)

### API Key Security Best Practices:
1. ❌ **NEVER** hardcode API keys in source files
2. ❌ **NEVER** commit API keys to version control
3. ✅ **ALWAYS** use environment variables or `.env` files
4. ✅ **ALWAYS** add `.env` to `.gitignore`
5. ✅ **ALWAYS** rotate keys if they are accidentally exposed
6. ✅ **ALWAYS** use different keys for development and production
7. ✅ **ALWAYS** set API usage limits in Google Cloud Console
