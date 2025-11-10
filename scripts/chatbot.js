class AccessibilityChatbot {
    constructor() {
        this.conversationId = 'accessibility-chat-' + Date.now();
        this.isLoading = false;
        this.progressInterval = null;
        this.currentMessageIndex = 0;
        
        // Progress messages for AI thinking
        this.thinkingMessages = [
            'Processing your question...',
            'Analyzing accessibility context...',
            'Consulting WCAG guidelines...',
            'Formulating detailed response...',
            'Reviewing best practices...',
            'Preparing recommendations...'
        ];
        
        // Backend URL Configuration
        // For local development: http://localhost:5000
        // For production: Update this to your deployed backend URL
        // Example: https://sliversystem-backend.onrender.com
        this.backendUrl = this.getBackendUrl();
        
        this.init();
    }

    getBackendUrl() {
        // Priority order for selecting backend URL:
        // 1. A <meta name="backend-url" content="https://..."> in the page head (allows override)
        // 2. If hosted on GitHub Pages (hostname contains github.io) => use Railway/default production URL
        // 3. If running on localhost/127.0.0.1 => use local backend
        // 4. Fallback to local backend

        // 1) meta tag override
        try {
            const meta = document.querySelector('meta[name="backend-url"]');
            if (meta && meta.content) {
                console.log('🌐 Using backend URL from meta tag:', meta.content);
                return meta.content;
            }
        } catch (e) {
            // ignore
        }

        const host = window.location.hostname || '';
        const isLocal = host === 'localhost' || host === '127.0.0.1' || host === '';
        const isGithubPages = host.includes('github.io');

        if (isGithubPages) {
            // If this frontend is served via GitHub Pages, point the frontend to the Railway backend.
            // This is set to the production Railway backend for this project.
            const railwayUrl = 'https://sliver-system-backend-production-9067.up.railway.app';
            console.log('🌐 Detected GitHub Pages host — using Railway backend URL:', railwayUrl);
            return railwayUrl;
        }

        if (isLocal) {
            const url = 'http://localhost:5000';
            console.log('🏠 Using local backend URL:', url);
            return url;
        }

        // Default fallback
        const fallback = 'http://localhost:5000';
        console.log('⚠️ Falling back to backend URL:', fallback);
        return fallback;
    }

    init() {
        console.log('Chatbot init() called');
        const messagesContainer = document.getElementById('chat-messages');
        if (messagesContainer && messagesContainer.children.length === 0) {
            // Insert initial bot message if empty
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message bot-message';
            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content';
            contentDiv.innerHTML = "<p>Hello! I'm your accessibility assistant. Ask me anything about web accessibility, WCAG, or inclusive design.</p>";
            messageDiv.appendChild(contentDiv);
            messagesContainer.appendChild(messageDiv);
        }
        this.bindEvents();
        this.loadChatHistory();
    }

    createChatInterface() {
        // Prefer #ai-chatbox (for Home tab), fallback to #ai (for AI in Accessibility tab)
        const aiSection = document.getElementById('ai-chatbox') || document.getElementById('ai');
        if (!aiSection) return;

        // Create chatbot container
        const chatbotContainer = document.createElement('div');
        chatbotContainer.className = 'chatbot-container';
        chatbotContainer.innerHTML = `
            <div class="chatbot-header">
                <h3>🤖 Accessibility Assistant</h3>
                <p>Ask me anything about web accessibility, WCAG guidelines, or assistive technologies!</p>
            </div>
            <div class="chat-messages" id="chat-messages">
                <div class="message bot-message">
                    <div class="message-content">
                        <p>Hello! I'm your accessibility assistant. I can help you with:</p>
                        <ul>
                            <li>WCAG guidelines and compliance</li>
                            <li>Assistive technologies</li>
                            <li>Inclusive design practices</li>
                            <li>Accessibility testing</li>
                            <li>And much more!</li>
                        </ul>
                        <p>What would you like to know about accessibility?</p>
                    </div>
                </div>
            </div>
            <div class="chat-input-container">
                <div class="input-wrapper">
                    <input type="text" id="chat-input" placeholder="Type your question here..." maxlength="500">
                    <button id="send-button" class="send-button">
                        <span class="send-icon">📤</span>
                    </button>
                </div>
                <div class="input-actions">
                    <button class="clear-chat-btn" onclick="chatbot.clearChat()">Clear Chat</button>
                    <button class="example-questions-btn" onclick="chatbot.showExampleQuestions()">Example Questions</button>
                </div>
            </div>
            <div class="example-questions" id="example-questions" style="display: none;">
                <h4>Try asking:</h4>
                <div class="question-chips">
                    <button class="question-chip" onclick="chatbot.askQuestion('What are the main WCAG principles?')">What are the main WCAG principles?</button>
                    <button class="question-chip" onclick="chatbot.askQuestion('How do I make a website keyboard accessible?')">How do I make a website keyboard accessible?</button>
                    <button class="question-chip" onclick="chatbot.askQuestion('What is alt text and why is it important?')">What is alt text and why is it important?</button>
                    <button class="question-chip" onclick="chatbot.askQuestion('How do I test my website for accessibility?')">How do I test my website for accessibility?</button>
                    <button class="question-chip" onclick="chatbot.askQuestion('What assistive technologies are commonly used?')">What assistive technologies are commonly used?</button>
                </div>
            </div>
        `;

        aiSection.appendChild(chatbotContainer);
    }

    bindEvents() {
        console.log('Binding events...');
        const input = document.getElementById('chat-input');
        const sendButton = document.getElementById('send-button');
        
        console.log('Input element:', input);
        console.log('Send button element:', sendButton);

        if (input && sendButton) {
            console.log('Both elements found, binding events');
            // Send message on Enter key
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });

            // Send message on button click
            sendButton.addEventListener('click', () => {
                console.log('Send button clicked');
                this.sendMessage();
            });

            // Auto-resize input
            input.addEventListener('input', () => {
                this.adjustInputHeight();
            });
        } else {
            console.error('Input or send button not found!');
        }
    }

    async sendMessage() {
        const input = document.getElementById('chat-input');
        const message = input.value.trim();

        if (!message || this.isLoading) return;

        // Add user message to chat
        this.addMessage(message, 'user');
        input.value = '';
        this.adjustInputHeight();

        // Show loading indicator
        this.showLoading();

        console.log('📤 Sending message to:', `${this.backendUrl}/api/chat`);
        console.log('📝 Message:', message);

        try {
            const response = await fetch(`${this.backendUrl}/api/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    conversation_id: this.conversationId
                })
            });

            console.log('📥 Response status:', response.status);
            console.log('📥 Response headers:', Object.fromEntries(response.headers.entries()));

            const data = await response.json();
            console.log('📥 Response data:', data);

            if (response.ok) {
                this.addMessage(data.response, 'bot');
                this.saveChatHistory();
            } else {
                console.error('❌ API Error:', data);
                this.addMessage('Sorry, I encountered an error. Please try again.', 'bot error');
            }
        } catch (error) {
            console.error('❌ Chat error:', error);
            console.error('❌ Error details:', {
                name: error.name,
                message: error.message,
                stack: error.stack
            });
            this.addMessage('Sorry, I'm having trouble connecting to the server. Please check if the Python backend is running.', 'bot error');
        }

        this.hideLoading();
    }

    addMessage(content, type) {
        const messagesContainer = document.getElementById('chat-messages');
        if (!messagesContainer) return;

        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        // Convert line breaks to <br> tags
        const formattedContent = content.replace(/\n/g, '<br>');
        contentDiv.innerHTML = formattedContent;
        
        messageDiv.appendChild(contentDiv);
        messagesContainer.appendChild(messageDiv);

        // Scroll to bottom
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    showLoading() {
        this.isLoading = true;
        const sendButton = document.getElementById('send-button');
        if (sendButton) {
            this.currentMessageIndex = 0;
            sendButton.innerHTML = `<span class="loading-spinner">⏳</span> <span class="loading-text">${this.thinkingMessages[0]}</span>`;
            sendButton.disabled = true;
            
            // Start rotating progress messages every 5 seconds
            this.progressInterval = setInterval(() => {
                this.currentMessageIndex = (this.currentMessageIndex + 1) % this.thinkingMessages.length;
                const loadingText = sendButton.querySelector('.loading-text');
                if (loadingText) {
                    loadingText.textContent = this.thinkingMessages[this.currentMessageIndex];
                }
            }, 5000);
        }
    }

    hideLoading() {
        this.isLoading = false;
        
        // Clear progress interval
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
            this.progressInterval = null;
        }
        
        const sendButton = document.getElementById('send-button');
        if (sendButton) {
            sendButton.innerHTML = '<span class="send-icon">📤</span>';
            sendButton.disabled = false;
        }
    }

    adjustInputHeight() {
        const input = document.getElementById('chat-input');
        if (input) {
            input.style.height = 'auto';
            input.style.height = Math.min(input.scrollHeight, 120) + 'px';
        }
    }

    clearChat() {
        const messagesContainer = document.getElementById('chat-messages');
        if (messagesContainer) {
            // Keep only the initial bot message
            const initialMessage = messagesContainer.querySelector('.bot-message');
            messagesContainer.innerHTML = '';
            if (initialMessage) {
                messagesContainer.appendChild(initialMessage);
            }
        }
        this.conversationId = 'accessibility-chat-' + Date.now();
        localStorage.removeItem('accessibility-chat-history');
    }

    showExampleQuestions() {
        const exampleQuestions = document.getElementById('example-questions');
        if (exampleQuestions) {
            exampleQuestions.style.display = exampleQuestions.style.display === 'none' ? 'block' : 'none';
        }
    }

    askQuestion(question) {
        const input = document.getElementById('chat-input');
        if (input) {
            input.value = question;
            this.sendMessage();
        }
    }

    saveChatHistory() {
        const messagesContainer = document.getElementById('chat-messages');
        if (messagesContainer) {
            const messages = Array.from(messagesContainer.children).map(msg => ({
                type: msg.classList.contains('user-message') ? 'user' : 'bot',
                content: msg.querySelector('.message-content').textContent
            }));
            localStorage.setItem('accessibility-chat-history', JSON.stringify(messages));
        }
    }

    loadChatHistory() {
        const savedHistory = localStorage.getItem('accessibility-chat-history');
        if (savedHistory) {
            try {
                const messages = JSON.parse(savedHistory);
                const messagesContainer = document.getElementById('chat-messages');
                if (messagesContainer && messages.length > 1) {
                    // Clear initial message and load saved history
                    messagesContainer.innerHTML = '';
                    messages.forEach(msg => {
                        this.addMessage(msg.content, msg.type);
                    });
                }
            } catch (error) {
                console.error('Error loading chat history:', error);
            }
        }
    }
}

// Initialize chatbot when AI tab is loaded
function initChatbot() {
    if (typeof chatbot === 'undefined') {
        window.chatbot = new AccessibilityChatbot();
    }
}

// Initialize chatbot when the page loads
document.addEventListener('DOMContentLoaded', () => {
    // Initialize chatbot after a short delay to ensure AI section is loaded
    setTimeout(initChatbot, 1000);
}); 