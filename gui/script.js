const input = document.getElementById('prompt-input');
const responseContainer = document.getElementById('response-container');
const statusContainer = document.getElementById('status-container');
const snapshotBtn = document.getElementById('snapshot-btn');

// --- EVENT LISTENERS ---

// Run when the page is fully loaded
document.addEventListener('DOMContentLoaded', () => {
    const statusText = document.getElementById('status-text');
    if (statusText) {
        statusText.textContent = "Jarvis is online. All systems nominal.";
    }
});

// Send command on Enter key
input.addEventListener('keydown', function(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        const question = input.value;
        if (question.trim() === '') return;

        displayMessage('You', question);
        input.value = '';
        resizeInput();

        // Show thinking indicator
        const thinkingMessageId = `msg-${Date.now()}`;
        displayMessage('Jarvis', '<span>.</span><span>.</span><span>.</span>', true, thinkingMessageId);

        // Bridge to Python
        if (!window.pywebview || !window.pywebview.api || !window.pywebview.api.process_command) {
            updateMessage(thinkingMessageId, "The backend isn’t ready yet. Please try again in a moment.");
            return;
        }

        window.pywebview.api.process_command(question)
            .then(response => {
                updateMessage(thinkingMessageId, response || "No response received.");
            })
            .catch(err => {
                updateMessage(thinkingMessageId, `Error: ${String(err)}`);
            });
    }
});

// Auto-resize the input text area as the user types
input.addEventListener('input', resizeInput);

function resizeInput() {
    input.style.height = 'auto';
    input.style.height = input.scrollHeight + 'px';
}

snapshotBtn.addEventListener('click', () => {
    displayMessage('You', '(Requested Daily Snapshot)');
    const thinkingMessageId = `msg-${Date.now()}`;
    displayMessage('Jarvis', '<span>.</span><span>.</span><span>.</span>', true, thinkingMessageId);

    // Call Python and handle failures gracefully
    if (!window.pywebview || !window.pywebview.api || !window.pywebview.api.get_snapshot) {
        updateMessage(thinkingMessageId, "Snapshot isn’t available (pywebview API not ready). Try again in a moment.");
        return;
    }

    window.pywebview.api.get_snapshot()
        .then(response => {
            updateMessage(thinkingMessageId, response || "Snapshot returned no content.");
        })
        .catch(err => {
            updateMessage(thinkingMessageId, `Error getting snapshot: ${String(err)}`);
        });
});

// --- UI HELPER FUNCTIONS ---

function displayMessage(sender, message, isThinking = false, messageId = null) {
    const messageBlock = document.createElement('div');
    messageBlock.classList.add('response-block');
    if (messageId) {
        messageBlock.id = messageId;
    }
    
    const senderStrong = document.createElement('strong');
    senderStrong.textContent = `${sender}:`;
    messageBlock.appendChild(senderStrong);

    const contentSpan = document.createElement('span');
    if (isThinking) {
        contentSpan.classList.add('thinking');
    }
    contentSpan.innerHTML = message.replace(/\n/g, '<br>');
    
    messageBlock.appendChild(contentSpan);
    responseContainer.appendChild(messageBlock);
    scrollToBottom();
}

function updateMessage(messageId, newMessage) {
    const messageBlock = document.getElementById(messageId);
    if (messageBlock) {
        const contentSpan = messageBlock.querySelector('span');
        if (contentSpan) {
            contentSpan.classList.remove('thinking');
            contentSpan.innerHTML = (newMessage || '').toString().replace(/\n/g, '<br>');
        }
    }
    scrollToBottom();
}

function scrollToBottom() {
    responseContainer.scrollTop = responseContainer.scrollHeight;
}
