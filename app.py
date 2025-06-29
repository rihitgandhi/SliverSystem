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

if __name__ == '__main__':
    print(f"Starting server on {HOST}:{PORT}")
    print(f"Gemini API Key Status: {'Configured' if GEMINI_API_KEY else 'NOT CONFIGURED'}")
    if not GEMINI_API_KEY:
        print("⚠️  WARNING: Please update config.py with your Gemini API key")
    app.run(debug=FLASK_DEBUG, host=HOST, port=PORT) 