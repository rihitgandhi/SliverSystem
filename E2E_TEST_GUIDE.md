## ✅ COMPLETE E2E TESTING GUIDE

### CURRENT STATUS:
✅ Server is running on http://127.0.0.1:5000
✅ Gemini API is configured
✅ Score page is open in Simple Browser
✅ All JavaScript errors have been fixed

---

### 🧪 E2E TEST - STEP BY STEP:

**Open the Score Page** (already done): http://127.0.0.1:5000/score.html

**Open Browser Console** (F12 or Right-click > Inspect > Console)

---

### ✅ EXPECTED CONSOLE OUTPUT (Score Page):

When you load score.html, you should see:
```
Score page script loaded
DOM ready, attaching form listener
Form found: [HTMLFormElement]
```

**✅ If you see these = JavaScript is working correctly!**

---

### 🎯 TEST THE SCORE FEATURE:

**Step 1:** In the score page, enter a URL in the input field:
- Example: `https://example.com`
- Or: `https://www.google.com`
- Or: `https://github.com`

**Step 2:** Click the "Check Accessibility" button

**Step 3:** Watch the Console - You should see:
```
Form submitted!
URL entered: https://example.com
Current hostname: 127.0.0.1
Current protocol: http:
Current origin: http://127.0.0.1:5000
Detected backend URL: http://localhost:5000
Sending request to: http://localhost:5000/api/score
Request data: {url: "https://example.com"}
```

**Step 4:** Button should change to "Analyzing..." with a ⏳ spinner

**Step 5:** Wait 30-60 seconds (Gemini AI is analyzing the website)

**Step 6:** Console should show:
```
Response status: 200
Response data: {score: 75, recommendations: {...}, ...}
```

**Step 7:** Results appear on the page:
- Accessibility Score (0-100)
- WCAG Compliance Standards
- Priority Issues
- Recommendations (Short/Medium/Long-term)

---

### ❌ IF IT DOESN'T WORK, CHECK:

**Console shows nothing when clicking button:**
- JavaScript didn't load
- Check if you see "Score page script loaded"

**Console shows "Form submitted!" but no request:**
- Backend URL detection issue
- Check the "Detected backend URL" log

**Console shows network error:**
- Server isn't running
- Check terminal: should show "Running on http://127.0.0.1:5000"

**Console shows 403/500 error:**
- Backend error
- Check server terminal for error logs

**Request times out:**
- Gemini API is taking too long
- Wait up to 2 minutes
- Check if API key is valid

---

### 🔧 DEBUGGING COMMANDS (if needed):

**Check if server is running:**
```powershell
curl http://localhost:5000/api/health
```
Expected: `{"status": "healthy", "api_key": "configured"}`

**Test API directly:**
```powershell
$body = @{url='https://example.com'} | ConvertTo-Json
Invoke-WebRequest -Uri 'http://127.0.0.1:5000/api/score' -Method POST -Body $body -ContentType 'application/json' -TimeoutSec 120
```

**Check API key:**
```powershell
python -c "from config import GEMINI_API_KEY; print('Configured' if GEMINI_API_KEY else 'Missing')"
```
Expected: `Configured`

---

### 📊 WHAT'S BEEN FIXED:

1. ✅ **index.html** - Added safety check for missing function
2. ✅ **score.html** - Fixed event listener with DOMContentLoaded
3. ✅ **score.html** - Added e.stopPropagation() to prevent redirect
4. ✅ **score.html** - Added comprehensive console logging
5. ✅ **app.py** - Updated to gemini-2.5-flash model
6. ✅ **.env** - Added valid API key

---

### 🎯 NEXT STEPS:

1. **Open the score page in Simple Browser** (already open)
2. **Press F12** to open DevTools > Console tab
3. **Verify you see**: "Score page script loaded"
4. **Enter a URL** and click "Check Accessibility"
5. **Watch the console** and tell me what you see!

---

**The application is ready to test! Try it now! 🚀**
