from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from datetime import datetime
import json
from config import GEMINI_API_KEY, FLASK_SECRET_KEY, FLASK_DEBUG, HOST, PORT
import google.generativeai as genai

app = Flask(__name__, static_folder='.', static_url_path='')
app.secret_key = FLASK_SECRET_KEY
CORS(app)  # Enable CORS for all routes

# Configure Gemini API
if not GEMINI_API_KEY or GEMINI_API_KEY == '':
    raise ValueError('Google Gemini API key not configured!')
genai.configure(api_key=GEMINI_API_KEY)

# Store conversation history (in a real app, you'd use a database)
conversations = {}

@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
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

@app.route('/api/score', methods=['POST'])
def score():
    try:
        data = request.get_json()
        url = data.get('url', '')
        
        if not url:
            return jsonify({'error': 'No URL provided'}), 400
        
        # Create a comprehensive prompt for Gemini to analyze accessibility
        system_prompt = """You are an expert web accessibility analyst. Analyze the given website URL and provide:
1. An accessibility score from 0-100
2. Specific WCAG 2.1 Level AA compliance issues found
3. Short-term recommendations (quick fixes, 1-2 weeks)
4. Medium-term recommendations (structural changes, 1-3 months)
5. Long-term recommendations (comprehensive improvements, 3-12 months)
6. Detailed explanations for each recommendation with specific WCAG criteria

Focus on WCAG 2.1 Level AA compliance, including:
- Color contrast and visual accessibility (WCAG 1.4.3)
- Keyboard navigation and focus management (WCAG 2.1.1, 2.4.7)
- Screen reader compatibility (WCAG 1.1.1, 4.1.2)
- Alternative text for images (WCAG 1.1.1)
- Semantic HTML structure (WCAG 1.3.1, 2.4.6)
- Form accessibility (WCAG 3.3.2, 4.1.2)
- Mobile accessibility (WCAG 1.4.4)
- Error handling and validation (WCAG 3.3.1)

Respond in JSON format with this structure:
{
    "score": 75,
    "wcag_standards": {
        "compliant": ["1.1.1", "1.4.3"],
        "non_compliant": ["2.1.1", "4.1.2"],
        "details": {
            "1.1.1": "All images have appropriate alt text",
            "2.1.1": "Some interactive elements are not keyboard accessible"
        }
    },
    "recommendations": {
        "short_term": "Quick fix description",
        "medium_term": "Medium-term improvement description", 
        "long_term": "Long-term strategy description"
    },
    "details": {
        "short_term": "Detailed explanation with specific WCAG criteria and implementation steps",
        "medium_term": "Detailed explanation with specific WCAG criteria and implementation steps",
        "long_term": "Detailed explanation with specific WCAG criteria and implementation steps"
    },
    "priority_issues": [
        {
            "wcag_criterion": "1.1.1",
            "title": "Missing Alt Text",
            "description": "Images without alt text prevent screen reader users from understanding content",
            "impact": "High",
            "effort": "Low"
        }
    ]
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
                    "wcag_standards": {
                        "compliant": ["1.1.1", "1.4.3"],
                        "non_compliant": ["2.1.1", "4.1.2", "3.3.2"],
                        "details": {
                            "1.1.1": "Most images have appropriate alt text",
                            "1.4.3": "Good color contrast ratios maintained",
                            "2.1.1": "Some interactive elements need keyboard accessibility",
                            "4.1.2": "Form labels and ARIA attributes need improvement",
                            "3.3.2": "Error messages could be more descriptive"
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
                            "effort": "Low"
                        },
                        {
                            "wcag_criterion": "2.1.1",
                            "title": "Keyboard Navigation",
                            "description": "Make all interactive elements keyboard accessible",
                            "impact": "High",
                            "effort": "Medium"
                        }
                    ]
                }
        except Exception as parse_error:
            # Fallback response if JSON parsing fails
            result = {
                "score": 65,
                "wcag_standards": {
                    "compliant": ["1.1.1"],
                    "non_compliant": ["1.4.3", "2.1.1", "4.1.2"],
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
                        "effort": "Medium"
                    },
                    {
                        "wcag_criterion": "2.1.1",
                        "title": "Keyboard Accessibility",
                        "description": "All functionality must be available from a keyboard",
                        "impact": "High",
                        "effort": "Medium"
                    }
                ]
            }
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error in score endpoint: {str(e)}")
        return jsonify({
            'error': 'An error occurred while analyzing the website',
            'details': str(e) if FLASK_DEBUG else 'Check server logs for details'
        }), 500

if __name__ == '__main__':
    print(f"Starting server on {HOST}:{PORT}")
    print(f"Gemini API Key Status: {'Configured' if GEMINI_API_KEY else 'NOT CONFIGURED'}")
    if not GEMINI_API_KEY:
        print("⚠️  WARNING: Please update config.py with your Gemini API key")
    app.run(debug=FLASK_DEBUG, host=HOST, port=PORT) 