# 🚨 URGENT: Gemini API Quick Fix Guide

## The Problem
Your Google Gemini API is not working due to:
1. ❌ Missing Python package
2. ❌ Outdated model name
3. 🔴 **LEAKED API KEY** (most critical)

## The Solution (5 Minutes)

### Step 1: Install Missing Package ✅ DONE
```bash
pip install -r requirements.txt
```

### Step 2: Get a New API Key 🔴 DO THIS NOW
1. **Delete the old key** at https://aistudio.google.com/app/apikey
2. **Create a new key** at the same URL
3. **Copy the new key immediately**

### Step 3: Configure the New API Key
**Create a file named `.env` in your project root:**

```env
GEMINI_API_KEY=paste_your_new_api_key_here
FLASK_SECRET_KEY=your-secret-key-here
FLASK_DEBUG=True
HOST=0.0.0.0
PORT=5000
```

**Example:**
```env
GEMINI_API_KEY=AIzaSyABC123xyz789...
FLASK_SECRET_KEY=my-super-secret-key-123
FLASK_DEBUG=True
HOST=0.0.0.0
PORT=5000
```

### Step 4: Test It
```bash
python test_gemini_direct.py
```

**Expected Output:**
```
✓ API Key Found
✓ API Configuration Successful
✓ Model Created Successfully
✓ Content Generation Successful
✓ ALL TESTS PASSED
```

### Step 5: Run Your App
```bash
python app.py
```

## What Was Fixed (Code Changes)

### ✅ Updated Model Names
Changed from `gemini-pro` → `gemini-2.5-flash` in:
- Chat endpoint
- Score endpoint
- Score-details endpoint

### ✅ Secured Config File
Removed hardcoded API key from `config.py`

### ✅ Added Security
- `.env.example` template created
- `.gitignore` already configured

## Testing Your Endpoints

### Health Check
```bash
curl http://localhost:5000/api/health
```

### Chat
```bash
curl -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d "{\"message\": \"Hello\"}"
```

### Website Score
```bash
curl -X POST http://localhost:5000/api/score -H "Content-Type: application/json" -d "{\"url\": \"https://example.com\"}"
```

## 🔐 Security Checklist
- [ ] Generated new API key
- [ ] Deleted old leaked key
- [ ] Created `.env` file with new key
- [ ] Verified `.env` is in `.gitignore`
- [ ] Tested API with `test_gemini_direct.py`
- [ ] **NEVER commit `.env` to git**

## For Deployment (Render/Heroku/etc)
Don't use `.env` file in production. Instead:
1. Go to your hosting dashboard
2. Find "Environment Variables" section
3. Add: `GEMINI_API_KEY` = your new API key
4. Redeploy your app

## Need Help?
- Read: `GEMINI_API_FIX_PLAN.md` for detailed explanation
- Test: Run `python test_gemini_direct.py`
- List models: Run `python list_models.py`

## Summary
✅ **Fixed**: Missing package installed
✅ **Fixed**: Model names updated to `gemini-2.5-flash`
✅ **Fixed**: Removed hardcoded API key from code
🔴 **YOU NEED TO**: Create new API key and add to `.env` file
