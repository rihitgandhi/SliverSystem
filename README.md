# Computer Accessibility Website with AI Chatbot

A comprehensive website about computer accessibility featuring an AI-powered chatbot for accessibility questions.

## 🌟 Features

- **Educational Content**: Lessons, blogs, and resources about computer accessibility
- **AI Chatbot**: Powered by Google Gemini API for accessibility questions
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Accessibility Features**: Built with WCAG 2.1 Level AA compliance
- **Interactive Lessons**: Step-by-step guides for designers and navigators

## 🚀 Quick Start

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/SliverSystem.git
   cd SliverSystem
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure API Key**
   - Edit `config.py`
   - Replace `'your-api-key-here'` with your Google Gemini API key
   - Get a free API key from [Google AI Studio](https://makersuite.google.com/app/apikey)

4. **Run the development server**
   ```bash
   python app.py
   ```

5. **Open in browser**
   - Main site: http://localhost:5000
   - Chatbot: http://localhost:5000/chat.html

### GitHub Pages Deployment

**Option A: Static Version (Recommended for GitHub Pages)**
1. The static files are ready for GitHub Pages
2. Push to GitHub and enable Pages in repository settings
3. Update the chatbot backend URL (see configuration section)

**Option B: Full Stack with External Backend**
1. Deploy the Python backend to a service like Render, Railway, or Heroku
2. Update the backend URL in `scripts/chatbot.js`
3. Push static files to GitHub Pages

## 🔧 Configuration

### API Keys

**For Local Development:**
```python
# config.py
GEMINI_API_KEY = 'your-actual-gemini-api-key'
```

**For Production:**
- Use environment variables
- Never commit API keys to version control

### Backend URL Configuration

**Local Development:**
```javascript
// scripts/chatbot.js
this.backendUrl = 'http://localhost:5000';
```

**Production (GitHub Pages):**
```javascript
// scripts/chatbot.js
this.backendUrl = 'https://your-backend-url.com';
```

## 📁 Project Structure

```
SliverSystem/
├── app.py                 # Flask backend server
├── config.py             # Configuration and API keys
├── requirements.txt      # Python dependencies
├── index.html           # Main website
├── chat.html            # Chatbot page
├── css/
│   └── main.css         # Styles
├── scripts/
│   └── chatbot.js       # Chatbot functionality
├── images/              # Website images
└── Wind power/          # Educational content
```

## 🌐 Deployment Options

### GitHub Pages (Static Files Only)

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Initial commit"
   git push origin main
   ```

2. **Enable GitHub Pages**
   - Go to repository Settings → Pages
   - Source: Deploy from a branch
   - Branch: main
   - Folder: / (root)

3. **Update Backend URL**
   - Edit `scripts/chatbot.js`
   - Change `backendUrl` to your deployed backend URL

### Full Stack Deployment

**Backend (Python/Flask):**
- **Render**: Free tier available
- **Railway**: Easy deployment
- **Heroku**: Requires credit card
- **PythonAnywhere**: Free tier available

**Frontend (Static Files):**
- **GitHub Pages**: Free and easy
- **Netlify**: Free tier with more features
- **Vercel**: Free tier available

## 🔒 Security Notes

- Never commit API keys to version control
- Use environment variables in production
- Consider rate limiting for production deployments
- The current setup is for development/testing

## 🛠️ Troubleshooting

### Common Issues

1. **"Connection refused" error**
   - Make sure the Python backend is running
   - Check if the backend URL is correct

2. **"API key invalid" error**
   - Verify your Gemini API key in `config.py`
   - Check if the API key has proper permissions

3. **CORS errors**
   - The backend has CORS enabled
   - Check browser console for specific errors

4. **GitHub Pages not loading**
   - Ensure all files are in the root directory
   - Check repository settings for Pages configuration

### Testing

```bash
# Test backend health
curl http://localhost:5000/api/health

# Test chatbot API
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "conversation_id": "test"}'
```

## 📚 API Documentation

### Endpoints

- `GET /` - Main website
- `GET /chat.html` - Chatbot page
- `POST /api/chat` - Send message to chatbot
- `GET /api/health` - Health check

### Chat API

**Request:**
```json
{
  "message": "What are WCAG guidelines?",
  "conversation_id": "user-123"
}
```

**Response:**
```json
{
  "response": "WCAG (Web Content Accessibility Guidelines) are...",
  "conversation_id": "user-123",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 🆘 Support

For issues and questions:
- Check the troubleshooting section
- Open an issue on GitHub
- Review the API documentation

---

**Made with ❤️ for accessibility and inclusive design**
