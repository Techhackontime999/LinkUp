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
    
    // Enhanced performance and optimistic UI state
    let isLoadingOlder = false;
    let hasMoreMessages = true;
    let oldestMessageId = null;
    let messageQueue = []; // Queue for offline messages
    let isOnline = navigator.onLine;
    let retryQueue = []; // Queue for failed messages
    let optimisticMessages = new Map(); // Track optimistic messages
    let messageCache = new Map(); // Cache for message deduplication
    let lastHeartbeat = Date.now();
    let heartbeatInterval = null;
    let connectionHealthCheck = null;
    
    // Performance optimization constants
    const OPTIMISTIC_DISPLAY_DELAY = 50; // 50ms for sender optimistic display
    const RECIPIENT_DISPLAY_TARGET = 100; // 100ms target for recipients
    const HEARTBEAT_INTERVAL = 30000; // 30 seconds
    const CONNECTION_HEALTH_CHECK = 5000; // 5 seconds
    const MESSAGE_BATCH_SIZE = 20; // Messages per batch load
    const SCROLL_DEBOUNCE_DELAY = 100; // Debounce scroll events
    
    // Optimistic UI performance tracking
    let performanceMetrics = {
        messagesSent: 0,
        messagesReceived: 0,
        averageSendTime: 0,
        averageReceiveTime: 0,
        failedMessages: 0,
        retriedMessages: 0
    };

    // WebSocket Connection with enhanced error handling and heartbeat
    function connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
        const wsUrl = protocol + window.location.host + `/ws/chat/${targetUser}/`;
        
        ws = new WebSocket(wsUrl);

        ws.addEventListener('open', () => {
            updateConnectionStatus('Connected', true);
            reconnectAttempts = 0;
            isOnline = true;
            lastHeartbeat = Date.now();
            
            // Start heartbeat and health monitoring
            startHeartbeat();
            startConnectionHealthCheck();
            
            // Process any queued messages
            processMessageQueue();
            
            // Request connection status and sync
            requestConnectionStatus();
            requestMessageSync();
        });

        ws.addEventListener('close', (event) => {
            updateConnectionStatus('Disconnected', false);
            isOnline = false;
            
            // Stop heartbeat and health check
            stopHeartbeat();
            stopConnectionHealthCheck();
            
            // Enhanced reconnection logic with exponential backoff
            if (reconnectAttempts < maxReconnectAttempts) {
                reconnectAttempts++;
                const delay = Math.min(2000 * Math.pow(2, reconnectAttempts - 1), 30000); // Max 30s delay
                
                setTimeout(() => {
                    updateConnectionStatus(`Reconnecting... (${reconnectAttempts}/${maxReconnectAttempts})`, false);
                    connectWebSocket();
                }, delay);
            } else {
                updateConnectionStatus('Connection failed. Messages will be queued.', false);
                // Try to recover after a longer delay
                setTimeout(() => {
                    reconnectAttempts = 0;
                    connectWebSocket();
                }, 60000); // Retry after 1 minute
            }
        });

        ws.addEventListener('error', (error) => {
            console.error('WebSocket error:', error);
            isOnline = false;
            performanceMetrics.failedMessages++;
        });

        ws.addEventListener('message', (ev) => {
            try {
                const data = JSON.parse(ev.data);
                const receiveTime = Date.now();
                
                // Update performance metrics
                if (data.type === 'message' || !data.type) {
                    performanceMetrics.messagesReceived++;
                    updateAverageReceiveTime(receiveTime);
                }
                
                handleWebSocketMessage(data);
            } catch (e) {
                console.error('Invalid message', e);
            }
        });
    }

    // Enhanced heartbeat system
    function startHeartbeat() {
        if (heartbeatInterval) clearInterval(heartbeatInterval);
        
        heartbeatInterval = setInterval(() => {
            if (ws && ws.readyState === WebSocket.OPEN) {
                const timestamp = Date.now();
                ws.send(JSON.stringify({
                    type: 'ping',
                    timestamp: timestamp
                }));
                lastHeartbeat = timestamp;
            }
        }, HEARTBEAT_INTERVAL);
    }

    function stopHeartbeat() {
        if (heartbeatInterval) {
            clearInterval(heartbeatInterval);
            heartbeatInterval = null;
        }
    }

    // Connection health monitoring
    function startConnectionHealthCheck() {
        if (connectionHealthCheck) clearInterval(connectionHealthCheck);
        
        connectionHealthCheck = setInterval(() => {
            const now = Date.now();
            const timeSinceLastHeartbeat = now - lastHeartbeat;
            
            // If no heartbeat response in 2x interval, consider connection unhealthy
            if (timeSinceLastHeartbeat > HEARTBEAT_INTERVAL * 2) {
                console.warn('Connection appears unhealthy, attempting reconnection');
                if (ws) {
                    ws.close();
                }
            }
        }, CONNECTION_HEALTH_CHECK);
    }

    function stopConnectionHealthCheck() {
        if (connectionHealthCheck) {
            clearInterval(connectionHealthCheck);
            connectionHealthCheck = null;
        }
    }

    // Request connection status from server
    function requestConnectionStatus() {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                type: 'get_connection_status'
            }));
        }
    }

    // Request message synchronization
    function requestMessageSync() {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                type: 'sync_request'
            }));
        }
    }

    // Enhanced message queue processing with batching
    function processMessageQueue() {
        if (messageQueue.length > 0 && ws && ws.readyState === WebSocket.OPEN) {
            const queuedMessages = [...messageQueue];
            messageQueue = [];
            
            // Process in batches to avoid overwhelming the connection
            const batchSize = 5;
            for (let i = 0; i < queuedMessages.length; i += batchSize) {
                const batch = queuedMessages.slice(i, i + batchSize);
                
                setTimeout(() => {
                    batch.forEach(message => {
                        ws.send(JSON.stringify(message));
                    });
                }, i * 100); // Stagger batches by 100ms
            }
            
            updateConnectionStatus(`Sending ${queuedMessages.length} queued messages`, true);
        }
        
        // Enhanced retry logic for failed messages
        if (retryQueue.length > 0) {
            const failedMessages = [...retryQueue];
            retryQueue = [];
            
            failedMessages.forEach((messageData, index) => {
                setTimeout(() => {
                    retryMessage(messageData);
                }, index * 200); // Stagger retries
            });
        }
    }

    // Enhanced retry with exponential backoff
    function retryMessage(messageData) {
        if (ws && ws.readyState === WebSocket.OPEN) {
            const retryData = {
                type: 'retry_message',
                message_id: messageData.id,
                original_content: messageData.content
            };
            
            ws.send(JSON.stringify(retryData));
            performanceMetrics.retriedMessages++;
            
            // Update message status to show retry
            updateMessageStatus(messageData.id, 'retrying');
        } else {
            // Re-queue if still offline
            messageQueue.push({
                type: 'message',
                message: messageData.content,
                client_id: messageData.client_id
            });
        }
    }

    // Enhanced message handling with optimistic UI
    function handleWebSocketMessage(data) {
        const type = data.type;
        
        switch (type) {
            case 'message':
            case undefined: // Default to message
                handleIncomingMessage(data);
                break;
            case 'typing':
                handleTypingIndicator(data);
                break;
            case 'read_receipt':
            case 'read_receipt_update':
                handleReadReceipt(data);
                break;
            case 'bulk_read_receipts':
                handleBulkReadReceipts(data);
                break;
            case 'user_status':
                handleUserStatus(data);
                break;
            case 'message_status_update':
                handleMessageStatusUpdate(data);
                break;
            case 'connection_status':
                handleConnectionStatus(data);
                break;
            case 'sync_completed':
                handleSyncCompleted(data);
                break;
            case 'pong':
                handlePong(data);
                break;
            case 'retry_result':
                handleRetryResult(data);
                break;
            case 'error':
                handleError(data);
                break;
            default:
                console.warn('Unknown message type:', type, data);
        }
    }

    // Handle incoming messages with deduplication
    function handleIncomingMessage(data) {
        // Check for duplicate messages
        if (messageCache.has(data.id)) {
            return; // Skip duplicate
        }
        
        messageCache.set(data.id, data);
        
        // If this was an optimistic message, update it
        if (optimisticMessages.has(data.client_id)) {
            updateOptimisticMessage(data.client_id, data);
        } else {
            // New message from other user
            appendMessage(data);
        }
        
        // Clean up old cache entries (keep last 100 messages)
        if (messageCache.size > 100) {
            const oldestKey = messageCache.keys().next().value;
            messageCache.delete(oldestKey);
        }
    }

    // Handle pong response for heartbeat
    function handlePong(data) {
        lastHeartbeat = Date.now();
        
        // Calculate round-trip time if timestamp provided
        if (data.timestamp) {
            const rtt = lastHeartbeat - data.timestamp;
            updateConnectionQuality(rtt);
        }
    }

    // Handle connection status updates
    function handleConnectionStatus(data) {
        if (data.status) {
            const status = data.status;
            updateConnectionStatus(`Connection: ${status.state}`, status.state === 'connected');
        }
    }

    // Handle sync completion
    function handleSyncCompleted(data) {
        updateConnectionStatus('Messages synchronized', true);
    }

    // Handle retry results
    function handleRetryResult(data) {
        if (data.success) {
            updateMessageStatus(data.message_id, 'sent');
        } else {
            updateMessageStatus(data.message_id, 'failed');
        }
    }

    // Update connection quality indicator
    function updateConnectionQuality(rtt) {
        let quality = 'excellent';
        let color = 'green';
        
        if (rtt > 1000) {
            quality = 'poor';
            color = 'red';
        } else if (rtt > 500) {
            quality = 'fair';
            color = 'yellow';
        } else if (rtt > 200) {
            quality = 'good';
            color = 'blue';
        }
        
        // Update UI if quality indicator exists
        const qualityEl = document.getElementById('connection-quality');
        if (qualityEl) {
            qualityEl.textContent = `${quality} (${rtt}ms)`;
            qualityEl.className = `text-${color}-600`;
        }
    }

    // Enhanced connection status with more details
    function updateConnectionStatus(text, isConnected) {
        if (!chatStatus) return;
        
        chatStatus.textContent = text;
        chatStatus.className = `text-xs px-3 py-1 rounded-full transition-all duration-200 ${
            isConnected 
                ? 'bg-green-100 text-green-700 border border-green-200' 
                : 'bg-red-100 text-red-700 border border-red-200'
        }`;
        
        // Add performance info if available
        if (isConnected && performanceMetrics.messagesSent > 0) {
            const avgSend = Math.round(performanceMetrics.averageSendTime);
            chatStatus.title = `Avg send time: ${avgSend}ms | Sent: ${performanceMetrics.messagesSent} | Failed: ${performanceMetrics.failedMessages}`;
        }
    }

    // Enhanced user status with last seen
    function handleUserStatus(data) {
        if (data.username !== targetUser) return;
        
        const isOnline = data.is_online;
        const lastSeen = data.last_seen_display;
        
        // Update online indicator with animation
        if (onlineIndicator) {
            onlineIndicator.className = `absolute bottom-0 right-0 w-4 h-4 rounded-full border-2 border-white transition-all duration-300 ${
                isOnline ? 'bg-green-500 shadow-green-300 shadow-lg' : 'bg-gray-400'
            }`;
        }
        
        // Update status text with more detail
        if (userStatusText) {
            if (isOnline) {
                userStatusText.innerHTML = '<span class="text-green-600 flex items-center"><span class="w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse"></span>Online</span>';
            } else {
                userStatusText.innerHTML = `<span class="text-gray-500">Last seen ${lastSeen || 'recently'}</span>`;
            }
        }
    }

    // Enhanced typing indicator with user info
    function handleTypingIndicator(data) {
        if (data.username === currentUser) return; // Don't show own typing
        
        if (typingIndicator) {
            if (data.is_typing) {
                typingIndicator.innerHTML = `
                    <div class="flex items-center space-x-2 text-gray-500 animate-pulse">
                        <div class="flex space-x-1">
                            <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                            <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0.1s"></div>
                            <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
                        </div>
                        <span class="text-sm">${data.username} is typing...</span>
                    </div>
                `;
                typingIndicator.classList.remove('hidden');
            } else {
                typingIndicator.classList.add('hidden');
            }
        }
    }

    // Enhanced message status updates with animations
    function handleMessageStatusUpdate(data) {
        const messageId = data.message_id;
        const newStatus = data.new_status;
        updateMessageStatus(messageId, newStatus);
    }

    // Update message status with improved icons and animations
    function updateMessageStatus(messageId, newStatus) {
        const messageEl = document.querySelector(`[data-message-id="${messageId}"]`);
        
        if (messageEl) {
            const checkmarks = messageEl.querySelector('.checkmarks');
            if (checkmarks) {
                let statusIcon = getStatusIcon(newStatus);
                
                if (statusIcon) {
                    // Add transition animation
                    checkmarks.style.opacity = '0';
                    setTimeout(() => {
                        checkmarks.innerHTML = statusIcon;
                        checkmarks.style.opacity = '1';
                    }, 100);
                }
            }
        }
    }

    // Get status icon HTML
    function getStatusIcon(status) {
        const icons = {
            pending: `
                <svg class="w-4 h-4 text-gray-400 animate-pulse checkmarks" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clip-rule="evenodd" />
                </svg>
            `,
            sent: `
                <svg class="w-4 h-4 text-gray-400 checkmarks transition-all duration-200" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M0 11l2-2 5 5L18 3l2 2L7 18z"/>
                </svg>
            `,
            delivered: `
                <svg class="w-4 h-4 text-gray-400 checkmarks transition-all duration-200" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M0 11l2-2 5 5L18 3l2 2L7 18z"/>
                    <path d="M7 11l2-2 5 5L18 3l2 2L7 18z" transform="translate(3, 0)"/>
                </svg>
            `,
            read: `
                <svg class="w-4 h-4 text-blue-500 checkmarks transition-all duration-200" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M0 11l2-2 5 5L18 3l2 2L7 18z"/>
                    <path d="M7 11l2-2 5 5L18 3l2 2L7 18z" transform="translate(3, 0)"/>
                </svg>
            `,
            failed: `
                <svg class="w-4 h-4 text-red-500 checkmarks transition-all duration-200" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
                </svg>
            `,
            retrying: `
                <svg class="w-4 h-4 text-yellow-500 animate-spin checkmarks" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z"/>
                </svg>
            `
        };
        
        return icons[status] || icons.pending;
    }

    // Handle bulk read receipts
    function handleBulkReadReceipts(data) {
        if (data.message_ids && Array.isArray(data.message_ids)) {
            data.message_ids.forEach(messageId => {
                updateMessageStatus(messageId, 'read');
            });
        }
    }

    // Enhanced error handling with user-friendly messages and retry options
    function handleError(data) {
        console.error('WebSocket error:', data.error);
        
        const errorEl = document.createElement('div');
        errorEl.className = 'bg-red-50 border-l-4 border-red-400 p-4 mb-3 rounded-r-lg shadow-sm';
        
        let retryButton = '';
        if (data.retry_available && data.message_id) {
            retryButton = `
                <button class="ml-3 bg-red-100 hover:bg-red-200 text-red-800 px-3 py-1 rounded text-sm transition-colors duration-200" 
                        onclick="retryFailedMessage('${data.message_id}')">
                    Retry
                </button>
            `;
        }
        
        errorEl.innerHTML = `
            <div class="flex items-start">
                <div class="flex-shrink-0">
                    <svg class="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
                    </svg>
                </div>
                <div class="ml-3 flex-1">
                    <p class="text-sm text-red-700">
                        <strong>Message Error:</strong> ${escapeHtml(data.error)}
                    </p>
                    ${data.error_details ? `<p class="text-xs text-red-600 mt-1">${escapeHtml(data.error_details)}</p>` : ''}
                </div>
                ${retryButton}
            </div>
        `;
        
        chatWindow.appendChild(errorEl);
        chatWindow.scrollTop = chatWindow.scrollHeight;
        
        // Auto-remove error after 10 seconds
        setTimeout(() => {
            if (errorEl.parentNode) {
                errorEl.style.opacity = '0';
                errorEl.style.transform = 'translateX(100%)';
                setTimeout(() => errorEl.remove(), 300);
            }
        }, 10000);
    }

    // Global retry function for failed messages
    window.retryFailedMessage = function(messageId) {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                type: 'retry_message',
                message_id: messageId
            }));
        }
    };

    // Update optimistic message when server confirms
    function updateOptimisticMessage(clientId, serverData) {
        const optimisticData = optimisticMessages.get(clientId);
        if (optimisticData) {
            const messageEl = document.querySelector(`[data-client-id="${clientId}"]`);
            if (messageEl) {
                // Update message ID and remove optimistic styling
                messageEl.setAttribute('data-message-id', serverData.id);
                messageEl.removeAttribute('data-client-id');
                messageEl.classList.remove('optimistic-message');
                
                // Update status
                updateMessageStatus(serverData.id, serverData.status || 'sent');
            }
            
            optimisticMessages.delete(clientId);
        }
    }

    // Performance metrics tracking
    function updateAverageSendTime(sendTime) {
        const count = performanceMetrics.messagesSent;
        const currentAvg = performanceMetrics.averageSendTime;
        performanceMetrics.averageSendTime = (currentAvg * count + sendTime) / (count + 1);
    }

    function updateAverageReceiveTime(receiveTime) {
        const count = performanceMetrics.messagesReceived;
        const currentAvg = performanceMetrics.averageReceiveTime;
        performanceMetrics.averageReceiveTime = (currentAvg * count + receiveTime) / (count + 1);
    }

    // Enhanced message display with optimistic UI and improved performance
    function appendMessage(m, prepend = false) {
        // Remove loading indicator if present
        const loadingEl = document.getElementById('loading-messages');
        if (loadingEl) {
            loadingEl.remove();
        }
        
        const el = document.createElement('div');
        const isCurrentUser = m.sender === currentUser;
        
        el.className = `flex ${isCurrentUser ? 'justify-end' : 'justify-start'} mb-3 message-bubble transition-all duration-200 ease-in-out`;
        el.setAttribute('data-message-id', m.id);
        
        // Add client ID for optimistic messages
        if (m.client_id && optimisticMessages.has(m.client_id)) {
            el.setAttribute('data-client-id', m.client_id);
            el.classList.add('optimistic-message');
        }
        
        const when = new Date(m.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        
        // Enhanced status icon with better visual feedback
        let statusIcon = '';
        if (isCurrentUser) {
            const status = m.status || 'pending';
            statusIcon = getStatusIcon(status);
        }
        
        // Enhanced message bubble with better styling and animations
        el.innerHTML = `
            <div class="max-w-xs lg:max-w-md transform transition-all duration-200 hover:scale-[1.02]">
                ${!isCurrentUser ? `<div class="text-xs text-gray-500 mb-1 ml-1 font-medium">${escapeHtml(m.sender)}</div>` : ''}
                <div class="relative group">
                    <div class="px-4 py-2.5 rounded-2xl shadow-sm transition-all duration-200 ${
                        isCurrentUser 
                            ? 'bg-gradient-to-br from-purple-600 to-purple-700 text-white rounded-br-sm hover:shadow-lg' 
                            : 'bg-white text-gray-800 rounded-bl-sm border border-gray-200 hover:shadow-md hover:border-gray-300'
                    }">
                        <div class="break-words leading-relaxed">${escapeHtml(m.content)}</div>
                        <div class="flex items-center justify-end mt-1.5 space-x-1 text-xs ${
                            isCurrentUser ? 'text-purple-200' : 'text-gray-400'
                        }">
                            <span class="font-medium">${when}</span>
                            ${isCurrentUser ? `<span class="checkmarks transition-all duration-200">${statusIcon}</span>` : ''}
                        </div>
                    </div>
                    <!-- Enhanced message tail with better positioning -->
                    <div class="absolute ${
                        isCurrentUser ? 'right-0 -mr-2' : 'left-0 -ml-2'
                    } bottom-0 w-0 h-0 border-8 ${
                        isCurrentUser 
                            ? 'border-l-purple-700 border-t-transparent border-r-transparent border-b-transparent' 
                            : 'border-r-white border-t-transparent border-l-transparent border-b-transparent'
                    }"></div>
                    
                    <!-- Message actions (show on hover) -->
                    <div class="absolute top-0 ${
                        isCurrentUser ? 'left-0 -ml-8' : 'right-0 -mr-8'
                    } opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                        <div class="flex flex-col space-y-1">
                            ${m.status === 'failed' ? `
                                <button onclick="retryFailedMessage('${m.id}')" 
                                        class="w-6 h-6 bg-red-500 hover:bg-red-600 text-white rounded-full flex items-center justify-center text-xs transition-colors duration-200"
                                        title="Retry message">
                                    ↻
                                </button>
                            ` : ''}
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Enhanced insertion with smooth animations
        if (prepend) {
            // For loading older messages, prepend to top with fade-in
            const firstMessage = chatWindow.querySelector('.message-bubble');
            if (firstMessage) {
                el.style.opacity = '0';
                el.style.transform = 'translateY(-10px)';
                chatWindow.insertBefore(el, firstMessage);
                
                // Animate in
                requestAnimationFrame(() => {
                    el.style.opacity = '1';
                    el.style.transform = 'translateY(0)';
                });
            } else {
                chatWindow.appendChild(el);
            }
        } else {
            // For new messages, append to bottom with slide-in animation
            el.style.opacity = '0';
            el.style.transform = 'translateY(20px)';
            chatWindow.appendChild(el);
            
            // Animate in
            requestAnimationFrame(() => {
                el.style.opacity = '1';
                el.style.transform = 'translateY(0)';
            });
            
            // Smooth scroll to bottom
            smoothScrollToBottom();
        }
        
        // Track oldest message for infinite scroll
        if (!oldestMessageId || m.id < oldestMessageId) {
            oldestMessageId = m.id;
        }
        
        // Enhanced read receipt handling with debouncing
        if (!isCurrentUser && ws && ws.readyState === WebSocket.OPEN) {
            // Debounce read receipts to avoid spam
            clearTimeout(window.readReceiptTimeout);
            window.readReceiptTimeout = setTimeout(() => {
                ws.send(JSON.stringify({
                    type: 'read_receipt',
                    message_id: m.id
                }));
            }, 500);
        }
    }

    // Smooth scroll to bottom with easing
    function smoothScrollToBottom() {
        const start = chatWindow.scrollTop;
        const end = chatWindow.scrollHeight - chatWindow.clientHeight;
        const distance = end - start;
        const duration = 300;
        let startTime = null;
        
        function animation(currentTime) {
            if (startTime === null) startTime = currentTime;
            const timeElapsed = currentTime - startTime;
            const progress = Math.min(timeElapsed / duration, 1);
            
            // Easing function (ease-out)
            const easeOut = 1 - Math.pow(1 - progress, 3);
            
            chatWindow.scrollTop = start + (distance * easeOut);
            
            if (timeElapsed < duration) {
                requestAnimationFrame(animation);
            }
        }
        
        requestAnimationFrame(animation);
    }

    // Enhanced infinite scroll with improved performance
    function loadOlderMessages() {
        if (isLoadingOlder || !hasMoreMessages || !oldestMessageId) {
            return;
        }
        
        isLoadingOlder = true;
        
        // Show enhanced loading indicator
        const loadingEl = document.createElement('div');
        loadingEl.id = 'loading-older';
        loadingEl.className = 'flex justify-center items-center py-4 animate-fade-in';
        loadingEl.innerHTML = `
            <div class="flex items-center space-x-3 text-gray-500 bg-gray-50 px-4 py-2 rounded-full shadow-sm">
                <div class="relative">
                    <div class="animate-spin rounded-full h-5 w-5 border-2 border-purple-600 border-t-transparent"></div>
                    <div class="absolute inset-0 rounded-full border-2 border-purple-200"></div>
                </div>
                <span class="text-sm font-medium">Loading older messages...</span>
            </div>
        `;
        
        const firstMessage = chatWindow.querySelector('.message-bubble');
        if (firstMessage) {
            chatWindow.insertBefore(loadingEl, firstMessage);
        } else {
            chatWindow.appendChild(loadingEl);
        }
        
        // Remember scroll position for restoration
        const scrollHeight = chatWindow.scrollHeight;
        const scrollTop = chatWindow.scrollTop;
        
        // Enhanced fetch with better error handling
        fetch(`${window.CHAT_CONFIG.loadOlderUrl}?before_id=${oldestMessageId}&page_size=${MESSAGE_BATCH_SIZE}`, {
            credentials: 'same-origin',
            headers: {
                'Accept': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            // Remove loading indicator with fade-out
            const loadingOlder = document.getElementById('loading-older');
            if (loadingOlder) {
                loadingOlder.style.opacity = '0';
                setTimeout(() => loadingOlder.remove(), 200);
            }
            
            if (data.messages && data.messages.length > 0) {
                // Batch insert older messages for better performance
                const fragment = document.createDocumentFragment();
                const tempContainer = document.createElement('div');
                
                data.messages.forEach(m => {
                    const messageEl = createMessageElement(m, true);
                    tempContainer.appendChild(messageEl);
                });
                
                // Insert all at once
                const firstMessage = chatWindow.querySelector('.message-bubble');
                if (firstMessage) {
                    chatWindow.insertBefore(tempContainer, firstMessage);
                    
                    // Move children from temp container to chat window
                    while (tempContainer.firstChild) {
                        chatWindow.insertBefore(tempContainer.firstChild, firstMessage);
                    }
                }
                
                // Restore scroll position with smooth transition
                const newScrollHeight = chatWindow.scrollHeight;
                const newScrollTop = scrollTop + (newScrollHeight - scrollHeight);
                
                chatWindow.style.scrollBehavior = 'auto';
                chatWindow.scrollTop = newScrollTop;
                setTimeout(() => {
                    chatWindow.style.scrollBehavior = 'smooth';
                }, 100);
                
                hasMoreMessages = data.has_more;
                
                // Update performance metrics
                console.log(`Loaded ${data.messages.length} older messages`);
            } else {
                hasMoreMessages = false;
                
                // Show "no more messages" indicator
                const noMoreEl = document.createElement('div');
                noMoreEl.className = 'text-center py-4 text-gray-400 text-sm';
                noMoreEl.textContent = 'No more messages';
                
                const firstMessage = chatWindow.querySelector('.message-bubble');
                if (firstMessage) {
                    chatWindow.insertBefore(noMoreEl, firstMessage);
                }
                
                // Auto-remove after 3 seconds
                setTimeout(() => {
                    if (noMoreEl.parentNode) {
                        noMoreEl.style.opacity = '0';
                        setTimeout(() => noMoreEl.remove(), 300);
                    }
                }, 3000);
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
            
            // Show error message
            const errorEl = document.createElement('div');
            errorEl.className = 'text-center py-4 text-red-500 text-sm bg-red-50 rounded-lg mx-4';
            errorEl.innerHTML = `
                <div class="flex items-center justify-center space-x-2">
                    <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
                    </svg>
                    <span>Failed to load older messages</span>
                    <button onclick="loadOlderMessages()" class="ml-2 text-red-700 underline hover:no-underline">
                        Retry
                    </button>
                </div>
            `;
            
            const firstMessage = chatWindow.querySelector('.message-bubble');
            if (firstMessage) {
                chatWindow.insertBefore(errorEl, firstMessage);
            }
            
            // Auto-remove error after 5 seconds
            setTimeout(() => {
                if (errorEl.parentNode) {
                    errorEl.style.opacity = '0';
                    setTimeout(() => errorEl.remove(), 300);
                }
            }, 5000);
            
            isLoadingOlder = false;
        });
    }

    // Create message element (helper function for batch operations)
    function createMessageElement(m, prepend = false) {
        const el = document.createElement('div');
        const isCurrentUser = m.sender === currentUser;
        
        el.className = `flex ${isCurrentUser ? 'justify-end' : 'justify-start'} mb-3 message-bubble transition-all duration-200 ease-in-out`;
        el.setAttribute('data-message-id', m.id);
        
        const when = new Date(m.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        let statusIcon = '';
        
        if (isCurrentUser) {
            const status = m.status || 'pending';
            statusIcon = getStatusIcon(status);
        }
        
        el.innerHTML = `
            <div class="max-w-xs lg:max-w-md transform transition-all duration-200 hover:scale-[1.02]">
                ${!isCurrentUser ? `<div class="text-xs text-gray-500 mb-1 ml-1 font-medium">${escapeHtml(m.sender)}</div>` : ''}
                <div class="relative group">
                    <div class="px-4 py-2.5 rounded-2xl shadow-sm transition-all duration-200 ${
                        isCurrentUser 
                            ? 'bg-gradient-to-br from-purple-600 to-purple-700 text-white rounded-br-sm hover:shadow-lg' 
                            : 'bg-white text-gray-800 rounded-bl-sm border border-gray-200 hover:shadow-md hover:border-gray-300'
                    }">
                        <div class="break-words leading-relaxed">${escapeHtml(m.content)}</div>
                        <div class="flex items-center justify-end mt-1.5 space-x-1 text-xs ${
                            isCurrentUser ? 'text-purple-200' : 'text-gray-400'
                        }">
                            <span class="font-medium">${when}</span>
                            ${isCurrentUser ? `<span class="checkmarks transition-all duration-200">${statusIcon}</span>` : ''}
                        </div>
                    </div>
                    <div class="absolute ${
                        isCurrentUser ? 'right-0 -mr-2' : 'left-0 -ml-2'
                    } bottom-0 w-0 h-0 border-8 ${
                        isCurrentUser 
                            ? 'border-l-purple-700 border-t-transparent border-r-transparent border-b-transparent' 
                            : 'border-r-white border-t-transparent border-l-transparent border-b-transparent'
                    }"></div>
                </div>
            </div>
        `;
        
        return el;
    }

    // Debounced scroll handler for better performance
    let scrollTimeout = null;
    function handleScroll() {
        if (scrollTimeout) {
            clearTimeout(scrollTimeout);
        }
        
        scrollTimeout = setTimeout(() => {
            if (chatWindow.scrollTop <= 100 && hasMoreMessages && !isLoadingOlder) {
                loadOlderMessages();
            }
        }, SCROLL_DEBOUNCE_DELAY);
    }

    // Enhanced message sending with optimistic UI and 50ms display target
    function sendMessage() {
        const text = chatInput.value.trim();
        if (!text) return;

        // Stop typing indicator
        if (isTyping) {
            isTyping = false;
            sendTypingIndicator(false);
            clearTimeout(typingTimeout);
        }

        // Generate client ID for deduplication and optimistic UI
        const clientId = `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        const sendTime = Date.now();

        // Create optimistic message for immediate display (50ms target)
        const optimisticMessage = {
            id: `temp_${clientId}`,
            sender: currentUser,
            recipient: targetUser,
            content: text,
            status: 'pending',
            client_id: clientId,
            created_at: new Date().toISOString(),
            is_read: false,
            read_at: null,
            delivered_at: null,
            optimistic: true
        };

        // Display optimistically within 50ms
        setTimeout(() => {
            appendMessage(optimisticMessage);
            performanceMetrics.messagesSent++;
            updateAverageSendTime(Date.now() - sendTime);
        }, OPTIMISTIC_DISPLAY_DELAY);

        // Store optimistic message for later update
        optimisticMessages.set(clientId, {
            tempId: optimisticMessage.id,
            content: text,
            timestamp: sendTime
        });

        const messageData = {
            type: 'message',
            message: text,
            client_id: clientId
        };

        // Clear input immediately for better UX
        chatInput.value = '';

        if (ws && ws.readyState === WebSocket.OPEN && isOnline) {
            // Send via WebSocket with performance tracking
            ws.send(JSON.stringify(messageData));
            
            // Update connection status
            updateConnectionStatus('Message sent', true);
        } else {
            // Enhanced offline handling with multiple fallback strategies
            handleOfflineMessage(messageData, optimisticMessage, sendTime);
        }
    }

    // Enhanced offline message handling
    function handleOfflineMessage(messageData, optimisticMessage, sendTime) {
        const fallbackData = {
            message: messageData.message,
            client_id: messageData.client_id
        };
        
        // Strategy 1: Try HTTP queue endpoint
        fetch(window.CHAT_CONFIG.queueUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify(fallbackData),
            credentials: 'same-origin'
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.queued) {
                // Message was queued successfully
                updateOptimisticMessage(messageData.client_id, {
                    id: data.id,
                    status: 'queued',
                    created_at: data.created_at
                });
                
                updateConnectionStatus(`Message queued for delivery`, false);
            } else if (data.id) {
                // Message was sent immediately via HTTP
                updateOptimisticMessage(messageData.client_id, {
                    id: data.id,
                    status: 'sent',
                    created_at: data.created_at
                });
                
                updateConnectionStatus('Message sent via HTTP', true);
            }
        })
        .catch(error => {
            console.error('HTTP fallback failed:', error);
            
            // Strategy 2: Local queue as last resort
            messageQueue.push(messageData);
            
            // Update optimistic message to show failed state
            updateOptimisticMessage(messageData.client_id, {
                status: 'failed',
                error: error.message
            });
            
            // Add to retry queue
            retryQueue.push({
                id: optimisticMessage.id,
                content: messageData.message,
                client_id: messageData.client_id,
                timestamp: sendTime
            });
            
            updateConnectionStatus(`Message failed - queued for retry (${messageQueue.length} pending)`, false);
            performanceMetrics.failedMessages++;
        });
    }

    // Enhanced typing indicator with debouncing and performance optimization
    let typingDebounceTimeout = null;
    function sendTypingIndicator(typing) {
        if (ws && ws.readyState === WebSocket.OPEN) {
            // Debounce typing indicators to reduce network traffic
            clearTimeout(typingDebounceTimeout);
            
            typingDebounceTimeout = setTimeout(() => {
                ws.send(JSON.stringify({
                    type: 'typing',
                    is_typing: typing
                }));
            }, 100); // 100ms debounce
        }
    }

    // Enhanced input handling with better typing detection
    let inputTimeout = null;
    chatInput.addEventListener('input', () => {
        // Immediate typing indicator for responsiveness
        if (!isTyping) {
            isTyping = true;
            sendTypingIndicator(true);
        }
        
        // Clear existing timeout
        clearTimeout(inputTimeout);
        clearTimeout(typingTimeout);
        
        // Set new timeout to stop typing indicator (1 second as per requirements)
        inputTimeout = setTimeout(() => {
            isTyping = false;
            sendTypingIndicator(false);
        }, 1000);
        
        // Also set typing timeout as backup
        typingTimeout = setTimeout(() => {
            if (isTyping) {
                isTyping = false;
                sendTypingIndicator(false);
            }
        }, 1200);
    });

    // Enhanced read receipt handling
    function handleReadReceipt(data) {
        const messageId = data.message_id;
        const readBy = data.read_by;
        
        // Update message status to read
        updateMessageStatus(messageId, 'read');
        
        // Show read receipt notification (optional)
        if (readBy !== currentUser) {
            console.log(`Message ${messageId} read by ${readBy}`);
        }
    }

    // Initialize message history with enhanced loading
    function initializeMessageHistory() {
        // Show initial loading indicator
        const loadingEl = document.createElement('div');
        loadingEl.id = 'loading-messages';
        loadingEl.className = 'flex justify-center items-center py-8';
        loadingEl.innerHTML = `
            <div class="flex flex-col items-center space-y-3 text-gray-500">
                <div class="relative">
                    <div class="animate-spin rounded-full h-8 w-8 border-2 border-purple-600 border-t-transparent"></div>
                    <div class="absolute inset-0 rounded-full border-2 border-purple-200"></div>
                </div>
                <span class="text-sm font-medium">Loading conversation...</span>
            </div>
        `;
        chatWindow.appendChild(loadingEl);

        fetch(window.CHAT_CONFIG.fetchHistoryUrl, {
            credentials: 'same-origin',
            headers: {
                'Accept': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            // Remove loading indicator
            const loading = document.getElementById('loading-messages');
            if (loading) {
                loading.remove();
            }
            
            if (data.messages && data.messages.length > 0) {
                // Load messages with staggered animation for better UX
                data.messages.forEach((m, index) => {
                    setTimeout(() => {
                        appendMessage(m);
                    }, index * 50); // 50ms stagger
                });
                
                // Set up pagination info
                if (data.pagination) {
                    hasMoreMessages = data.pagination.has_previous;
                }
                
                // Scroll to bottom after all messages loaded
                setTimeout(() => {
                    smoothScrollToBottom();
                }, data.messages.length * 50 + 200);
            } else {
                // Show empty state
                const emptyEl = document.createElement('div');
                emptyEl.className = 'flex flex-col items-center justify-center py-12 text-gray-400';
                emptyEl.innerHTML = `
                    <svg class="w-16 h-16 mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"></path>
                    </svg>
                    <p class="text-lg font-medium mb-2">Start a conversation</p>
                    <p class="text-sm">Send a message to begin chatting with ${targetUser}</p>
                `;
                chatWindow.appendChild(emptyEl);
            }
        })
        .catch(err => {
            console.error('Failed to fetch message history:', err);
            
            // Remove loading indicator
            const loading = document.getElementById('loading-messages');
            if (loading) {
                loading.remove();
            }
            
            // Show error state
            const errorEl = document.createElement('div');
            errorEl.className = 'flex flex-col items-center justify-center py-12 text-red-500';
            errorEl.innerHTML = `
                <svg class="w-16 h-16 mb-4" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
                </svg>
                <p class="text-lg font-medium mb-2">Failed to load messages</p>
                <p class="text-sm mb-4">${err.message}</p>
                <button onclick="initializeMessageHistory()" class="bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded-lg transition-colors duration-200">
                    Retry
                </button>
            `;
            chatWindow.appendChild(errorEl);
            
            if (chatStatus) {
                chatStatus.textContent = 'Failed to load message history';
                chatStatus.className = 'text-xs px-3 py-1 rounded-full bg-red-100 text-red-700';
            }
        });
    }

    // Escape HTML to prevent XSS with enhanced security
    function escapeHtml(s) {
        if (!s) return '';
        
        const div = document.createElement('div');
        div.textContent = s;
        return div.innerHTML
            .replace(/\n/g, '<br>')
            .replace(/\t/g, '&nbsp;&nbsp;&nbsp;&nbsp;');
    }

    // Enhanced event listeners with better performance
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

    // Enhanced scroll listener with throttling
    let scrollThrottleTimeout = null;
    chatWindow.addEventListener('scroll', () => {
        if (scrollThrottleTimeout) return;
        
        scrollThrottleTimeout = setTimeout(() => {
            handleScroll();
            scrollThrottleTimeout = null;
        }, SCROLL_DEBOUNCE_DELAY);
    });

    // Enhanced online/offline event handling
    window.addEventListener('online', () => {
        isOnline = true;
        updateConnectionStatus('Back online - reconnecting...', true);
        
        // Reconnect WebSocket if needed
        if (!ws || ws.readyState !== WebSocket.OPEN) {
            connectWebSocket();
        }
        
        // Process queued messages
        setTimeout(() => {
            processMessageQueue();
        }, 1000);
    });

    window.addEventListener('offline', () => {
        isOnline = false;
        updateConnectionStatus('Offline - messages will be queued', false);
    });

    // Enhanced visibility change handling for better performance
    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            // Page is hidden, reduce activity
            if (isTyping) {
                isTyping = false;
                sendTypingIndicator(false);
            }
        } else {
            // Page is visible, resume normal activity
            if (ws && ws.readyState === WebSocket.OPEN) {
                // Send a ping to check connection health
                ws.send(JSON.stringify({
                    type: 'ping',
                    timestamp: Date.now()
                }));
            }
        }
    });

    // Get CSRF token with caching and fallback methods
    let csrfToken = null;
    function getCookie(name) {
        if (name === 'csrftoken' && csrfToken) {
            return csrfToken;
        }
        
        // Try to get from cookie first
        const v = document.cookie.match('(^|;) ?' + name + '=([^;]*)(;|$)');
        let token = v ? v[2] : null;
        
        // Fallback to meta tag if cookie not found
        if (!token && name === 'csrftoken') {
            const metaTag = document.querySelector('meta[name="csrf-token"]');
            token = metaTag ? metaTag.getAttribute('content') : null;
        }
        
        // Fallback to form input if still not found
        if (!token && name === 'csrftoken') {
            const formInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
            token = formInput ? formInput.value : null;
        }
        
        if (name === 'csrftoken') {
            csrfToken = token;
        }
        
        return token;
    }

    // Performance monitoring and debugging
    function getPerformanceStats() {
        return {
            ...performanceMetrics,
            optimisticMessages: optimisticMessages.size,
            messageCache: messageCache.size,
            messageQueue: messageQueue.length,
            retryQueue: retryQueue.length,
            connectionState: ws ? ws.readyState : 'not_connected',
            isOnline: isOnline
        };
    }

    // Expose performance stats for debugging
    window.getChatPerformanceStats = getPerformanceStats;

    // Initialize everything
    initializeMessageHistory();
    connectWebSocket();
    
    // Focus input on load with slight delay for better UX
    setTimeout(() => {
        if (chatInput) {
            chatInput.focus();
        }
    }, 500);

    // Add CSS animations for optimistic UI
    const style = document.createElement('style');
    style.textContent = `
        .optimistic-message {
            opacity: 0.8;
            transform: scale(0.98);
        }
        
        .message-bubble {
            transition: all 0.2s ease-in-out;
        }
        
        .message-bubble:hover {
            transform: translateY(-1px);
        }
        
        .animate-fade-in {
            animation: fadeIn 0.3s ease-in-out;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .checkmarks {
            transition: all 0.2s ease-in-out;
        }
        
        .connection-indicator {
            transition: all 0.3s ease-in-out;
        }
    `;
    document.head.appendChild(style);

})();
