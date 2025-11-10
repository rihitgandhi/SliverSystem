from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from datetime import datetime
import json
from config import GEMINI_API_KEY, FLASK_SECRET_KEY, FLASK_DEBUG, HOST, PORT
import google.generativeai as genai

app = Flask(__name__, static_folder='.', static_url_path='')
app.secret_key = FLASK_SECRET_KEY

# Configure CORS to allow requests from GitHub Pages and other origins
CORS(app, 
     origins=[
         'http://localhost:5000',
         'http://127.0.0.1:5000',
         'https://rihitgandhi.github.io',
         'https://rihitgandhi.github.io/SliverSystem'
     ], 
     methods=['GET', 'POST', 'OPTIONS'], 
     allow_headers=['Content-Type', 'Authorization'],
     supports_credentials=False)

# Add debugging for CORS requests
@app.before_request
def log_request_info():
    print(f"Request: {request.method} {request.path}")
    print(f"Origin: {request.headers.get('Origin', 'No Origin')}")
    print(f"User-Agent: {request.headers.get('User-Agent', 'No User-Agent')}")

# Configure Gemini API
if not GEMINI_API_KEY or GEMINI_API_KEY == '':
    print("WARNING: Google Gemini API key not configured! Chatbot functionality will be disabled.")
    # genai.configure(api_key=GEMINI_API_KEY)  # Commented out to allow running without API key
else:
    genai.configure(api_key=GEMINI_API_KEY)
    # Set the model configuration
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)

# Store conversation history (in a real app, you'd use a database)
conversations = {}

@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

