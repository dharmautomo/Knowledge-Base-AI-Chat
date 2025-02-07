document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('fileInput');
    const uploadBtn = document.getElementById('uploadBtn');
    const messageInput = document.getElementById('messageInput');
    const sendBtn = document.getElementById('sendBtn');
    const chatContainer = document.getElementById('chatContainer');
    const resetBtn = document.getElementById('resetBtn');
    const loadingOverlay = document.getElementById('loadingOverlay');
    const typingIndicator = document.getElementById('typingIndicator');

    // Load chat history on page load
    loadChatHistory();

    function showLoading() {
        loadingOverlay.classList.add('active');
        document.body.style.overflow = 'hidden';
    }

    function hideLoading() {
        loadingOverlay.classList.remove('active');
        document.body.style.overflow = '';
    }

    function showTypingIndicator() {
        typingIndicator.style.display = 'block';
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    function hideTypingIndicator() {
        typingIndicator.style.display = 'none';
    }

    function addMessageToChat(message, role) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role === 'user' ? 'user-message' : 'ai-message'}`;

        const header = document.createElement('div');
        header.className = 'message-header';
        header.textContent = role === 'user' ? 'You' : 'AI';

        const content = document.createElement('div');
        content.className = 'message-content';
        content.textContent = message;

        messageDiv.appendChild(header);
        messageDiv.appendChild(content);

        // Insert before typing indicator
        chatContainer.insertBefore(messageDiv, typingIndicator);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    // Reset Chat Handler
    resetBtn.addEventListener('click', async () => {
        if (!confirm('Are you sure you want to reset the chat? This will clear all messages.')) {
            return;
        }

        try {
            resetBtn.disabled = true;
            messageInput.disabled = true;
            sendBtn.disabled = true;
            showLoading();

            const response = await fetch('/reset', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to reset chat');
            }

            chatContainer.innerHTML = '';
            messageInput.value = '';

            // Re-add typing indicator after clearing
            chatContainer.appendChild(typingIndicator);

        } catch (error) {
            console.error('Reset error:', error);
            alert('Error resetting chat: ' + error.message);
        } finally {
            hideLoading();
            resetBtn.disabled = false;
            messageInput.disabled = false;
            sendBtn.disabled = false;
        }
    });

    // File Upload Handler
    uploadBtn.addEventListener('click', async () => {
        const file = fileInput.files[0];
        if (!file) {
            alert('Please select a file first.');
            return;
        }

        const fileExtension = file.name.toLowerCase().split('.').pop();
        if (!['txt', 'pdf'].includes(fileExtension)) {
            alert('Please upload only TXT or PDF files.');
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        try {
            showLoading();
            uploadBtn.disabled = true;

            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Error uploading file');
            }

            const data = await response.json();
            messageInput.value = data.content;

        } catch (error) {
            console.error('Upload error:', error);
            alert('Error uploading file: ' + error.message);
        } finally {
            hideLoading();
            uploadBtn.disabled = false;
            fileInput.value = '';
        }
    });

    // Send Message Handler
    sendBtn.addEventListener('click', sendMessage);
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    async function sendMessage() {
        const message = messageInput.value.trim();
        if (!message) return;

        messageInput.value = '';
        sendBtn.disabled = true;

        // Immediately add user message to chat
        addMessageToChat(message, 'user');
        showTypingIndicator();

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ message })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Error sending message');
            }

            hideTypingIndicator();
            updateChatDisplay(data.history);

        } catch (error) {
            console.error('Chat error:', error);
            hideTypingIndicator();
            alert('Error processing message: ' + error.message);
        } finally {
            sendBtn.disabled = false;
        }
    }

    async function loadChatHistory() {
        try {
            const response = await fetch('/history');
            const data = await response.json();

            if (response.ok) {
                updateChatDisplay(data.history);
            } else {
                throw new Error(data.error || 'Error loading history');
            }
        } catch (error) {
            console.error('Error loading chat history:', error);
            alert('Error loading chat history. Please refresh the page.');
        }
    }

    function updateChatDisplay(history) {
        // Clear all messages but keep typing indicator
        while (chatContainer.firstChild && chatContainer.firstChild !== typingIndicator) {
            chatContainer.removeChild(chatContainer.firstChild);
        }

        history.forEach(message => {
            addMessageToChat(message.content, message.role);
        });
    }
});