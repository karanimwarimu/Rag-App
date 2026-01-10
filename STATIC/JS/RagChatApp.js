// DOM elements
const messagesContainer = document.getElementById('messages-container');
const chatForm = document.getElementById('chat-form');
const messageInput = document.getElementById('message-input');
const imageUpload = document.getElementById('image-upload');
const imagePreviewContainer = document.getElementById('image-preview-container');
const imagePreview = document.getElementById('image-preview');
const imageFileName = document.getElementById('image-file-name');
const clearImageBtn = document.getElementById('clear-image-btn');
const errorModal = document.getElementById('error-modal');
const errorMessage = document.getElementById('error-message');
const closeModalBtn = document.getElementById('close-modal-btn');
const reloadBtn = document.getElementById('reload-btn');
const reloadOverlay = document.getElementById('reload-overlay');

// State variables
let messages = [];
let isThinking = false;
let base64Image = null;

// Function to show a custom error modal
const showErrorModal = (message) => {
    errorMessage.textContent = message;
    errorModal.classList.remove('hidden');
};

// Event listener to close the error modal
closeModalBtn.addEventListener('click', () => {
    errorModal.classList.add('hidden');
    // After the modal closes, show a prompt in the chat
    const promptMessage = {
        id: Date.now(),
        text: "An error occurred, but you can continue chatting. To start fresh, just reload the page.",
        sender: 'ai',
        timestamp: new Date().toLocaleTimeString(),
    };
    renderMessage(promptMessage);
    messages.push(promptMessage);
});

// Event listener to reload the page
reloadBtn.addEventListener('click', () => {
    // Show the reloading animation overlay before reloading
    reloadOverlay.classList.remove('hidden');
    location.reload();
});

// Function to scroll to the bottom of the messages container
const scrollToBottom = () => {
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
};

// Function to render a single message (user or AI)
const renderMessage = (message) => {
    const messageDiv = document.createElement('div');
    messageDiv.className = `flex flex-col ${message.sender === 'user' ? 'items-end' : 'items-start'}`;
    
    // Set message bubble styling based on sender
    const bubbleClass = message.sender === 'user'
        ? 'bg-pink-50 text-gray-800 rounded-br-none'
        : 'bg-stone-200 text-gray-800 rounded-bl-none';

    messageDiv.innerHTML = `
        <div class="p-3 rounded-2xl shadow-md ${bubbleClass} chat-bubble-fit">
            ${message.image ? `<img src="${message.image}" alt="User uploaded" class="rounded-lg mb-2 max-h-40 w-auto object-cover" />` : ''}
            <p class="break-words">${message.text}</p>
            <div class="flex justify-between items-center mt-2">
                <span class="block text-xs text-gray-500">
                    ${message.timestamp}
                </span>
            </div>
        </div>
        ${message.sender === 'user' ? `
        <div class="flex items-center space-x-2 mt-1 text-xs text-gray-400 cursor-pointer hover:text-white">
            <button class="edit-btn px-2 py-1 rounded-full text-xs font-semibold" data-id="${message.id}">Edit</button>
            <button class="copy-btn px-2 py-1 rounded-full text-xs font-semibold" data-id="${message.id}">Copy</button>
        </div>
        ` : `
        <div class="mt-1 text-xs text-gray-400 cursor-pointer hover:text-white text-left">
            <button class="copy-btn px-2 py-1 rounded-full text-xs font-semibold" data-id="${message.id}">Copy</button>
        </div>
        `}
    `;
    messagesContainer.appendChild(messageDiv);

    // Add event listeners for the copy and edit buttons
    const copyBtn = messageDiv.querySelector('.copy-btn');
    if (copyBtn) {
        copyBtn.addEventListener('click', () => handleCopy(message.text, message.id, copyBtn));
    }
    const editBtn = messageDiv.querySelector('.edit-btn');
    if (editBtn) {
        editBtn.addEventListener('click', () => handleEdit(message.text, message.id));
    }
};

// Function to show the 'thinking' bubble
const showThinkingBubble = () => {
    isThinking = true;
    const thinkingDiv = document.createElement('div');
    thinkingDiv.id = 'thinking-bubble';
    thinkingDiv.className = 'flex justify-start';
    thinkingDiv.innerHTML = `
        <div class="p-3 rounded-2xl chat-bubble-fit bg-stone-200 rounded-bl-none">
            <div class="flex space-x-1 animate-bounce-dots">
                <div class="h-2 w-2 bg-gray-800 rounded-full"></div>
                <div class="h-2 w-2 bg-gray-800 rounded-full"></div>
                <div class="h-2 w-2 bg-gray-800 rounded-full"></div>
            </div>
        </div>
    `;
    messagesContainer.appendChild(thinkingDiv);
    scrollToBottom();
};

// Function to remove the 'thinking' bubble
const hideThinkingBubble = () => {
    isThinking = false;
    const thinkingDiv = document.getElementById('thinking-bubble');
    if (thinkingDiv) {
        thinkingDiv.remove();
    }
};

// Handler for copying message text to the clipboard
const handleCopy = (text, id, button) => {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    document.body.appendChild(textarea);
    textarea.select();
    try {
        // Use the older, more compatible API for iframes
        document.execCommand('copy');
        button.textContent = 'Copied!';
        setTimeout(() => button.textContent = 'Copy', 1000);
    } catch (err) {
        console.error('Failed to copy text: ', err);
        showErrorModal('Failed to copy text. Please try again.');
    }
    document.body.removeChild(textarea);
};

// Handler for editing a message
const handleEdit = (text, id) => {
    messageInput.value = text;
    // You can add more complex logic here, like removing the old message
    // or highlighting the message being edited. For now, we'll just populate the input.
};