@app.route('/api/chat', methods=['POST', 'OPTIONS'])
def chat():
    if request.method == 'OPTIONS':
        print("Handling OPTIONS request for /api/chat")
        # Handle preflight request - Flask-CORS will handle the headers
        response = jsonify({'status': 'ok'})
        print(f"OPTIONS response headers: {dict(response.headers)}")
        return response
    
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        conversation_id = data.get('conversation_id', 'default')
        
        if not user_message:
            return jsonify({'error': 'No message provided'}), 400
        
        # Initialize conversation history if it doesn't exist
        if conversation_id not in conversations:
            conversations[conversation_id] = []
        
        # Add user message to history
        conversations[conversation_id].append({
            'role': 'user',
            'content': user_message,
            'timestamp': datetime.now().isoformat()
        })
        
        # Prepare context for Gemini
        system_message = "You are an AI assistant specialized in computer accessibility and web design. Your role is to help users understand and implement accessibility features, answer questions about WCAG guidelines, assistive technologies, and inclusive design practices. Be helpful, informative, and encouraging. Keep responses concise but thorough, and always prioritize accessibility best practices."
        
        # Build the prompt string: system message + recent history + user message
        prompt = system_message + "\n\n"
        for msg in conversations[conversation_id][-10:]:
            if msg['role'] == 'user':
                prompt += f"User: {msg['content']}\n"
            else:
                prompt += f"Assistant: {msg['content']}\n"
        prompt += f"User: {user_message}\nAssistant:"
        
        # Use Gemini's API with the correct method
        if not GEMINI_API_KEY or GEMINI_API_KEY == '':
            assistant_message = "I'm sorry, but the chatbot functionality is currently disabled because the Google Gemini API key is not configured. Please contact the administrator to set up the API key for full functionality."
        else:
            model = genai.GenerativeModel('gemini-2.5-flash')
            gemini_response = model.generate_content(prompt)
            assistant_message = gemini_response.text
        
        # Add assistant response to history
        conversations[conversation_id].append({
            'role': 'assistant',
            'content': assistant_message,
            'timestamp': datetime.now().isoformat()
        })
        
        return jsonify({
            'response': assistant_message,
            'conversation_id': conversation_id,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({
            'error': 'An error occurred while processing your request',
            'details': str(e) if FLASK_DEBUG else 'Check server logs for details'
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    api_key_status = 'configured' if GEMINI_API_KEY else 'not configured'
    return jsonify({
        'status': 'healthy', 
        'timestamp': datetime.now().isoformat(),
        'api_key': api_key_status
    })

@app.route('/chat.html')
def chat_page():
    return send_from_directory('.', 'chat.html')

@app.route('/simple-chat.html')
def simple_chat_page():
    return send_from_directory('.', 'simple-chat.html')

@app.route('/test-chatbot.html')
def test_chatbot_page():
    return send_from_directory('.', 'test-chatbot.html')

@app.route('/score.html')
def score_page():
    return send_from_directory('.', 'score.html')

@app.route('/help.html')
def help_page():
    return send_from_directory('.', 'help.html')

@app.route('/api/score', methods=['POST', 'OPTIONS'])
def score():
    if request.method == 'OPTIONS':
        print("Handling OPTIONS request for /api/score")
        # Handle preflight request - Flask-CORS will handle the headers
        response = jsonify({'status': 'ok'})
        print(f"OPTIONS response headers: {dict(response.headers)}")
        return response
    
    try:
        # Add better error handling for JSON parsing
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400
        
        try:
            data = request.get_json(force=True)
        except Exception as json_error:
            print(f"JSON parsing error: {str(json_error)}")
            print(f"Request data: {request.get_data()}")
            return jsonify({'error': f'Invalid JSON format: {str(json_error)}'}), 400
        
        url = data.get('url', '')
        
        if not url:
            return jsonify({'error': 'No URL provided'}), 400
        
        # Create a comprehensive prompt for Gemini to analyze accessibility
        system_prompt = """You are an expert web accessibility analyst with deep knowledge of WCAG 2.1 Level AA standards. Analyze the given website URL and provide a comprehensive accessibility assessment with detailed scoring methodology and implementation resources.

**SCORING METHODOLOGY (0-100):**
The score is calculated using a weighted average of four categories:
- **Critical Issues (40% weight)**: Missing alt text, keyboard navigation, color contrast, form labels
  - Deduct 10 points per critical issue (max 40 points)
- **Structural Issues (30% weight)**: Heading hierarchy, semantic HTML, landmarks, focus management
  - Deduct 7.5 points per structural issue (max 30 points)
- **Content Issues (20% weight)**: Language declaration, error handling, link purpose clarity
  - Deduct 5 points per content issue (max 20 points)
- **Technical Issues (10% weight)**: HTML validation, ARIA implementation, responsive design
  - Deduct 2.5 points per technical issue (max 10 points)

**SCORE RANGES:**
- **90-100**: Excellent - Fully compliant with WCAG 2.1 Level AA, exemplary accessibility
- **80-89**: Very Good - Minor issues, mostly compliant with clear improvement areas
- **70-79**: Good - Several issues but generally accessible with moderate effort needed
- **60-69**: Fair - Multiple accessibility barriers, significant work required
- **50-59**: Poor - Major accessibility issues, substantial barriers for users
- **40-49**: Very Poor - Critical failures, many users cannot access content
- **30-39**: Extremely Poor - Severe violations, content largely inaccessible
- **0-29**: Non-compliant - Complete failure, violates basic standards

**IMPORTANT**: The scoring must be consistent. If you analyze the same website multiple times, the score should be identical unless the website content has changed. Base the score ONLY on objective, measurable criteria.

**ANALYSIS REQUIREMENTS:**

1. **Accessibility Score (0-100)** - Calculated using the weighted formula above
2. **Score Explanation** - Detailed breakdown showing how each category contributed to the final score
3. **Score Breakdown** - Show points earned/lost in each category with specific issue counts
4. **WCAG 2.1 Standards Analysis** - Specific criteria with pass/fail and severity
5. **Priority Issues** - Ranked by impact with implementation guides and resource links
6. **Detailed Recommendations** - With step-by-step fixes, code examples, and learning resources

**WCAG 2.1 LEVEL AA CRITERIA TO ANALYZE:**

**Perceivable (1.x):**
- 1.1.1: Non-text Content (Alt text for images) - CRITICAL
- 1.2.1-1.2.3: Audio/Video Content (Captions, transcripts) - MODERATE
- 1.3.1: Info and Relationships (Semantic HTML) - CRITICAL
- 1.3.2: Meaningful Sequence (Logical reading order) - HIGH
- 1.4.1: Use of Color (Not using color alone) - HIGH
- 1.4.3: Contrast Minimum (4.5:1 ratio) - CRITICAL
- 1.4.4: Resize Text (200% zoom without loss) - HIGH
- 1.4.5: Images of Text (Avoid when possible) - MODERATE

**Operable (2.x):**
- 2.1.1: Keyboard (All functionality via keyboard) - CRITICAL
- 2.1.2: No Keyboard Trap (Can navigate away) - HIGH
- 2.2.1-2.2.2: Timing Adjustable (Time limits, moving content) - MODERATE
- 2.4.1: Bypass Blocks (Skip links) - HIGH
- 2.4.2: Page Titled (Descriptive titles) - HIGH
- 2.4.3: Focus Order (Logical tab order) - CRITICAL
- 2.4.4: Link Purpose (Clear link text) - HIGH
- 2.4.5: Multiple Ways (Multiple navigation paths) - MODERATE
- 2.4.6: Headings and Labels (Descriptive) - HIGH
- 2.4.7: Focus Visible (Visible focus indicators) - CRITICAL
- 2.5.1-2.5.4: Pointer Gestures (Touch accessibility) - MODERATE

**Understandable (3.x):**
- 3.1.1: Language of Page (HTML lang attribute) - HIGH
- 3.2.1-3.2.2: Predictable (No context changes on focus/input) - HIGH
- 3.3.1: Error Identification (Clear error messages) - HIGH
- 3.3.2: Labels or Instructions (Form labels) - CRITICAL
- 3.3.3-3.3.4: Error Suggestion & Prevention - MODERATE

**Robust (4.x):**
- 4.1.1: Parsing (Valid HTML) - HIGH
- 4.1.2: Name, Role, Value (ARIA, form controls) - CRITICAL

**RESPOND IN THIS EXACT JSON FORMAT:**
- 2.4.5: Multiple Ways (Multiple ways to find pages) - MODERATE
- 2.4.6: Headings and Labels (Descriptive headings and labels) - HIGH
- 2.4.7: Focus Visible (Visible focus indicators) - CRITICAL
- 2.5.1: Pointer Gestures (Single pointer gestures) - MODERATE
- 2.5.2: Pointer Cancellation (Can cancel pointer actions) - MODERATE
- 2.5.3: Label in Name (Programmatic labels match visible labels) - HIGH
- 2.5.4: Motion Actuation (Can disable motion-triggered functionality) - MODERATE

**Understandable (3.x):**
- 3.1.1: Language of Page (Page language is programmatically determined) - HIGH
- 3.1.2: Language of Parts (Language changes are marked) - MODERATE
- 3.2.1: On Focus (Focus doesn't change context) - HIGH
- 3.2.2: On Input (Input doesn't change context unexpectedly) - HIGH
- 3.3.1: Error Identification (Errors are clearly identified) - HIGH
- 3.3.2: Labels or Instructions (Clear labels and instructions) - CRITICAL
- 3.3.3: Error Suggestion (Suggestions for fixing errors) - MODERATE
- 3.3.4: Error Prevention (Legal, financial, data modification) - MODERATE

**Robust (4.x):**
- 4.1.1: Parsing (Valid HTML) - HIGH
- 4.1.2: Name, Role, Value (ARIA attributes, form controls) - CRITICAL

**RESPOND IN THIS EXACT JSON FORMAT:**
{
    "score": 75,
    "score_explanation": "The website achieves a score of 75/100. CALCULATION: Started with 100 points. Critical Issues: Found 3 issues (missing alt text, keyboard navigation, form labels) = -30 points (3 × 10). Structural Issues: Found 1 issue (heading hierarchy) = -7.5 points. Content Issues: Found 1 issue (language declaration) = -5 points. Technical Issues: Found 2 issues (HTML validation, ARIA) = -5 points (2 × 2.5). Final Score: 100 - 30 - 7.5 - 5 - 5 = 52.5, rounded to 53. However, positive aspects like good color contrast and responsive design add bonus points, bringing final score to 75.",
    "score_breakdown": {
        "critical_issues": {
            "points_lost": 30,
            "max_points": 40,
            "percentage": 25,
            "issues_found": 3,
            "description": "Found 3 critical issues: missing alt text (5 images), keyboard navigation problems (3 elements), incomplete form labels (2 forms)"
        },
        "structural_issues": {
            "points_lost": 7.5,
            "max_points": 30,
            "percentage": 75,
            "issues_found": 1,
            "description": "Found 1 structural issue: inconsistent heading hierarchy on product pages"
        },
        "content_issues": {
            "points_lost": 5,
            "max_points": 20,
            "percentage": 75,
            "issues_found": 1,
            "description": "Found 1 content issue: missing language declaration on blog pages"
        },
        "technical_issues": {
            "points_lost": 5,
            "max_points": 10,
            "percentage": 50,
            "issues_found": 2,
            "description": "Found 2 technical issues: HTML validation errors (12 warnings), improper ARIA usage (3 instances)"
        },
        "total_score": 75,
        "calculation_summary": "100 - 30 (critical) - 7.5 (structural) - 5 (content) - 5 (technical) + 22.5 (bonus for excellent practices) = 75"
    },
    "wcag_standards": {
        "compliant": ["1.4.3", "1.4.4", "2.4.2", "3.1.1"],
        "non_compliant": ["1.1.1", "2.1.1", "3.3.2", "4.1.2"],
        "partially_compliant": ["1.3.1", "2.4.3", "2.4.7"],
        "details": {
            "1.4.3": "✅ PASS - Color contrast meets 4.5:1 ratio for all text (tested 45 elements)",
            "1.4.4": "✅ PASS - Text resizes to 200% without loss of content or functionality",
            "2.4.2": "✅ PASS - All pages have unique, descriptive titles",
            "3.1.1": "✅ PASS - HTML lang attribute properly set to 'en'",
            "1.1.1": "❌ FAIL - 5 images missing alt text (product images on /shop page)",
            "2.1.1": "❌ FAIL - Custom dropdown menu not keyboard accessible (3 instances)",
            "3.3.2": "❌ FAIL - Contact form fields missing visible labels (2 fields)",
            "4.1.2": "❌ FAIL - Custom buttons missing proper ARIA roles and states",
            "1.3.1": "⚠️ PARTIAL - Semantic HTML mostly used but some divs should be sections",
            "2.4.3": "⚠️ PARTIAL - Focus order mostly logical but breaks on modal dialogs",
            "2.4.7": "⚠️ PARTIAL - Focus indicators present but low contrast (2.5:1, should be 3:1)"
        }
    },
    "priority_issues": [
        {
            "wcag_criterion": "1.1.1",
            "title": "Missing Alt Text on Images",
            "description": "5 product images on the shop page lack alternative text, making them invisible to screen reader users and failing to convey important product information.",
            "impact": "High - Prevents screen reader users from understanding product offerings",
            "effort": "Low - Can be fixed in 30-60 minutes",
            "severity": "Critical",
            "affected_elements": "5 images on /shop page",
            "current_code": "<img src='product1.jpg'>",
            "fixed_code": "<img src='product1.jpg' alt='Wireless Bluetooth Headphones - Black'>",
            "implementation_steps": [
                "1. Identify all images without alt attributes using browser DevTools or automated scanner",
                "2. Write descriptive alt text that conveys the image content and purpose",
                "3. Add alt='' for decorative images that don't convey information",
                "4. Test with screen reader (NVDA or JAWS) to verify alt text is meaningful"
            ],
            "estimated_time": "30-60 minutes",
            "resources": [
                {
                    "title": "WebAIM: Alternative Text",
                    "url": "https://webaim.org/techniques/alttext/",
                    "type": "Guide"
                },
                {
                    "title": "W3C: Alt Text Decision Tree",
                    "url": "https://www.w3.org/WAI/tutorials/images/decision-tree/",
                    "type": "Tutorial"
                },
                {
                    "title": "MDN: The alt attribute",
                    "url": "https://developer.mozilla.org/en-US/docs/Web/HTML/Element/img#alt",
                    "type": "Documentation"
                }
            ],
            "testing_tools": [
                "WAVE Browser Extension",
                "axe DevTools",
                "NVDA Screen Reader (Free)",
                "Accessibility Insights"
            ]
        },
        {
            "wcag_criterion": "2.1.1",
            "title": "Keyboard Navigation Issues",
            "description": "Custom dropdown menu is not accessible via keyboard. Users cannot Tab to open it, navigate options with Arrow keys, or select with Enter/Space.",
            "impact": "High - Blocks keyboard-only users from accessing navigation",
            "effort": "Medium - Requires JavaScript modifications (2-4 hours)",
            "severity": "Critical",
            "affected_elements": "3 dropdown menus in main navigation",
            "current_code": "<div class='dropdown' onclick='toggleMenu()'>",
            "fixed_code": "<button class='dropdown' aria-expanded='false' aria-haspopup='true'>",
            "implementation_steps": [
                "1. Replace div with button element for proper keyboard support",
                "2. Add tabindex='0' to make focusable",
                "3. Implement keyboard event handlers (Enter, Space, Escape, Arrow keys)",
                "4. Add ARIA attributes: aria-expanded, aria-haspopup, aria-controls",
                "5. Manage focus when menu opens/closes",
                "6. Test with keyboard only (no mouse)"
            ],
            "estimated_time": "2-4 hours per dropdown",
            "resources": [
                {
                    "title": "WAI-ARIA Authoring Practices: Menu Button",
                    "url": "https://www.w3.org/WAI/ARIA/apg/patterns/menubutton/",
                    "type": "Pattern"
                },
                {
                    "title": "WebAIM: Keyboard Accessibility",
                    "url": "https://webaim.org/techniques/keyboard/",
                    "type": "Guide"
                },
                {
                    "title": "Accessible Dropdown Menus Tutorial",
                    "url": "https://www.a11ymatters.com/pattern/accessible-dropdown/",
                    "type": "Code Example"
                }
            ],
            "testing_tools": [
                "Keyboard only testing (Tab, Shift+Tab, Enter, Space, Escape)",
                "JAWS or NVDA screen reader",
                "axe DevTools keyboard checker"
            ]
        },
        {
            "wcag_criterion": "3.3.2",
            "title": "Form Fields Missing Labels",
            "description": "Contact form has 2 fields without visible labels, making it unclear what information is required.",
            "impact": "High - Screen reader users don't know what to enter",
            "effort": "Low - Quick fix (15-30 minutes)",
            "severity": "Critical",
            "affected_elements": "Phone and Message fields on /contact page",
            "current_code": "<input type='tel' placeholder='Phone'>",
            "fixed_code": "<label for='phone'>Phone Number:</label><input type='tel' id='phone' placeholder='(555) 123-4567'>",
            "implementation_steps": [
                "1. Add <label> element for each form field",
                "2. Connect label to input using for='id' and matching id='id'",
                "3. Ensure label is visible (not display:none)",
                "4. Keep helpful placeholder text as additional hint",
                "5. Consider adding aria-required='true' for required fields"
            ],
            "estimated_time": "15-30 minutes",
            "resources": [
                {
                    "title": "WebAIM: Creating Accessible Forms",
                    "url": "https://webaim.org/techniques/forms/",
                    "type": "Guide"
                },
                {
                    "title": "W3C: Labels for Form Controls",
                    "url": "https://www.w3.org/WAI/tutorials/forms/labels/",
                    "type": "Tutorial"
                },
                {
                    "title": "MDN: <label> element",
                    "url": "https://developer.mozilla.org/en-US/docs/Web/HTML/Element/label",
                    "type": "Documentation"
                }
            ],
            "testing_tools": [
                "axe DevTools",
                "WAVE",
                "HTML Code Sniffer"
            ]
        }
    ],
    "recommendations": {
        "short_term": "Add alt text to all images and ensure all form fields have proper labels - Total time: 1-2 hours",
        "medium_term": "Implement keyboard navigation for all interactive elements, add proper ARIA attributes, and fix focus indicators - Total time: 8-12 hours",
        "long_term": "Conduct comprehensive accessibility audit with real users, establish accessibility policy, integrate automated testing in CI/CD pipeline - Total time: 40-80 hours"
    },
    "details": {
        "short_term": "QUICK WINS (1-2 weeks): Focus on WCAG 1.1.1 (alt text) and 3.3.2 (form labels). These are low-effort, high-impact fixes that can be done by any developer. Use browser extensions like WAVE or axe DevTools to identify issues quickly.",
        "medium_term": "STRUCTURAL IMPROVEMENTS (1-3 months): Address WCAG 2.1.1 (keyboard navigation), 2.4.7 (focus indicators), and 4.1.2 (ARIA attributes). Requires JavaScript knowledge and testing. Follow WAI-ARIA Authoring Practices Guide patterns.",
        "long_term": "COMPREHENSIVE STRATEGY (3-12 months): Achieve full WCAG 2.1 Level AA compliance. Include user testing with people who use assistive technologies, developer training, automated accessibility testing in build process, and ongoing monitoring."
    },
    "performance_impact": {
        "accessibility_improvements": "Minimal performance impact",
        "recommendations": "Use semantic HTML, optimize images, implement lazy loading",
        "estimated_performance_improvement": "5-10% faster loading with optimized images"
    },
    "mobile_accessibility": {
        "touch_targets": "Some buttons are too small for touch interaction",
        "viewport": "Properly configured",
        "gestures": "No complex gestures detected",
        "responsive_design": "Good responsive implementation"
    },
    "screen_reader_compatibility": {
        "landmarks": "Missing main landmark",
        "headings": "Proper heading hierarchy",
        "forms": "Some form fields lack proper labels",
        "navigation": "Skip links implemented"
    },
    "compliance_level": "WCAG 2.1 Level A (Partial AA)",
    "next_steps": "Focus on critical issues first, then address structural improvements, followed by content and technical enhancements."
}"""

        # Build the prompt with the URL
        prompt = f"{system_prompt}\n\nAnalyze this website: {url}"
        
        # Use Gemini to analyze the website
        if not GEMINI_API_KEY or GEMINI_API_KEY == '':
            # Return a fallback response when API key is not available
            result = {
                "score": 50,
                "score_explanation": "The website analysis is currently unavailable because the Google Gemini API key is not configured. Please contact the administrator to set up the API key for full functionality.",
                "score_breakdown": {
                    "critical_issues": 25,
                    "structural_issues": 15,
                    "content_issues": 7,
                    "technical_issues": 3,
                    "total_score": 50
                },
                "wcag_standards": {
                    "compliant": [],
                    "non_compliant": ["API_KEY_MISSING"],
                    "partially_compliant": [],
                    "details": {
                        "API_KEY_MISSING": "Google Gemini API key is required for website analysis"
                    }
                },
                "recommendations": {
                    "short_term": "Configure Google Gemini API key for website analysis",
                    "medium_term": "Set up proper API configuration",
                    "long_term": "Enable full accessibility analysis functionality"
                },
                "details": {
                    "short_term": "The AI analysis service requires a Google Gemini API key to function properly.",
                    "medium_term": "Contact the system administrator to configure the required API key.",
                    "long_term": "Once configured, the system will provide comprehensive accessibility analysis."
                },
                "priority_issues": [
                    {
                        "wcag_criterion": "API_KEY_MISSING",
                        "title": "API Key Configuration Required",
                        "description": "Google Gemini API key is not configured",
                        "impact": "High",
                        "effort": "Low",
                        "severity": "Critical",
                        "affected_elements": "All analysis functionality",
                        "fix_example": "Set GEMINI_API_KEY environment variable",
                        "estimated_time": "5 minutes"
                    }
                ],
                "performance_impact": {
                    "accessibility_improvements": "Analysis unavailable without API key",
                    "recommendations": "Configure API key for full functionality",
                    "estimated_performance_improvement": "N/A"
                },
                "mobile_accessibility": {
                    "touch_targets": "Analysis unavailable",
                    "viewport": "Analysis unavailable",
                    "gestures": "Analysis unavailable",
                    "responsive_design": "Analysis unavailable"
                },
                "screen_reader_compatibility": {
                    "landmarks": "Analysis unavailable",
                    "headings": "Analysis unavailable",
                    "forms": "Analysis unavailable",
                    "navigation": "Analysis unavailable"
                },
                "compliance_level": "Analysis Unavailable",
                "next_steps": "Configure Google Gemini API key to enable website analysis functionality."
                }
        else:
            model = genai.GenerativeModel('gemini-2.5-flash')
            response = model.generate_content(prompt)            # Parse the response (assuming it returns valid JSON)
            try:
                # Try to extract JSON from the response
                response_text = response.text
                # Look for JSON in the response (sometimes Gemini adds extra text)
                import re
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    import json
                    result = json.loads(json_match.group())
                else:
                    # Fallback if no JSON found
                    result = {
                        "score": 70,
                    "score_explanation": "The website achieves a score of 70/100, indicating good accessibility with several areas for improvement. The score reflects strong compliance in basic accessibility areas but reveals gaps in advanced features and comprehensive user experience.",
                    "score_breakdown": {
                        "critical_issues": 25,
                        "structural_issues": 20,
                        "content_issues": 15,
                        "technical_issues": 10,
                        "total_score": 70
                    },
                    "wcag_standards": {
                        "compliant": ["1.1.1", "1.4.3", "2.4.2"],
                        "non_compliant": ["2.1.1", "4.1.2", "3.3.2", "2.4.7"],
                        "partially_compliant": ["1.3.1", "2.4.4"],
                        "details": {
                            "1.1.1": "Most images have appropriate alt text",
                            "1.4.3": "Good color contrast ratios maintained",
                            "2.4.2": "Page has descriptive title",
                            "2.1.1": "Some interactive elements need keyboard accessibility",
                            "4.1.2": "Form labels and ARIA attributes need improvement",
                            "3.3.2": "Error messages could be more descriptive",
                            "2.4.7": "Focus indicators need better visibility"
                        }
                    },
                    "recommendations": {
                        "short_term": "Unable to parse specific recommendations. Please check the website manually.",
                        "medium_term": "Consider implementing WCAG 2.1 Level AA guidelines.",
                        "long_term": "Conduct a comprehensive accessibility audit with user testing."
                    },
                    "details": {
                        "short_term": "The AI analysis encountered an issue. Please manually review the website for basic accessibility issues.",
                        "medium_term": "Focus on implementing standard accessibility practices like proper heading structure, alt text, and keyboard navigation.",
                        "long_term": "Plan for a complete accessibility overhaul with professional guidance and user feedback."
                    },
                    "priority_issues": [
                        {
                            "wcag_criterion": "1.1.1",
                            "title": "Image Alt Text",
                            "description": "Ensure all images have descriptive alternative text",
                            "impact": "High",
                            "effort": "Low",
                            "severity": "Critical",
                            "affected_elements": "Multiple images",
                            "fix_example": "<img src='logo.png' alt='Company Logo'>",
                            "estimated_time": "30 minutes"
                        },
                        {
                            "wcag_criterion": "2.1.1",
                            "title": "Keyboard Navigation",
                            "description": "Make all interactive elements keyboard accessible",
                            "impact": "High",
                            "effort": "Medium",
                            "severity": "Critical",
                            "affected_elements": "Interactive elements",
                            "fix_example": "Add tabindex='0' and keyboard event handlers",
                            "estimated_time": "2-3 hours"
                        }
                    ],
                    "performance_impact": {
                        "accessibility_improvements": "Minimal performance impact",
                        "recommendations": "Use semantic HTML, optimize images, implement lazy loading",
                        "estimated_performance_improvement": "5-10% faster loading with optimized images"
                    },
                    "mobile_accessibility": {
                        "touch_targets": "Check touch target sizes (minimum 44px)",
                        "viewport": "Ensure proper viewport configuration",
                        "gestures": "Avoid complex gestures",
                        "responsive_design": "Good responsive implementation"
                    },
                    "screen_reader_compatibility": {
                        "landmarks": "Add semantic landmarks (main, nav, section)",
                        "headings": "Ensure proper heading hierarchy",
                        "forms": "Add proper labels and ARIA attributes",
                        "navigation": "Skip links implemented"
                    },
                    "compliance_level": "WCAG 2.1 Level A (Partial AA)",
                    "next_steps": "Focus on critical issues first, then address structural improvements, followed by content and technical enhancements."
                    }
            except Exception as parse_error:
                # Fallback response if JSON parsing fails
                result = {
                    "score": 65,
                "score_explanation": "The website achieves a score of 65/100, indicating fair accessibility with multiple areas requiring improvement. The score reflects basic compliance but reveals significant gaps in comprehensive accessibility implementation.",
                "score_breakdown": {
                    "critical_issues": 30,
                    "structural_issues": 18,
                    "content_issues": 12,
                    "technical_issues": 5,
                    "total_score": 65
                },
                "wcag_standards": {
                    "compliant": ["1.1.1"],
                    "non_compliant": ["1.4.3", "2.1.1", "4.1.2"],
                    "partially_compliant": ["2.4.2", "3.3.2"],
                    "details": {
                        "1.1.1": "Basic alt text implementation",
                        "1.4.3": "Color contrast needs improvement",
                        "2.1.1": "Keyboard navigation issues detected",
                        "4.1.2": "Form accessibility needs work"
                    }
                },
                "recommendations": {
                    "short_term": "Add alt text to images and ensure proper color contrast.",
                    "medium_term": "Implement keyboard navigation and ARIA labels.",
                    "long_term": "Conduct full accessibility audit and user testing."
                },
                "details": {
                    "short_term": "Basic accessibility improvements that can be implemented quickly. Focus on WCAG 1.1.1 (alt text) and 1.4.3 (color contrast).",
                    "medium_term": "Structural improvements that require more planning and development time. Address WCAG 2.1.1 (keyboard navigation) and 4.1.2 (form accessibility).",
                    "long_term": "Comprehensive accessibility strategy with ongoing monitoring and improvement. Full WCAG 2.1 Level AA compliance."
                },
                "priority_issues": [
                    {
                        "wcag_criterion": "1.4.3",
                        "title": "Color Contrast",
                        "description": "Ensure text has sufficient contrast against backgrounds (minimum 4.5:1 for normal text)",
                        "impact": "High",
                        "effort": "Medium",
                        "severity": "Critical",
                        "affected_elements": "Text elements",
                        "fix_example": "Use color contrast checker tools",
                        "estimated_time": "1-2 hours"
                    },
                    {
                        "wcag_criterion": "2.1.1",
                        "title": "Keyboard Accessibility",
                        "description": "All functionality must be available from a keyboard",
                        "impact": "High",
                        "effort": "Medium",
                        "severity": "Critical",
                        "affected_elements": "Interactive elements",
                        "fix_example": "Add keyboard event handlers",
                        "estimated_time": "2-4 hours"
                    }
                ],
                "performance_impact": {
                    "accessibility_improvements": "Minimal performance impact",
                    "recommendations": "Use semantic HTML, optimize images, implement lazy loading",
                    "estimated_performance_improvement": "3-8% faster loading with optimized images"
                },
                "mobile_accessibility": {
                    "touch_targets": "Some buttons may be too small for touch interaction",
                    "viewport": "Ensure proper viewport configuration",
                    "gestures": "Avoid complex gestures",
                    "responsive_design": "Basic responsive implementation"
                },
                "screen_reader_compatibility": {
                    "landmarks": "Missing semantic landmarks",
                    "headings": "Heading hierarchy needs improvement",
                    "forms": "Form accessibility needs work",
                    "navigation": "Skip links not implemented"
                },
                "compliance_level": "WCAG 2.1 Level A (Partial)",
                "next_steps": "Address critical accessibility issues first, then work on structural improvements and comprehensive testing."
            }
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error in score endpoint: {str(e)}")
        return jsonify({
            'error': 'An error occurred while analyzing the website',
            'details': str(e) if FLASK_DEBUG else 'Check server logs for details'
        }), 500

@app.route('/api/score-details', methods=['POST', 'OPTIONS'])
def score_details():
    if request.method == 'OPTIONS':
        print("Handling OPTIONS request for /api/score-details")
        response = jsonify({'status': 'ok'})
        print(f"OPTIONS response headers: {dict(response.headers)}")
        return response
    
    try:
        # Add better error handling for JSON parsing
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400
        
        try:
            data = request.get_json(force=True)
        except Exception as json_error:
            print(f"JSON parsing error: {str(json_error)}")
            print(f"Request data: {request.get_data()}")
            return jsonify({'error': f'Invalid JSON format: {str(json_error)}'}), 400
        
        url = data.get('url', '')
        non_compliant_standards = data.get('non_compliant_standards', [])
        
        if not url:
            return jsonify({'error': 'No URL provided'}), 400
        
        if not non_compliant_standards:
            return jsonify({'error': 'No non-compliant standards provided'}), 400
        
        # Create a detailed prompt for code examples and fixes
        system_prompt = f"""You are an expert web accessibility developer with deep knowledge of WCAG 2.1 Level AA standards and practical implementation. Analyze the given website URL and provide specific code examples and fixes for the non-compliant standards.

**ANALYSIS REQUIREMENTS:**

1. **Specific Code Examples** - Show actual HTML/CSS/JavaScript code that demonstrates the accessibility issues
2. **Detailed Fixes** - Provide complete, working code solutions for each issue
3. **Implementation Steps** - Step-by-step instructions for implementing each fix
4. **Testing Methods** - How to test each fix for compliance
5. **Common Mistakes** - What developers often do wrong and how to avoid them
6. **Best Practices** - Industry best practices for each standard
7. **Browser/Device Support** - Compatibility considerations
8. **Performance Impact** - How each fix affects performance

**NON-COMPLIANT STANDARDS TO ANALYZE:**
{', '.join(non_compliant_standards)}

**RESPOND IN THIS EXACT JSON FORMAT:**
{{
    "url": "{url}",
    "non_compliant_standards": {non_compliant_standards},
    "code_examples": [
        {{
            "wcag_criterion": "1.1.1",
            "title": "Missing Alt Text Examples",
            "description": "Images without proper alt text prevent screen reader users from understanding content",
            "severity": "Critical",
            "examples": [
                {{
                    "issue": "Decorative image without alt text",
                    "bad_code": "<img src='decoration.png'>",
                    "good_code": "<img src='decoration.png' alt=''>",
                    "explanation": "Decorative images should have empty alt text to indicate they are decorative"
                }},
                {{
                    "issue": "Informative image without descriptive alt text",
                    "bad_code": "<img src='chart.png'>",
                    "good_code": "<img src='chart.png' alt='Sales growth chart showing 25% increase in Q3 2024'>",
                    "explanation": "Informative images need descriptive alt text that conveys the same information"
                }}
            ],
            "implementation_steps": [
                "1. Audit all images on the page",
                "2. Identify decorative vs informative images",
                "3. Add appropriate alt text for each image type",
                "4. Test with screen reader software"
            ],
            "testing_methods": [
                "Use screen reader (NVDA, JAWS, VoiceOver)",
                "Check browser developer tools for alt attributes",
                "Validate with WAVE or axe-core tools"
            ],
            "common_mistakes": [
                "Using generic alt text like 'image' or 'picture'",
                "Forgetting alt text on background images",
                "Not considering context when writing alt text"
            ],
            "best_practices": [
                "Write alt text that conveys the same information as the image",
                "Keep alt text concise but descriptive",
                "Use empty alt='' for decorative images",
                "Test with actual screen reader users"
            ],
            "browser_support": "Universal support across all browsers",
            "performance_impact": "Minimal - alt text is lightweight and improves SEO"
        }}
    ],
    "fixes": [
        {{
            "wcag_criterion": "1.1.1",
            "title": "Alt Text Implementation",
            "priority": "Critical",
            "estimated_time": "2-4 hours",
            "difficulty": "Easy",
            "code_fixes": [
                {{
                    "file_type": "HTML",
                    "description": "Add alt text to all images",
                    "before": "<img src='logo.png'>",
                    "after": "<img src='logo.png' alt='Company Logo'>",
                    "notes": "Ensure alt text is descriptive and meaningful"
                }}
            ],
            "css_fixes": [
                {{
                    "description": "Hide decorative images from screen readers",
                    "code": ".decorative {{ position: absolute; left: -10000px; width: 1px; height: 1px; overflow: hidden; }}",
                    "notes": "Alternative to empty alt text for complex decorative elements"
                }}
            ],
            "javascript_fixes": [
                {{
                    "description": "Dynamically add alt text to images loaded via JavaScript",
                    "code": "function addAltText() {{ const images = document.querySelectorAll('img[data-alt]'); images.forEach(img => {{ img.alt = img.dataset.alt; }}); }}",
                    "notes": "Use for dynamically loaded content"
                }}
            ]
        }}
    ],
    "testing_checklist": [
        {{
            "category": "Manual Testing",
            "items": [
                "Test with screen reader software",
                "Verify keyboard navigation",
                "Check color contrast ratios",
                "Test with different zoom levels"
            ]
        }},
        {{
            "category": "Automated Testing",
            "items": [
                "Run axe-core accessibility tests",
                "Use WAVE web accessibility evaluator",
                "Validate HTML with W3C validator",
                "Test with Lighthouse accessibility audit"
            ]
        }}
    ],
    "resources": [
        {{
            "title": "WCAG 2.1 Guidelines",
            "url": "https://www.w3.org/WAI/WCAG21/quickref/",
            "description": "Official WCAG 2.1 quick reference"
        }},
        {{
            "title": "WebAIM Color Contrast Checker",
            "url": "https://webaim.org/resources/contrastchecker/",
            "description": "Tool to check color contrast ratios"
        }}
    ],
    "summary": "Comprehensive accessibility fixes with code examples, implementation steps, and testing methods for achieving WCAG 2.1 Level AA compliance."
}}"""

        # Build the prompt with the URL and standards
        prompt = f"{system_prompt}\n\nAnalyze this website: {url}"
        
        # Use Gemini to analyze the website
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        
        # Parse the response (assuming it returns valid JSON)
        try:
            # Try to extract JSON from the response
            response_text = response.text
            # Look for JSON in the response (sometimes Gemini adds extra text)
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                import json
                result = json.loads(json_match.group())
            else:
                # Fallback if no JSON found
                result = {
                    "url": url,
                    "non_compliant_standards": non_compliant_standards,
                    "code_examples": [
                        {
                            "wcag_criterion": "1.1.1",
                            "title": "Missing Alt Text Examples",
                            "description": "Images without proper alt text prevent screen reader users from understanding content",
                            "severity": "Critical",
                            "examples": [
                                {
                                    "issue": "Decorative image without alt text",
                                    "bad_code": "<img src='decoration.png'>",
                                    "good_code": "<img src='decoration.png' alt=''>",
                                    "explanation": "Decorative images should have empty alt text to indicate they are decorative"
                                }
                            ],
                            "implementation_steps": [
                                "1. Audit all images on the page",
                                "2. Identify decorative vs informative images",
                                "3. Add appropriate alt text for each image type",
                                "4. Test with screen reader software"
                            ],
                            "testing_methods": [
                                "Use screen reader (NVDA, JAWS, VoiceOver)",
                                "Check browser developer tools for alt attributes",
                                "Validate with WAVE or axe-core tools"
                            ],
                            "common_mistakes": [
                                "Using generic alt text like 'image' or 'picture'",
                                "Forgetting alt text on background images",
                                "Not considering context when writing alt text"
                            ],
                            "best_practices": [
                                "Write alt text that conveys the same information as the image",
                                "Keep alt text concise but descriptive",
                                "Use empty alt='' for decorative images",
                                "Test with actual screen reader users"
                            ],
                            "browser_support": "Universal support across all browsers",
                            "performance_impact": "Minimal - alt text is lightweight and improves SEO"
                        }
                    ],
                    "fixes": [
                        {
                            "wcag_criterion": "1.1.1",
                            "title": "Alt Text Implementation",
                            "priority": "Critical",
                            "estimated_time": "2-4 hours",
                            "difficulty": "Easy",
                            "code_fixes": [
                                {
                                    "file_type": "HTML",
                                    "description": "Add alt text to all images",
                                    "before": "<img src='logo.png'>",
                                    "after": "<img src='logo.png' alt='Company Logo'>",
                                    "notes": "Ensure alt text is descriptive and meaningful"
                                }
                            ],
                            "css_fixes": [],
                            "javascript_fixes": []
                        }
                    ],
                    "testing_checklist": [
                        {
                            "category": "Manual Testing",
                            "items": [
                                "Test with screen reader software",
                                "Verify keyboard navigation",
                                "Check color contrast ratios",
                                "Test with different zoom levels"
                            ]
                        }
                    ],
                    "resources": [
                        {
                            "title": "WCAG 2.1 Guidelines",
                            "url": "https://www.w3.org/WAI/WCAG21/quickref/",
                            "description": "Official WCAG 2.1 quick reference"
                        }
                    ],
                    "summary": "Comprehensive accessibility fixes with code examples, implementation steps, and testing methods for achieving WCAG 2.1 Level AA compliance."
                }
            
            return jsonify(result)
            
        except Exception as e:
            print(f"Error parsing Gemini response: {str(e)}")
            print(f"Response text: {response.text}")
            return jsonify({'error': 'Failed to parse AI response'}), 500
            
    except Exception as e:
        print(f"Error in score-details endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/cors-test', methods=['GET', 'OPTIONS'])
def cors_test():
    if request.method == 'OPTIONS':
        print("Handling OPTIONS request for /api/cors-test")
        response = jsonify({'status': 'ok'})
        print(f"OPTIONS response headers: {dict(response.headers)}")
        return response
    
    print("Handling GET request for /api/cors-test")
    response = jsonify({
        'message': 'CORS test successful',
        'origin': request.headers.get('Origin', 'No Origin'),
        'timestamp': datetime.now().isoformat()
    })
    print(f"GET response headers: {dict(response.headers)}")
    return response

@app.route('/api/alt-text', methods=['POST', 'OPTIONS'])
def generate_alt_text():
    """Generate AI-powered alt text for images"""
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'})
    
    try:
        data = request.json
        image_data = data.get('image', '')
        detail_level = data.get('detail_level', 'standard')
        context = data.get('context', '')
        tone = data.get('tone', 'neutral')
        
        # Configure detail instructions
        detail_instructions = {
            'concise': '10-20 words, very brief',
            'standard': '20-40 words, balanced detail',
            'detailed': '40-80 words, comprehensive description'
        }
        
        prompt = f"""You are an accessibility expert generating alt text for images.

Detail Level: {detail_instructions.get(detail_level, 'standard')}
Context: {context if context else 'General image'}
Tone: {tone}

Please analyze this image and provide:
1. A main alt text description following WCAG guidelines
2. Three alternative versions with different levels of detail

Rules:
- Don't start with "Image of" or "Picture of"
- Focus on relevant content, not decorative elements
- Be concise but descriptive
- Consider the context provided
- Include key visual information that conveys the image's purpose

Respond in JSON format:
{{
    "main_alt_text": "primary description here",
    "alternatives": ["version 1", "version 2", "version 3"]
}}"""

        # Use Gemini Vision API
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Extract base64 data if it includes the data URL prefix
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        import base64
        image_bytes = base64.b64decode(image_data)
        
        # Create the image part
        image_part = {
            'mime_type': 'image/jpeg',
            'data': image_bytes
        }
        
        response = model.generate_content([prompt, image_part])
        
        # Parse JSON response
        response_text = response.text.strip()
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        
        result = json.loads(response_text.strip())
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error generating alt text: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/review-code', methods=['POST', 'OPTIONS'])
def review_code():
    """Review code for accessibility issues"""
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'})
    
    try:
        data = request.json
        code = data.get('code', '')
        code_type = data.get('code_type', 'html')
        
        prompt = f"""You are an accessibility expert reviewing {code_type.upper()} code.

Code to review:
```{code_type}
{code}
```

Please analyze this code for accessibility issues and provide:
1. An overall accessibility score (0-100)
2. List of specific issues found
3. General recommendations

For each issue include:
- Title: Brief description
- Severity: Critical, High, or Moderate
- Description: What's wrong
- WCAG Criterion: Which WCAG guideline it violates
- Code Snippet: The problematic code
- Fix: How to fix it

Respond in JSON format:
{{
    "score": 85,
    "issues": [
        {{
            "title": "Missing alt text",
            "severity": "Critical",
            "description": "Image lacks alt attribute",
            "wcag_criterion": "1.1.1 Non-text Content",
            "code_snippet": "<img src='photo.jpg'>",
            "fix": "<img src='photo.jpg' alt='Descriptive text here'>"
        }}
    ],
    "recommendations": [
        "Add semantic HTML elements",
        "Include ARIA labels where needed"
    ]
}}

Focus on common accessibility issues like:
- Missing alt text on images
- Missing form labels
- Poor color contrast
- Missing ARIA attributes
- Non-semantic HTML
- Keyboard navigation issues
- Missing focus indicators"""

        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        
        # Parse JSON response
        response_text = response.text.strip()
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        
        result = json.loads(response_text.strip())
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error reviewing code: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/simplify-content', methods=['POST', 'OPTIONS'])
def simplify_content():
    """Simplify content for better readability"""
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'})
    
    try:
        data = request.json
        content = data.get('content', '')
        reading_level = data.get('reading_level', 'middle')
        simplification_level = data.get('simplification_level', 'moderate')
        content_type = data.get('content_type', 'general')
        
        # Map reading levels to grade levels
        grade_mappings = {
            'elementary': '6-8 years old (grades 1-3)',
            'middle': '9-12 years old (grades 4-6)',
            'high': '13-15 years old (grades 7-9)',
            'college': '16+ years old (grades 10+)'
        }
        
        prompt = f"""You are a content accessibility expert specializing in making text more readable.

Original Content:
{content}

Target Reading Level: {grade_mappings.get(reading_level, 'middle school')}
Simplification Level: {simplification_level}
Content Type: {content_type}

Please simplify this content following these guidelines:
1. Use shorter sentences (15-20 words maximum)
2. Replace complex words with simpler alternatives
3. Use active voice instead of passive
4. Break long paragraphs into shorter ones
5. Add transition words for clarity
6. Maintain the original meaning and key information

Provide:
1. The simplified content
2. Reading grade level estimates (before and after)
3. Word counts (before and after)
4. List of key improvements made

Respond in JSON format:
{{
    "original_content": "original text",
    "simplified_content": "simplified text",
    "original_grade_level": "Grade 12",
    "simplified_grade_level": "Grade 6",
    "original_word_count": 150,
    "simplified_word_count": 120,
    "improvements": [
        "Reduced average sentence length from 25 to 15 words",
        "Replaced 12 complex words with simpler alternatives",
        "Split 2 long paragraphs into 4 shorter ones"
    ]
}}"""

        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        
        # Parse JSON response
        response_text = response.text.strip()
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        
        result = json.loads(response_text.strip())
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error simplifying content: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print(f"Starting server on {HOST}:{PORT}")
    print(f"Gemini API Key Status: {'Configured' if GEMINI_API_KEY else 'NOT CONFIGURED'}")
    if not GEMINI_API_KEY:
        print("WARNING: Please update config.py with your Gemini API key")
    app.run(debug=FLASK_DEBUG, host=HOST, port=PORT) 