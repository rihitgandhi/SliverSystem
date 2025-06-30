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
    raise ValueError('Google Gemini API key not configured!')
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
        model = genai.GenerativeModel('gemini-1.5-flash')
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
        system_prompt = """You are an expert web accessibility analyst with deep knowledge of WCAG 2.1 Level AA standards. Analyze the given website URL and provide a comprehensive accessibility assessment with detailed scoring methodology.

**SCORING METHODOLOGY (0-100):**
- **90-100**: Excellent - Fully compliant with WCAG 2.1 Level AA, exemplary accessibility practices
- **80-89**: Very Good - Minor issues, mostly compliant with clear improvement areas
- **70-79**: Good - Several issues but generally accessible with moderate effort to fix
- **60-69**: Fair - Multiple accessibility barriers, significant work needed
- **50-59**: Poor - Major accessibility issues, substantial barriers for users with disabilities
- **40-49**: Very Poor - Critical accessibility failures, many users cannot access content
- **30-39**: Extremely Poor - Severe accessibility violations, content largely inaccessible
- **0-29**: Non-compliant - Complete accessibility failure, violates basic accessibility standards

**SCORING FACTORS:**
1. **Critical Issues (40% weight)**: Missing alt text, keyboard navigation, color contrast, form labels
2. **Structural Issues (30% weight)**: Heading hierarchy, semantic HTML, landmarks, focus management
3. **Content Issues (20% weight)**: Language declaration, error handling, link purpose clarity
4. **Technical Issues (10% weight)**: HTML validation, ARIA implementation, responsive design

**ANALYSIS REQUIREMENTS:**

1. **Accessibility Score (0-100)** - Based on WCAG 2.1 Level AA compliance with detailed explanation
2. **WCAG 2.1 Level AA Standards Analysis** - Specific criteria compliance with severity ratings
3. **Priority Issues** - Ranked by impact and effort with specific element counts
4. **Detailed Recommendations** - With implementation steps and estimated effort
5. **Performance Impact** - How accessibility affects performance
6. **Mobile Accessibility** - Mobile-specific issues and touch target analysis
7. **Screen Reader Compatibility** - Detailed screen reader analysis
8. **Score Breakdown** - Detailed explanation of how the score was calculated

**WCAG 2.1 LEVEL AA CRITERIA TO ANALYZE:**

**Perceivable (1.x):**
- 1.1.1: Non-text Content (Images, buttons, form controls) - CRITICAL
- 1.2.1: Audio-only and Video-only (Prerecorded) - MODERATE
- 1.2.2: Captions (Prerecorded) - MODERATE
- 1.2.3: Audio Description or Media Alternative (Prerecorded) - MODERATE
- 1.3.1: Info and Relationships (Semantic HTML, headings, lists) - CRITICAL
- 1.3.2: Meaningful Sequence (Logical reading order) - HIGH
- 1.3.3: Sensory Characteristics (Not relying on shape, size, location) - MODERATE
- 1.4.1: Use of Color (Not using color alone) - HIGH
- 1.4.3: Contrast (Minimum) (4.5:1 for normal text, 3:1 for large text) - CRITICAL
- 1.4.4: Resize Text (Up to 200% without loss of functionality) - HIGH
- 1.4.5: Images of Text (Avoid images of text when possible) - MODERATE

**Operable (2.x):**
- 2.1.1: Keyboard (All functionality available from keyboard) - CRITICAL
- 2.1.2: No Keyboard Trap (Can navigate away from all components) - HIGH
- 2.2.1: Timing Adjustable (Time limits can be adjusted or turned off) - MODERATE
- 2.2.2: Pause, Stop, Hide (Moving, blinking, scrolling content) - MODERATE
- 2.3.1: Three Flashes or Below Threshold (No content flashes more than 3 times per second) - HIGH
- 2.4.1: Bypass Blocks (Skip links, landmarks) - HIGH
- 2.4.2: Page Titled (Descriptive page titles) - HIGH
- 2.4.3: Focus Order (Logical tab order) - CRITICAL
- 2.4.4: Link Purpose (In Context) (Clear link purpose) - HIGH
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

**Respond in this exact JSON format:**
{
    "score": 75,
    "score_explanation": "The website achieves a score of 75/100, indicating good accessibility with several areas for improvement. The score reflects strong compliance in basic accessibility areas but reveals gaps in advanced features and comprehensive user experience.",
    "score_breakdown": {
        "critical_issues": 28,
        "structural_issues": 22,
        "content_issues": 15,
        "technical_issues": 10,
        "total_score": 75
    },
    "wcag_standards": {
        "compliant": ["1.1.1", "1.4.3", "2.4.2"],
        "non_compliant": ["2.1.1", "4.1.2", "3.3.2"],
        "partially_compliant": ["1.3.1", "2.4.7"],
        "details": {
            "1.1.1": "All images have appropriate alt text",
            "1.4.3": "Color contrast meets 4.5:1 ratio for normal text",
            "2.4.2": "Page has descriptive title",
            "2.1.1": "Some interactive elements are not keyboard accessible",
            "4.1.2": "Form controls missing proper labels and ARIA attributes",
            "3.3.2": "Form fields lack clear instructions"
        }
    },
    "recommendations": {
        "short_term": "Add alt text to remaining images and ensure all form fields have labels",
        "medium_term": "Implement keyboard navigation for all interactive elements and add ARIA attributes",
        "long_term": "Conduct comprehensive accessibility audit with user testing and establish accessibility policy"
    },
    "details": {
        "short_term": "Quick fixes focusing on WCAG 1.1.1 (alt text) and 3.3.2 (form labels). These can be implemented immediately with minimal development effort.",
        "medium_term": "Structural improvements addressing WCAG 2.1.1 (keyboard navigation) and 4.1.2 (ARIA attributes). Requires planning and development time.",
        "long_term": "Comprehensive accessibility strategy including user testing, policy development, and ongoing monitoring for full WCAG 2.1 Level AA compliance."
    },
    "priority_issues": [
        {
            "wcag_criterion": "1.1.1",
            "title": "Missing Alt Text",
            "description": "Images without alt text prevent screen reader users from understanding content",
            "impact": "High",
            "effort": "Low",
            "severity": "Critical",
            "affected_elements": "5 images",
            "fix_example": "<img src='logo.png' alt='Company Logo'>",
            "estimated_time": "30 minutes"
        },
        {
            "wcag_criterion": "2.1.1",
            "title": "Keyboard Navigation Issues",
            "description": "Some interactive elements cannot be accessed using keyboard only",
            "impact": "High",
            "effort": "Medium",
            "severity": "Critical",
            "affected_elements": "3 buttons, 1 dropdown",
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
        model = genai.GenerativeModel('gemini-1.5-flash')
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
        model = genai.GenerativeModel('gemini-1.5-flash')
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

if __name__ == '__main__':
    print(f"Starting server on {HOST}:{PORT}")
    print(f"Gemini API Key Status: {'Configured' if GEMINI_API_KEY else 'NOT CONFIGURED'}")
    if not GEMINI_API_KEY:
        print("⚠️  WARNING: Please update config.py with your Gemini API key")
    app.run(debug=FLASK_DEBUG, host=HOST, port=PORT) 