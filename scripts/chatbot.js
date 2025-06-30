class AccessibilityChatbot {
    constructor() {
        this.conversationId = 'accessibility-chat-' + Date.now();
        this.isLoading = false;
        
        // Backend URL Configuration
        // For local development: http://localhost:5000
        // For production: Update this to your deployed backend URL
        // Example: https://sliversystem-backend.onrender.com
        this.backendUrl = this.getBackendUrl();
        
        this.init();
    }

    getBackendUrl() {
        // Check if we're on GitHub Pages (production)
        if (window.location.hostname.includes('github.io')) {
            // Production: Update this URL to your deployed backend
            const url = 'https://sliversystem-backend.onrender.com';
            console.log('🌐 Using production backend URL:', url);
            return url;
        } else {
            // Local development
            const url = 'http://localhost:5000';
            console.log('🏠 Using local backend URL:', url);
            return url;
        }
    }

    init() {
        console.log('Chatbot init() called');
        // Check if we're on the chat page (has existing HTML structure)
        const existingChatMessages = document.getElementById('chat-messages');
        console.log('Existing chat messages element:', existingChatMessages);
        
        if (existingChatMessages) {
            // We're on chat.html - use existing structure
            console.log('Using existing HTML structure');
            this.bindEvents();
            this.loadChatHistory();
        } else {
            // We're on index.html - create interface dynamically
            console.log('Creating interface dynamically');
            this.createChatInterface();
            this.bindEvents();
            this.loadChatHistory();
        }
    }

    createChatInterface() {
        const aiSection = document.getElementById('ai');
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

        // Insert chatbot after the existing AI content
        const existingContent = aiSection.querySelector('.my-ai-card');
        if (existingContent) {
            existingContent.parentNode.insertBefore(chatbotContainer, existingContent.nextSibling);
        } else {
            aiSection.appendChild(chatbotContainer);
        }
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
            this.addMessage('Sorry, I\'m having trouble connecting to the server. Please check if the Python backend is running.', 'bot error');
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
            sendButton.innerHTML = '<span class="loading-spinner">⏳</span>';
            sendButton.disabled = true;
        }
    }

    hideLoading() {
        this.isLoading = false;
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