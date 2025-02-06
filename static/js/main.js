document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('fileInput');
    const uploadBtn = document.getElementById('uploadBtn');
    const messageInput = document.getElementById('messageInput');
    const sendBtn = document.getElementById('sendBtn');
    const chatContainer = document.getElementById('chatContainer');
    const resetBtn = document.getElementById('resetBtn');
    const loadingModal = new bootstrap.Modal(document.getElementById('loadingModal'));

    // Load chat history on page load
    loadChatHistory();

    // Reset Chat Handler
    resetBtn.addEventListener('click', async () => {
        if (!confirm('Are you sure you want to reset the chat? This will clear all messages.')) {
            return;
        }

        try {
            loadingModal.show();
            resetBtn.disabled = true;
            messageInput.disabled = true;
            sendBtn.disabled = true;

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

            // Clear the chat container
            chatContainer.innerHTML = '';
            messageInput.value = '';

        } catch (error) {
            console.error('Reset error:', error);
            alert('Error resetting chat: ' + error.message);
        } finally {
            loadingModal.hide();
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

        if (!file.name.toLowerCase().endsWith('.txt')) {
            alert('Please upload only TXT files.');
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        try {
            loadingModal.show();
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
            loadingModal.hide();
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

        const originalMessage = message;
        messageInput.value = '';
        sendBtn.disabled = true;

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

            updateChatDisplay(data.history);

        } catch (error) {
            console.error('Chat error:', error);
            alert('Error processing message: ' + error.message);
            messageInput.value = originalMessage;
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
        chatContainer.innerHTML = '';

        history.forEach(message => {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${message.role === 'user' ? 'user-message' : 'ai-message'}`;

            const header = document.createElement('div');
            header.className = 'message-header';
            header.textContent = message.role === 'user' ? 'You' : 'AI';

            const content = document.createElement('div');
            content.className = 'message-content';
            content.textContent = message.content;

            messageDiv.appendChild(header);
            messageDiv.appendChild(content);
            chatContainer.appendChild(messageDiv);
        });

        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
});