document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('fileInput');
    const uploadBtn = document.getElementById('uploadBtn');
    const messageInput = document.getElementById('messageInput');
    const sendBtn = document.getElementById('sendBtn');
    const chatContainer = document.getElementById('chatContainer');
    const loadingModal = new bootstrap.Modal(document.getElementById('loadingModal'));

    // Load chat history on page load
    loadChatHistory();

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
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
            
            if (response.ok) {
                messageInput.value = data.content;
            } else {
                throw new Error(data.error || 'Error uploading file');
            }
        } catch (error) {
            alert('Error: ' + error.message);
        } finally {
            loadingModal.hide();
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

        try {
            loadingModal.show();
            messageInput.value = '';

            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ message })
            });

            const data = await response.json();
            
            if (response.ok) {
                updateChatDisplay(data.history);
            } else {
                throw new Error(data.error || 'Error sending message');
            }
        } catch (error) {
            alert('Error: ' + error.message);
        } finally {
            loadingModal.hide();
        }
    }

    async function loadChatHistory() {
        try {
            const response = await fetch('/history');
            const data = await response.json();
            
            if (response.ok) {
                updateChatDisplay(data.history);
            }
        } catch (error) {
            console.error('Error loading chat history:', error);
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
