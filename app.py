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
2. Short-term recommendations (quick fixes, 1-2 weeks)
3. Medium-term recommendations (structural changes, 1-3 months)
4. Long-term recommendations (comprehensive improvements, 3-12 months)
5. Detailed explanations for each recommendation

Focus on WCAG 2.1 Level AA compliance, including:
- Color contrast and visual accessibility
- Keyboard navigation and focus management
- Screen reader compatibility
- Alternative text for images
- Semantic HTML structure
- Form accessibility
- Mobile accessibility

Respond in JSON format with this structure:
{
    "score": 75,
    "recommendations": {
        "short_term": "Quick fix description",
        "medium_term": "Medium-term improvement description", 
        "long_term": "Long-term strategy description"
    },
    "details": {
        "short_term": "Detailed explanation of short-term fixes",
        "medium_term": "Detailed explanation of medium-term improvements",
        "long_term": "Detailed explanation of long-term strategy"
    }
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
                    "recommendations": {
                        "short_term": "Unable to parse specific recommendations. Please check the website manually.",
                        "medium_term": "Consider implementing WCAG 2.1 Level AA guidelines.",
                        "long_term": "Conduct a comprehensive accessibility audit with user testing."
                    },
                    "details": {
                        "short_term": "The AI analysis encountered an issue. Please manually review the website for basic accessibility issues.",
                        "medium_term": "Focus on implementing standard accessibility practices like proper heading structure, alt text, and keyboard navigation.",
                        "long_term": "Plan for a complete accessibility overhaul with professional guidance and user feedback."
                    }
                }
        except Exception as parse_error:
            # Fallback response if JSON parsing fails
            result = {
                "score": 65,
                "recommendations": {
                    "short_term": "Add alt text to images and ensure proper color contrast.",
                    "medium_term": "Implement keyboard navigation and ARIA labels.",
                    "long_term": "Conduct full accessibility audit and user testing."
                },
                "details": {
                    "short_term": "Basic accessibility improvements that can be implemented quickly.",
                    "medium_term": "Structural improvements that require more planning and development time.",
                    "long_term": "Comprehensive accessibility strategy with ongoing monitoring and improvement."
                }
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