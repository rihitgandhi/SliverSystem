# Accessibility Chatbot Setup

This chatbot provides AI-powered assistance for accessibility questions and WCAG guidelines.

## Setup Instructions

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Key

Edit the `config.py` file and replace `'your-api-key-here'` with your actual OpenAI API key:

```python
OPENAI_API_KEY = 'sk-your-actual-api-key-here'
```

### 3. Run the Backend Server

```bash
python app.py
```

The server will start on `http://localhost:5000`

### 4. Test the Chatbot

1. Open your website in a browser
2. Navigate to the "AI in Accessibility" tab
3. The chatbot will appear below the existing AI content
4. Start asking questions about accessibility!

## Features

- **Real-time Chat**: Ask questions about accessibility and get instant responses
- **Context Awareness**: The chatbot remembers conversation history
- **Accessibility Focused**: Specialized in WCAG guidelines and assistive technologies
- **Example Questions**: Quick access to common accessibility questions
- **Responsive Design**: Works on desktop and mobile devices

## API Endpoints

- `POST /api/chat` - Send a message and get a response
- `GET /api/health` - Check if the server is running

## Example Usage

```javascript
// Send a message to the chatbot
fetch('http://localhost:5000/api/chat', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        message: 'What are the main WCAG principles?',
        conversation_id: 'user-123'
    })
})
.then(response => response.json())
.then(data => console.log(data.response));
```

## Deployment Notes

### For GitHub Pages

Since GitHub Pages only supports static content, you'll need to:

1. **Deploy the Python backend separately** (e.g., Heroku, Railway, or Render)
2. **Update the backend URL** in `scripts/chatbot.js` to point to your deployed backend
3. **Push the static files** to GitHub Pages

### For Local Development

1. Run the Python backend locally
2. The chatbot will automatically connect to `http://localhost:5000`
3. Make sure CORS is enabled (already configured in the code)

## Troubleshooting

### Common Issues

1. **"Connection refused" error**: Make sure the Python backend is running
2. **"API key invalid" error**: Check your OpenAI API key in `config.py`
3. **CORS errors**: The backend already has CORS enabled, but check your browser console

### Testing the Backend

```bash
# Test the health endpoint
curl http://localhost:5000/api/health

# Test the chat endpoint
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "conversation_id": "test"}'
```

## Security Notes

- Never commit your actual API key to version control
- Use environment variables in production
- Consider rate limiting for production deployments
- The current setup is for development/testing only

## Customization

You can customize the chatbot by:

1. **Modifying the system message** in `app.py` to change the bot's personality
2. **Adjusting the model parameters** (temperature, max_tokens) for different response styles
3. **Adding new features** like file uploads or voice input
4. **Styling the interface** by modifying the CSS in `css/main.css` 