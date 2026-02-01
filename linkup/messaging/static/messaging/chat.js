(function(){
    'use strict';
    
    // DOM Elements
    const chatWindow = document.getElementById('chat-window');
    const chatInput = document.getElementById('chat-input');
    const chatForm = document.getElementById('chat-form');
    const chatSend = document.getElementById('chat-send');
    const chatStatus = document.getElementById('chat-status');
    const onlineIndicator = document.getElementById('online-indicator');
    const userStatusText = document.getElementById('user-status-text');
    const typingIndicator = document.getElementById('typing-indicator');

    if (!window.CHAT_CONFIG) {
        console.warn('CHAT_CONFIG not found');
        if (chatStatus) chatStatus.textContent = 'Chat configuration missing.';
        return;
    }

    const currentUser = window.CHAT_CONFIG.currentUser;
    const targetUser = window.CHAT_CONFIG.username;
    let ws = null;
    let reconnectAttempts = 0;
    const maxReconnectAttempts = 5;
    let typingTimeout = null;
    let isTyping = false;
    
    // Progressive loading state
    let isLoadingOlder = false;
    let hasMoreMessages = true;
    let oldestMessageId = null;
    let messageQueue = []; // Queue for offline messages
    let isOnline = navigator.onLine;
    let retryQueue = []; // Queue for failed messages

    // WebSocket Connection
    function connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
        const wsUrl = protocol + window.location.host + `/ws/chat/${targetUser}/`;
        
        ws = new WebSocket(wsUrl);

        ws.addEventListener('open', () => {
            updateConnectionStatus('Connected', true);
            reconnectAttempts = 0;
            isOnline = true;
            
            // Process any queued messages
            processMessageQueue();
        });

        ws.addEventListener('close', () => {
            updateConnectionStatus('Disconnected', false);
            isOnline = false;
            
            // Try to reconnect
            if (reconnectAttempts < maxReconnectAttempts) {
                reconnectAttempts++;
                setTimeout(() => {
                    updateConnectionStatus(`Reconnecting... (${reconnectAttempts}/${maxReconnectAttempts})`, false);
                    connectWebSocket();
                }, 2000 * reconnectAttempts);
            } else {
                updateConnectionStatus('Connection failed. Messages will be queued.', false);
            }
        });

        ws.addEventListener('error', (error) => {
            console.error('WebSocket error:', error);
            isOnline = false;
        });

        ws.addEventListener('message', (ev) => {
            try {
                const data = JSON.parse(ev.data);
                handleWebSocketMessage(data);
            } catch (e) {
                console.error('Invalid message', e);
            }
        });
    }

    // Process queued messages when connection is restored
    function processMessageQueue() {
        if (messageQueue.length > 0 && ws && ws.readyState === WebSocket.OPEN) {
            const queuedMessages = [...messageQueue];
            messageQueue = [];
            
            queuedMessages.forEach(message => {
                ws.send(JSON.stringify(message));
            });
            
            updateConnectionStatus('Queued messages sent', true);
        }
        
        // Retry failed messages
        if (retryQueue.length > 0) {
            const failedMessages = [...retryQueue];
            retryQueue = [];
            
            failedMessages.forEach(messageData => {
                retryMessage(messageData);
            });
        }
    }

    // Retry failed message delivery
    function retryMessage(messageData) {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                type: 'message',
                message: messageData.content,
                retry_id: messageData.id
            }));
            
            // Update message status to show retry
            const messageEl = document.querySelector(`[data-message-id="${messageData.id}"]`);
            if (messageEl) {
                const checkmarks = messageEl.querySelector('.checkmarks');
                if (checkmarks) {
                    checkmarks.innerHTML = `
                        <svg class="w-4 h-4 text-yellow-500 animate-spin" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z"/>
                        </svg>
                    `;
                }
            }
        } else {
            // Re-queue if still offline
            messageQueue.push({
                type: 'message',
                message: messageData.content
            });
        }
    }

    // Handle different types of WebSocket messages
    function handleWebSocketMessage(data) {
        const type = data.type;
        
        if (type === 'message' || !type) {
            // Regular chat message
            appendMessage(data);
        } else if (type === 'typing') {
            // Typing indicator
            handleTypingIndicator(data);
        } else if (type === 'read_receipt') {
            // Read receipt
            handleReadReceipt(data);
        } else if (type === 'user_status') {
            // User online/offline status
            handleUserStatus(data);
        }
    }

    // Update connection status
    function updateConnectionStatus(text, isConnected) {
        if (!chatStatus) return;
        chatStatus.textContent = text;
        chatStatus.className = `text-xs px-3 py-1 rounded-full ${isConnected ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`;
    }

    // Handle user online/offline status
    function handleUserStatus(data) {
        if (data.username !== targetUser) return;
        
        const isOnline = data.is_online;
        
        // Update online indicator
        if (onlineIndicator) {
            onlineIndicator.className = `absolute bottom-0 right-0 w-4 h-4 rounded-full border-2 border-white ${isOnline ? 'bg-green-500' : 'bg-gray-400'}`;
        }
        
        // Update status text
        if (userStatusText) {
            if (isOnline) {
                userStatusText.innerHTML = '<span class="text-green-600">● Online</span>';
            } else {
                userStatusText.textContent = 'Offline';
            }
        }
    }

    // Handle typing indicator
    function handleTypingIndicator(data) {
        if (data.username === currentUser) return; // Don't show own typing
        
        if (typingIndicator) {
            if (data.is_typing) {
                typingIndicator.classList.remove('hidden');
            } else {
                typingIndicator.classList.add('hidden');
            }
        }
    }

    // Handle read receipts
    function handleReadReceipt(data) {
        const messageId = data.message_id;
        const messageEl = document.querySelector(`[data-message-id="${messageId}"]`);
        
        if (messageEl) {
            const checkmarks = messageEl.querySelector('.checkmarks');
            if (checkmarks) {
                // Update to double blue checkmarks
                checkmarks.innerHTML = `
                    <svg class="w-4 h-4 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M0 11l2-2 5 5L18 3l2 2L7 18z"/>
                        <path d="M7 11l2-2 5 5L18 3l2 2L7 18z" transform="translate(3, 0)"/>
                    </svg>
                `;
            }
        }
    }

    // Append message to chat window
    function appendMessage(m, prepend = false) {
        // Remove loading indicator if present
        const loadingEl = document.getElementById('loading-messages');
        if (loadingEl) {
            loadingEl.remove();
        }
        
        const el = document.createElement('div');
        const isCurrentUser = m.sender === currentUser;
        
        el.className = `flex ${isCurrentUser ? 'justify-end' : 'justify-start'} mb-3 message-bubble`;
        el.setAttribute('data-message-id', m.id);
        
        const when = new Date(m.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        
        // Determine message status (for sent messages only)
        let statusIcon = '';
        if (isCurrentUser) {
            if (m.queued) {
                // Queued message (waiting for delivery)
                statusIcon = `
                    <svg class="w-4 h-4 text-yellow-500" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clip-rule="evenodd" />
                    </svg>
                `;
            } else if (m.failed) {
                // Failed message
                statusIcon = `
                    <svg class="w-4 h-4 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
                    </svg>
                `;
            } else if (m.is_read) {
                // Double blue checkmarks (read)
                statusIcon = `
                    <svg class="w-4 h-4 text-blue-400 checkmarks" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M0 11l2-2 5 5L18 3l2 2L7 18z"/>
                        <path d="M7 11l2-2 5 5L18 3l2 2L7 18z" transform="translate(3, 0)"/>
                    </svg>
                `;
            } else if (m.delivered_at) {
                // Double gray checkmarks (delivered)
                statusIcon = `
                    <svg class="w-4 h-4 text-gray-400 checkmarks" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M0 11l2-2 5 5L18 3l2 2L7 18z"/>
                        <path d="M7 11l2-2 5 5L18 3l2 2L7 18z" transform="translate(3, 0)"/>
                    </svg>
                `;
            } else {
                // Single gray checkmark (sent)
                statusIcon = `
                    <svg class="w-4 h-4 text-gray-400 checkmarks" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M0 11l2-2 5 5L18 3l2 2L7 18z"/>
                    </svg>
                `;
            }
        }
        
        // Create message bubble with improved styling
        el.innerHTML = `
            <div class="max-w-xs lg:max-w-md">
                ${!isCurrentUser ? `<div class="text-xs text-gray-500 mb-1 ml-1">${m.sender}</div>` : ''}
                <div class="relative group">
                    <div class="px-4 py-2.5 rounded-2xl shadow-sm ${isCurrentUser ? 'bg-gradient-to-br from-purple-600 to-purple-700 text-white rounded-br-sm' : 'bg-white text-gray-800 rounded-bl-sm border border-gray-200'}">
                        <div class="break-words">${escapeHtml(m.content)}</div>
                        <div class="flex items-center justify-end mt-1 space-x-1 text-xs ${isCurrentUser ? 'text-purple-200' : 'text-gray-400'}">
                            <span>${when}</span>
                            ${isCurrentUser ? statusIcon : ''}
                        </div>
                    </div>
                    <!-- Message tail -->
                    <div class="absolute ${isCurrentUser ? 'right-0 -mr-2' : 'left-0 -ml-2'} bottom-0 w-0 h-0 border-8 ${isCurrentUser ? 'border-l-purple-700 border-t-transparent border-r-transparent border-b-transparent' : 'border-r-white border-t-transparent border-l-transparent border-b-transparent'}"></div>
                </div>
            </div>
        `;
        
        if (prepend) {
            // For loading older messages, prepend to top
            const firstMessage = chatWindow.querySelector('.message-bubble');
            if (firstMessage) {
                chatWindow.insertBefore(el, firstMessage);
            } else {
                chatWindow.appendChild(el);
            }
        } else {
            // For new messages, append to bottom
            chatWindow.appendChild(el);
            chatWindow.scrollTop = chatWindow.scrollHeight;
        }
        
        // Track oldest message for infinite scroll
        if (!oldestMessageId || m.id < oldestMessageId) {
            oldestMessageId = m.id;
        }
        
        // Send read receipt if this is a received message
        if (!isCurrentUser && ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                type: 'read_receipt',
                message_id: m.id
            }));
        }
    }

    // Load older messages for infinite scroll
    function loadOlderMessages() {
        if (isLoadingOlder || !hasMoreMessages || !oldestMessageId) {
            return;
        }
        
        isLoadingOlder = true;
        
        // Show loading indicator at top
        const loadingEl = document.createElement('div');
        loadingEl.id = 'loading-older';
        loadingEl.className = 'flex justify-center items-center py-4';
        loadingEl.innerHTML = `
            <div class="flex items-center space-x-2 text-gray-500">
                <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-purple-600"></div>
                <span class="text-sm">Loading older messages...</span>
            </div>
        `;
        
        const firstMessage = chatWindow.querySelector('.message-bubble');
        if (firstMessage) {
            chatWindow.insertBefore(loadingEl, firstMessage);
        } else {
            chatWindow.appendChild(loadingEl);
        }
        
        // Remember scroll position
        const scrollHeight = chatWindow.scrollHeight;
        const scrollTop = chatWindow.scrollTop;
        
        fetch(`${window.CHAT_CONFIG.loadOlderUrl}?before_id=${oldestMessageId}&page_size=20`, {
            credentials: 'same-origin'
        })
        .then(r => r.json())
        .then(data => {
            // Remove loading indicator
            const loadingOlder = document.getElementById('loading-older');
            if (loadingOlder) {
                loadingOlder.remove();
            }
            
            if (data.messages && data.messages.length > 0) {
                // Prepend older messages
                data.messages.forEach(m => {
                    appendMessage(m, true);
                });
                
                // Restore scroll position (maintain relative position)
                const newScrollHeight = chatWindow.scrollHeight;
                chatWindow.scrollTop = scrollTop + (newScrollHeight - scrollHeight);
                
                hasMoreMessages = data.has_more;
            } else {
                hasMoreMessages = false;
            }
            
            isLoadingOlder = false;
        })
        .catch(err => {
            console.error('Failed to load older messages:', err);
            
            // Remove loading indicator
            const loadingOlder = document.getElementById('loading-older');
            if (loadingOlder) {
                loadingOlder.remove();
            }
            
            isLoadingOlder = false;
        });
    }

    // Infinite scroll handler
    function handleScroll() {
        if (chatWindow.scrollTop <= 100 && hasMoreMessages && !isLoadingOlder) {
            loadOlderMessages();
        }
    }

    // Escape HTML to prevent XSS
    function escapeHtml(s){
        return s ? s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\n/g,'<br>') : '';
    }

    // Fetch message history
    fetch(window.CHAT_CONFIG.fetchHistoryUrl, {credentials: 'same-origin'})
        .then(r => r.json())
        .then(data => {
            if (data.messages) {
                data.messages.forEach(m => appendMessage(m));
                
                // Set up pagination info
                if (data.pagination) {
                    hasMoreMessages = data.pagination.has_previous;
                }
            }
        })
        .catch(err => {
            console.warn('Failed to fetch history', err);
            if (chatStatus) chatStatus.textContent = 'Failed to load message history';
        });

    // Send typing indicator
    function sendTypingIndicator(typing) {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                type: 'typing',
                is_typing: typing
            }));
        }
    }

    // Handle typing in input
    chatInput.addEventListener('input', () => {
        if (!isTyping) {
            isTyping = true;
            sendTypingIndicator(true);
        }
        
        // Clear existing timeout
        clearTimeout(typingTimeout);
        
        // Set new timeout to stop typing indicator
        typingTimeout = setTimeout(() => {
            isTyping = false;
            sendTypingIndicator(false);
        }, 1000);
    });

    // Send message function
    function sendMessage() {
        const text = chatInput.value.trim();
        if (!text) return;

        // Stop typing indicator
        if (isTyping) {
            isTyping = false;
            sendTypingIndicator(false);
            clearTimeout(typingTimeout);
        }

        const messageData = {
            type: 'message',
            message: text
        };

        if (ws && ws.readyState === WebSocket.OPEN && isOnline) {
            // Send via WebSocket
            ws.send(JSON.stringify(messageData));
            chatInput.value = '';
        } else {
            // Queue message for later delivery or try HTTP fallback
            const messageData = {
                type: 'message',
                message: text
            };
            
            // Try queue endpoint first for better offline support
            fetch(window.CHAT_CONFIG.queueUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({message: text}),
                credentials: 'same-origin'
            })
            .then(r => r.json())
            .then(d => {
                if (d.queued) {
                    // Message was queued successfully
                    const queuedMessage = {
                        id: d.id,
                        sender: currentUser,
                        recipient: targetUser,
                        content: text,
                        created_at: d.created_at,
                        is_read: false,
                        read_at: null,
                        delivered_at: null,
                        queued: true
                    };
                    
                    appendMessage(queuedMessage);
                    chatInput.value = '';
                    updateConnectionStatus(`Message queued for delivery`, false);
                } else {
                    // Regular message sent
                    appendMessage(d);
                    chatInput.value = '';
                    updateConnectionStatus('Message sent via HTTP', false);
                }
            })
            .catch(e => {
                console.error('Failed to queue/send message:', e);
                
                // Add to local queue as last resort
                messageQueue.push(messageData);
                
                // Create temporary message with pending status
                const tempMessage = {
                    id: 'temp_' + Date.now(),
                    sender: currentUser,
                    recipient: targetUser,
                    content: text,
                    created_at: new Date().toISOString(),
                    is_read: false,
                    read_at: null,
                    delivered_at: null,
                    failed: true
                };
                
                appendMessage(tempMessage);
                chatInput.value = '';
                
                // Add to retry queue
                retryQueue.push({
                    id: tempMessage.id,
                    content: text
                });
                
                updateConnectionStatus(`Message failed - will retry (${messageQueue.length} queued)`, false);
            });
        }
    }

    // Event listeners
    chatSend.addEventListener('click', sendMessage);
    
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        sendMessage();
    });

    // Add scroll listener for infinite scroll
    chatWindow.addEventListener('scroll', handleScroll);

    // Listen for online/offline events
    window.addEventListener('online', () => {
        isOnline = true;
        updateConnectionStatus('Back online', true);
        if (ws && ws.readyState !== WebSocket.OPEN) {
            connectWebSocket();
        }
        processMessageQueue();
    });

    window.addEventListener('offline', () => {
        isOnline = false;
        updateConnectionStatus('Offline - messages will be queued', false);
    });

    // Get CSRF token
    function getCookie(name) {
        const v = document.cookie.match('(^|;) ?' + name + '=([^;]*)(;|$)');
        return v ? v[2] : null;
    }

    // Initialize WebSocket connection
    connectWebSocket();
    
    // Focus input on load
    chatInput.focus();
})();
