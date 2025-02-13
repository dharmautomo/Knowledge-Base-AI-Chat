document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('fileInput');
    const uploadBtn = document.getElementById('uploadBtn');
    const messageInput = document.getElementById('messageInput');
    const sendBtn = document.getElementById('sendBtn');
    const chatContainer = document.getElementById('chatContainer');
    const resetBtn = document.getElementById('resetBtn');
    const loadingOverlay = document.getElementById('loadingOverlay');
    const typingIndicator = document.getElementById('typingIndicator');
    const dropZone = document.getElementById('dropZone');

    // Drag and Drop handlers
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, unhighlight, false);
    });

    function highlight(e) {
        dropZone.classList.add('dragover');
    }

    function unhighlight(e) {
        dropZone.classList.remove('dragover');
    }

    dropZone.addEventListener('drop', handleDrop, false);

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;

        if (files.length > 0) {
            fileInput.files = files;
            handleFileUpload(files[0]);
        }
    }

    // Modified upload button click handler
    uploadBtn.addEventListener('click', () => {
        const file = fileInput.files[0];
        if (file) {
            handleFileUpload(file);
        }
    });

    // File input change handler
    fileInput.addEventListener('change', () => {
        const file = fileInput.files[0];
    });

    // File upload handler
    function handleFileUpload(file) {
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

        uploadFile(formData);
    }

    async function uploadFile(formData) {
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

            await response.json();
            alert('File uploaded and processed successfully!');
            fileInput.value = ''; // Clear the file input
            loadFiles(); // Refresh the files list

        } catch (error) {
            console.error('Upload error:', error);
            alert('Error uploading file: ' + error.message);
        } finally {
            hideLoading();
            uploadBtn.disabled = false;
        }
    }

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

    // Modified addMessageToChat function
    function addMessageToChat(message, role) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role === 'user' ? 'user-message' : 'ai-message'}`;

        const header = document.createElement('div');
        header.className = 'message-header';

        // Add avatar container
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';

        if (role === 'assistant') {
            const img = document.createElement('img');
            img.src = '/static/images/logo-lucky-indah-keramik.png';
            img.alt = 'Lucky Indah Keramik AI';
            img.style.backgroundColor = 'transparent';
            avatar.appendChild(img);
        } else {
            // User avatar - using initials or icon
            const icon = document.createElement('i');
            icon.className = 'bi bi-person-fill';
            avatar.appendChild(icon);
        }

        const name = document.createElement('span');
        name.textContent = role === 'user' ? 'You' : 'Lucky Indah Keramik AI';

        header.appendChild(avatar);
        header.appendChild(name);

        const content = document.createElement('div');
        content.className = 'message-content';

        if (role === 'assistant') {
            // Format AI messages with proper spacing and structure
            const formattedMessage = message
                .split('\n')
                .map(line => {
                    if (line.trim().startsWith('-') || line.trim().startsWith('*')) {
                        return line.trim();
                    }
                    if (/^\d+\./.test(line.trim())) {
                        return line.trim();
                    }
                    return line;
                })
                .join('\n')
                .replace(/\n{3,}/g, '\n\n')
                .trim();

            content.innerHTML = formattedMessage
                .split('\n')
                .map(line => {
                    const escapedLine = line
                        .replace(/&/g, '&amp;')
                        .replace(/</g, '&lt;')
                        .replace(/>/g, '&gt;');

                    if (line.trim() === '') {
                        return '<div class="paragraph-break"></div>';
                    }
                    if (line.trim().startsWith('-') || line.trim().startsWith('*')) {
                        return `<div class="bullet-point">${escapedLine}</div>`;
                    }
                    if (/^\d+\./.test(line.trim())) {
                        return `<div class="numbered-item">${escapedLine}</div>`;
                    }
                    return `<div class="text-line">${escapedLine}</div>`;
                })
                .join('');
        } else {
            // For user messages, maintain simpler formatting
            const formattedMessage = message
                .split('\n')
                .map(line => line.trim())
                .join('\n')
                .replace(/\n{3,}/g, '\n\n')
                .trim();

            content.innerHTML = formattedMessage
                .split('\n')
                .map(line => {
                    const escapedLine = line
                        .replace(/&/g, '&amp;')
                        .replace(/</g, '&lt;')
                        .replace(/>/g, '&gt;');

                    return line.trim() === '' ?
                        '<div class="paragraph-break"></div>' :
                        `<div class="text-line">${escapedLine}</div>`;
                })
                .join('');
        }

        messageDiv.appendChild(header);
        messageDiv.appendChild(content);

        let messageList = chatContainer.querySelector('.message-list');
        if (!messageList) {
            messageList = document.createElement('div');
            messageList.className = 'message-list';
            chatContainer.appendChild(messageList);
        }
        messageList.appendChild(messageDiv);
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
        const messageList = chatContainer.querySelector('.message-list');
        if (messageList) {
            messageList.innerHTML = '';
        }

        history.forEach(message => {
            addMessageToChat(message.content, message.role);
        });
    }

    async function loadFiles() {
        try {
            const response = await fetch('/files');
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Error loading files');
            }

            updateFilesList(data.files);
        } catch (error) {
            console.error('Error loading files:', error);
            alert('Error loading files. Please try again.');
        }
    }

    function updateFilesList(files) {
        const filesListDiv = document.getElementById('filesList');
        if (!filesListDiv) {
            console.error('Files list container not found');
            return;
        }

        filesListDiv.innerHTML = '';

        if (files.length === 0) {
            filesListDiv.innerHTML = '<p class="text-muted">No files uploaded yet.</p>';
            return;
        }

        files.forEach(file => {
            const fileDiv = document.createElement('div');
            fileDiv.className = 'file-item';

            const fileInfo = document.createElement('div');
            fileInfo.className = 'file-info';

            const icon = document.createElement('i');
            icon.className = 'bi bi-file-text file-icon';

            const details = document.createElement('div');
            details.className = 'file-details';

            const fileName = document.createElement('p');
            fileName.className = 'file-name';
            fileName.textContent = file.original_filename;

            const fileTime = document.createElement('p');
            fileTime.className = 'file-time';
            fileTime.textContent = new Date(file.uploaded_at).toLocaleString();

            details.appendChild(fileName);
            details.appendChild(fileTime);

            fileInfo.appendChild(icon);
            fileInfo.appendChild(details);

            const deleteBtn = document.createElement('button');
            deleteBtn.className = 'delete-btn';
            deleteBtn.innerHTML = '<i class="bi bi-trash"></i>';
            deleteBtn.onclick = () => deleteFile(file.id);

            fileDiv.appendChild(fileInfo);
            fileDiv.appendChild(deleteBtn);
            filesListDiv.appendChild(fileDiv);
        });
    }

    async function deleteFile(fileId) {
        if (!confirm('Are you sure you want to delete this file?')) {
            return;
        }

        try {
            const response = await fetch(`/files/${fileId}`, {
                method: 'DELETE'
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Error deleting file');
            }

            loadFiles(); // Refresh the files list
        } catch (error) {
            console.error('Error deleting file:', error);
            alert('Error deleting file. Please try again.');
        }
    }

    loadFiles(); // Load files when page loads
    loadChatHistory(); //load initial chat history.
});