// Function to call the FastAPI server for a text and image response
const generateFastAPIImageResponse = async (userPrompt, base64ImageData) => {
    showThinkingBubble();
    let retries = 0;
    const maxRetries = 3;
    const initialDelay = 1000;
    
    const payload = {
        prompt: userPrompt,
        imageData: base64ImageData
    };

    // ----- FASTAPI INTEGRATION: Plug your API route here -----
    // This is a placeholder. You need to replace this with your actual endpoint URL.
    const apiUrl = 'http://192.168.0.100:8000/chat-with-image';

    while (retries < maxRetries) {
        try {
            const response = await fetch(apiUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                throw new Error(`API call failed with status: ${response.status}`);
            }

            const result = await response.json();
            // Assuming your FastAPI server returns a JSON object with a 'text' field
            const generatedText = result.text;

            if (generatedText) {
                const aiMessage = {
                    id: Date.now(),
                    text: generatedText,
                    sender: 'ai',
                    timestamp: new Date().toLocaleTimeString(),
                };
                messages.push(aiMessage);
                renderMessage(aiMessage);
                hideThinkingBubble();
                // Clear image state after successful response
                base64Image = null;
                imagePreviewContainer.classList.add('hidden');
                imagePreviewContainer.classList.remove('flex');
                imageUpload.value = null;
                return;
            } else {
                throw new Error('No content returned from FastAPI server');
            }
        } catch (error) {
            console.error('Error generating AI response:', error);
            retries++;
            if (retries < maxRetries) {
                // Use exponential backoff
                const delay = initialDelay * Math.pow(2, retries - 1);
                await new Promise(res => setTimeout(res, delay));
            } else {
                // Fallback message after max retries
                hideThinkingBubble();
                showErrorModal("Sorry, I'm having trouble connecting right now. Please try again later.");
                base64Image = null;
                imagePreviewContainer.classList.add('hidden');
                imagePreviewContainer.classList.remove('flex');
                imageUpload.value = null;
            }
        }
    }
};
// Function to call the FastAPI server for a text-only response
const generateFastAPIResponse = async (userPrompt, sendBtn, messageInput) => {
    showThinkingBubble();
    let retries = 0;
    const maxRetries = 3;
    const initialDelay = 1000;

    const payload = { prompt: userPrompt };
    const apiUrl = 'http://192.168.100.45:5000/send_prompt';

    try {
        while (retries < maxRetries) {
            try {
                const response = await fetch( apiUrl, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                if (!response.ok) {
                    throw new Error(`API call failed with status: ${response.status}`);
                }

                const result = await response.json();
                const generatedText = result.RESULT;

                if (generatedText) {
                    const aiMessage = {
                        id: Date.now(),
                        text: generatedText,
                        sender: 'ai',
                        timestamp: new Date().toLocaleTimeString(),
                    };
                    messages.push(aiMessage);
                    renderMessage(aiMessage);
                    hideThinkingBubble();
                    return; // Success, exit
                } else {
                    throw new Error('No content returned from FastAPI server');
                }
            } catch (error) {
                console.error('Error generating AI response:', error);
                retries++;
                if (retries < maxRetries) {
                    const delay = initialDelay * Math.pow(2, retries - 1);
                    await new Promise(res => setTimeout(res, delay));
                } else {
                    hideThinkingBubble();
                    showErrorModal("Sorry, I'm having trouble connecting right now. Please try again later.");
                }
            }
        }
    } finally {
        // Always re-enable the send button and input after the request finishes
        sendBtn.disabled = false;
        messageInput.disabled = false;
    }
};

// Event listener for form submission
chatForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const messageText = messageInput.value.trim();
    if (messageText === '' && !base64Image) {
        showErrorModal('Please enter a message or select an image.');
        return;
    }

    const sendBtn = chatForm.querySelector('button[type="submit"]');
    sendBtn.disabled = true;
    messageInput.disabled = true;

    const userMessage = {
        id: Date.now(),
        text: messageText,
        sender: 'user',
        timestamp: new Date().toLocaleTimeString(),
        image: base64Image ? `data:image/jpeg;base64,${base64Image}` : null,
    };

    messages.push(userMessage);
    renderMessage(userMessage);

    if (base64Image) {
        generateFastAPIImageResponse(messageText, base64Image, sendBtn, messageInput);
    } else {
        generateFastAPIResponse(messageText, sendBtn, messageInput);
    }

    messageInput.value = '';
    scrollToBottom();
});

// Event listener for image upload
imageUpload.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        imagePreview.src = URL.createObjectURL(file);
        imageFileName.textContent = file.name;
        imagePreviewContainer.classList.remove('hidden');
        imagePreviewContainer.classList.add('flex');

        const reader = new FileReader();
        reader.onloadend = () => {
            base64Image = reader.result.split(',')[1];
        };
        reader.readAsDataURL(file);
    }
});


// Event listener for clearing the image preview
clearImageBtn.addEventListener('click', () => {
    base64Image = null;
    imageUpload.value = null; // Reset the file input
    imagePreviewContainer.classList.add('hidden');
    imagePreviewContainer.classList.remove('flex');
    imagePreview.src = '';
    imageFileName.textContent = '';
});

// Initial greeting message on page load
window.addEventListener('DOMContentLoaded', () => {
    const initialMessage = {
        id: Date.now(),
        text: "Hello there! I'm an AI assistant. How can I help you today?",
        sender: 'ai',
        timestamp: new Date().toLocaleTimeString(),
    };
    messages.push(initialMessage);
    renderMessage(initialMessage);
    scrollToBottom();
});