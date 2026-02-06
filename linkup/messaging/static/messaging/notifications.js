/**
 * Comprehensive Real-time Notification System
 * Handles WebSocket connections, notification display, and user interactions
 */
class NotificationSystem {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.isConnected = false;
        this.notifications = [];
        this.unreadCount = 0;
        
        // Initialize DOM elements immediately
        this.initializeDOMElements();
    }
    
    initializeDOMElements() {
        // DOM elements
        this.badge = document.getElementById('notif-badge');
        this.list = document.getElementById('notif-list');
        this.dropdown = document.getElementById('notif-dropdown');
        this.btn = document.getElementById('notif-btn');
        this.loadMoreBtn = document.getElementById('load-more-notifications');
        this.markAllReadBtn = document.getElementById('mark-all-read');
        
        // Pagination
        this.currentOffset = 0;
        this.pageSize = 20;
        this.hasMore = true;
    }
    
    init() {
        if (!this.btn) {
            console.log('No notification UI on this page');
            return; // No notification UI on this page
        }
        
        console.log('Initializing notification system...');
        this.setupEventListeners();
        this.connectWebSocket();
        this.loadInitialNotifications();
        
        // Periodic fallback polling
        setInterval(() => this.pollFallback(), 30000);
    }
    
    setupEventListeners() {
        // Toggle dropdown
        if (this.btn) {
            this.btn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('Notification button clicked!');
                this.toggleDropdown();
            });
        }
        
        // Mark all as read
        if (this.markAllReadBtn) {
            this.markAllReadBtn.addEventListener('click', () => {
                this.markAllAsRead();
            });
        }
        
        // Load more notifications
        if (this.loadMoreBtn) {
            this.loadMoreBtn.addEventListener('click', () => {
                this.loadMoreNotifications();
            });
        }
        
        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (this.dropdown && !this.dropdown.contains(e.target) && !this.btn.contains(e.target)) {
                this.closeDropdown();
            }
        });
        
        // Handle visibility change for connection management
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible' && !this.isConnected) {
                this.connectWebSocket();
            }
        });
    }
    
    connectWebSocket() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            return; // Already connected
        }
        
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/notifications/`;
        
        try {
            this.ws = new WebSocket(wsUrl);
            
            this.ws.addEventListener('open', () => {
                console.log('Notification WebSocket connected');
                this.isConnected = true;
                this.reconnectAttempts = 0;
                this.showConnectionStatus('connected');
            });
            
            this.ws.addEventListener('message', (event) => {
                this.handleWebSocketMessage(event);
            });
            
            this.ws.addEventListener('close', (event) => {
                console.log('Notification WebSocket closed:', event.code, event.reason);
                this.isConnected = false;
                this.showConnectionStatus('disconnected');
                this.scheduleReconnect();
            });
            
            this.ws.addEventListener('error', (error) => {
                console.error('Notification WebSocket error:', error);
                this.isConnected = false;
                this.showConnectionStatus('error');
            });
            
        } catch (error) {
            console.error('Failed to create WebSocket connection:', error);
            this.scheduleReconnect();
        }
    }
    
    handleWebSocketMessage(event) {
        try {
            const data = JSON.parse(event.data);
            
            switch (data.type) {
                case 'notification':
                    this.handleNewNotification(data.notification);
                    break;
                case 'badge_update':
                    this.updateBadgeCount(data.unread_count);
                    break;
                case 'mark_read_response':
                    this.handleMarkReadResponse(data);
                    break;
                case 'mark_all_read_response':
                    this.handleMarkAllReadResponse(data);
                    break;
                case 'notifications_list':
                    this.handleNotificationsList(data);
                    break;
                case 'pong':
                    // Health check response
                    break;
                default:
                    console.log('Unknown notification message type:', data.type);
            }
        } catch (error) {
            console.error('Error parsing WebSocket message:', error);
        }
    }
    
    handleNewNotification(notification) {
        // Add to notifications array
        this.notifications.unshift(notification);
        
        // Update badge count
        this.updateBadgeCount(notification.unread_count);
        
        // Add to UI
        this.addNotificationToUI(notification);
        
        // Show browser notification if supported and permission granted
        this.showBrowserNotification(notification);
        
        // Play notification sound
        this.playNotificationSound();
        
        console.log('New notification received:', notification);
    }
    
    addNotificationToUI(notification) {
        const element = this.createNotificationElement(notification);
        
        // Add to top of list
        if (this.list.firstChild) {
            this.list.insertBefore(element, this.list.firstChild);
        } else {
            this.list.appendChild(element);
        }
        
        // Limit displayed notifications to prevent memory issues
        const maxDisplayed = 50;
        while (this.list.children.length > maxDisplayed) {
            this.list.removeChild(this.list.lastChild);
        }
    }
    
    createNotificationElement(notification) {
        const element = document.createElement('div');
        element.className = `notification-item p-3 border-b border-gray-100 hover:bg-gray-50 cursor-pointer ${!notification.is_read ? 'bg-blue-50' : ''}`;
        element.dataset.notificationId = notification.id;
        
        const timeAgo = this.formatTimeAgo(new Date(notification.created_at));
        const priorityClass = this.getPriorityClass(notification.priority);
        
        element.innerHTML = `
            <div class="flex items-start space-x-3">
                ${notification.sender_avatar ? 
                    `<img src="${notification.sender_avatar}" alt="${notification.sender}" class="w-8 h-8 rounded-full">` :
                    `<div class="w-8 h-8 rounded-full bg-purple-500 flex items-center justify-center text-white text-sm font-medium">
                        ${notification.sender ? notification.sender.charAt(0).toUpperCase() : 'S'}
                    </div>`
                }
                <div class="flex-1 min-w-0">
                    <div class="flex items-center justify-between">
                        <p class="text-sm font-medium text-gray-900 truncate">
                            ${notification.title}
                            ${notification.is_grouped && notification.group_count > 1 ? 
                                `<span class="ml-2 px-2 py-1 text-xs bg-gray-200 text-gray-700 rounded-full">${notification.group_count}</span>` : 
                                ''
                            }
                        </p>
                        <div class="flex items-center space-x-2">
                            ${priorityClass ? `<span class="w-2 h-2 rounded-full ${priorityClass}"></span>` : ''}
                            <span class="text-xs text-gray-500">${timeAgo}</span>
                        </div>
                    </div>
                    <p class="text-sm text-gray-600 mt-1">${notification.message}</p>
                    ${!notification.is_read ? 
                        `<button class="mark-read-btn text-xs text-purple-600 hover:text-purple-800 mt-2" data-notification-id="${notification.id}">
                            Mark as read
                        </button>` : 
                        ''
                    }
                </div>
            </div>
        `;
        
        // Add click handlers
        element.addEventListener('click', (e) => {
            if (e.target.classList.contains('mark-read-btn')) {
                e.stopPropagation();
                this.markNotificationAsRead(notification.id);
            } else {
                this.handleNotificationClick(notification);
            }
        });
        
        return element;
    }
    
    getPriorityClass(priority) {
        switch (priority) {
            case 'urgent': return 'bg-red-500';
            case 'high': return 'bg-orange-500';
            case 'normal': return 'bg-blue-500';
            case 'low': return 'bg-gray-400';
            default: return '';
        }
    }
    
    formatTimeAgo(date) {
        const now = new Date();
        const diffInSeconds = Math.floor((now - date) / 1000);
        
        if (diffInSeconds < 60) return 'Just now';
        if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
        if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
        if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)}d ago`;
        
        return date.toLocaleDateString();
    }
    
    handleNotificationClick(notification) {
        // Mark as read if not already
        if (!notification.is_read) {
            this.markNotificationAsRead(notification.id);
        }
        
        // Navigate to action URL if available
        if (notification.action_url) {
            window.location.href = notification.action_url;
        }
        
        // Close dropdown
        this.closeDropdown();
    }
    
    markNotificationAsRead(notificationId) {
        // Send WebSocket message
        if (this.isConnected) {
            this.ws.send(JSON.stringify({
                type: 'mark_read',
                notification_id: notificationId
            }));
        }
        
        // Fallback HTTP request
        fetch(`/messages/notifications/${notificationId}/read/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': this.getCSRFToken(),
                'Content-Type': 'application/json'
            },
            credentials: 'same-origin'
        }).then(response => {
            if (response.ok) {
                this.updateNotificationReadStatus(notificationId, true);
            }
        }).catch(error => {
            console.error('Error marking notification as read:', error);
        });
    }
    
    markAllAsRead() {
        // Send WebSocket message
        if (this.isConnected) {
            this.ws.send(JSON.stringify({
                type: 'mark_all_read'
            }));
        }
        
        // Fallback HTTP request
        fetch('/messages/notifications/mark-all-read/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': this.getCSRFToken(),
                'Content-Type': 'application/json'
            },
            credentials: 'same-origin'
        }).then(response => response.json()).then(data => {
            if (data.success) {
                this.updateAllNotificationsReadStatus();
                this.updateBadgeCount(0);
            }
        }).catch(error => {
            console.error('Error marking all notifications as read:', error);
        });
    }
    
    updateNotificationReadStatus(notificationId, isRead) {
        // Update in notifications array
        const notification = this.notifications.find(n => n.id == notificationId);
        if (notification) {
            notification.is_read = isRead;
        }
        
        // Update UI element
        const element = document.querySelector(`[data-notification-id="${notificationId}"]`);
        if (element) {
            if (isRead) {
                element.classList.remove('bg-blue-50');
                const markReadBtn = element.querySelector('.mark-read-btn');
                if (markReadBtn) {
                    markReadBtn.remove();
                }
            } else {
                element.classList.add('bg-blue-50');
            }
        }
    }
    
    updateAllNotificationsReadStatus() {
        // Update all notifications in array
        this.notifications.forEach(notification => {
            notification.is_read = true;
        });
        
        // Update all UI elements
        document.querySelectorAll('.notification-item').forEach(element => {
            element.classList.remove('bg-blue-50');
            const markReadBtn = element.querySelector('.mark-read-btn');
            if (markReadBtn) {
                markReadBtn.remove();
            }
        });
    }
    
    loadInitialNotifications() {
        fetch(`/messages/notifications/?limit=${this.pageSize}&offset=0`, {
            credentials: 'same-origin'
        }).then(response => response.json()).then(data => {
            this.notifications = data.notifications || [];
            this.updateBadgeCount(data.total_unread || 0);
            this.renderNotifications();
            this.hasMore = data.has_more || false;
            this.updateLoadMoreButton();
        }).catch(error => {
            console.error('Error loading initial notifications:', error);
            this.pollFallback(); // Fallback to old system
        });
    }
    
    loadMoreNotifications() {
        if (!this.hasMore) return;
        
        this.currentOffset += this.pageSize;
        
        fetch(`/messages/notifications/?limit=${this.pageSize}&offset=${this.currentOffset}`, {
            credentials: 'same-origin'
        }).then(response => response.json()).then(data => {
            const newNotifications = data.notifications || [];
            this.notifications.push(...newNotifications);
            this.renderAdditionalNotifications(newNotifications);
            this.hasMore = data.has_more || false;
            this.updateLoadMoreButton();
        }).catch(error => {
            console.error('Error loading more notifications:', error);
        });
    }
    
    renderNotifications() {
        this.list.innerHTML = '';
        this.notifications.forEach(notification => {
            this.list.appendChild(this.createNotificationElement(notification));
        });
    }
    
    renderAdditionalNotifications(notifications) {
        notifications.forEach(notification => {
            this.list.appendChild(this.createNotificationElement(notification));
        });
    }
    
    updateLoadMoreButton() {
        if (this.loadMoreBtn) {
            this.loadMoreBtn.style.display = this.hasMore ? 'block' : 'none';
        }
    }
    
    updateBadgeCount(count) {
        this.unreadCount = count;
        
        // Update desktop badge
        if (this.badge) {
            if (count > 0) {
                this.badge.style.display = 'flex';
                this.badge.textContent = count > 99 ? '99+' : String(count);
            } else {
                this.badge.style.display = 'none';
            }
        }
        
        // Update mobile badge
        const mobileBadge = document.getElementById('mobile-messages-badge');
        if (mobileBadge) {
            if (count > 0) {
                mobileBadge.style.display = 'flex';
                mobileBadge.textContent = count > 99 ? '99+' : String(count);
            } else {
                mobileBadge.style.display = 'none';
            }
        }
    }
    
    toggleDropdown() {
        console.log('=== NOTIFICATION DEBUG ===');
        console.log('toggleDropdown called');
        console.log('dropdown element:', this.dropdown);
        console.log('btn element:', this.btn);
        console.log('dropdown classes:', this.dropdown ? this.dropdown.className : 'NOT FOUND');
        console.log('btn classes:', this.btn ? this.btn.className : 'NOT FOUND');
        
        if (!this.dropdown) {
            console.error('Dropdown element not found!');
            return;
        }
        
        if (!this.btn) {
            console.error('Button element not found!');
            return;
        }
        
        const isHidden = this.dropdown.classList.contains('hidden');
        console.log('Dropdown is hidden:', isHidden);
        
        if (isHidden) {
            console.log('Opening dropdown...');
            // Show dropdown
            this.dropdown.classList.remove('hidden');
            this.dropdown.classList.add('block');
            this.btn.setAttribute('aria-expanded', 'true');
            
            // Load fresh notifications when opening
            this.loadInitialNotifications();
            
            // Add click outside listener
            this.addClickOutsideListener();
            
            console.log('Notification dropdown opened successfully');
        } else {
            console.log('Closing dropdown...');
            // Hide dropdown
            this.closeDropdown();
        }
        
        console.log('=== END DEBUG ===');
    }
    
    closeDropdown() {
        if (this.dropdown) {
            this.dropdown.classList.add('hidden');
            this.dropdown.classList.remove('block');
            this.btn.setAttribute('aria-expanded', 'false');
            this.removeClickOutsideListener();
            console.log('Notification dropdown closed');
        }
    }
    
    addClickOutsideListener() {
        this.clickOutsideHandler = (e) => {
            if (!this.dropdown.contains(e.target) && !this.btn.contains(e.target)) {
                this.closeDropdown();
            }
        };
        document.addEventListener('click', this.clickOutsideHandler);
    }
    
    removeClickOutsideListener() {
        if (this.clickOutsideHandler) {
            document.removeEventListener('click', this.clickOutsideHandler);
            this.clickOutsideHandler = null;
        }
    }
    
    showBrowserNotification(notification) {
        if ('Notification' in window && Notification.permission === 'granted') {
            const browserNotification = new Notification(notification.title, {
                body: notification.message,
                icon: notification.sender_avatar || '/static/images/notification-icon.png',
                tag: `notification-${notification.id}`,
                requireInteraction: notification.priority === 'urgent'
            });
            
            browserNotification.onclick = () => {
                window.focus();
                this.handleNotificationClick(notification);
                browserNotification.close();
            };
            
            // Auto-close after 5 seconds for non-urgent notifications
            if (notification.priority !== 'urgent') {
                setTimeout(() => browserNotification.close(), 5000);
            }
        }
    }
    
    playNotificationSound() {
        // Only play sound if user has interacted with the page
        if (document.hasFocus()) {
            const audio = new Audio('/static/sounds/notification.mp3');
            audio.volume = 0.3;
            audio.play().catch(() => {
                // Ignore audio play errors (user hasn't interacted with page yet)
            });
        }
    }
    
    showConnectionStatus(status) {
        // Show connection status indicator
        const indicator = document.getElementById('connection-status');
        if (indicator) {
            indicator.className = `connection-status ${status}`;
            indicator.textContent = status === 'connected' ? '●' : status === 'error' ? '⚠' : '○';
        }
    }
    
    scheduleReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
            
            console.log(`Scheduling WebSocket reconnect attempt ${this.reconnectAttempts} in ${delay}ms`);
            
            setTimeout(() => {
                this.connectWebSocket();
            }, delay);
        } else {
            console.log('Max reconnection attempts reached, falling back to polling');
            this.pollFallback();
        }
    }
    
    pollFallback() {
        // Fallback to HTTP polling when WebSocket is unavailable
        fetch('/messages/unread/', {
            credentials: 'same-origin'
        }).then(response => response.json()).then(data => {
            this.updateBadgeCount(data.total_unread || 0);
            
            // Update message previews if available
            if (data.messages && data.messages.items) {
                // This is legacy support for the old message-only system
                // The new system uses the notifications endpoint
            }
        }).catch(error => {
            console.error('Error in polling fallback:', error);
        });
    }
    
    getCSRFToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    }
    
    // Handle WebSocket responses
    handleMarkReadResponse(data) {
        if (data.success) {
            this.updateNotificationReadStatus(data.notification_id, true);
            this.unreadCount = Math.max(0, this.unreadCount - 1);
            this.updateBadgeCount(this.unreadCount);
        }
    }
    
    handleMarkAllReadResponse(data) {
        this.updateAllNotificationsReadStatus();
        this.updateBadgeCount(0);
    }
    
    handleNotificationsList(data) {
        this.notifications = data.notifications || [];
        this.renderNotifications();
        this.hasMore = data.has_more || false;
        this.updateLoadMoreButton();
    }
    
    // Request browser notification permission
    requestNotificationPermission() {
        if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission().then(permission => {
                console.log('Notification permission:', permission);
            });
        }
    }
}

// Initialize notification system when DOM is ready
function initializeNotificationSystem() {
    if (!window.notificationSystem) {
        window.notificationSystem = new NotificationSystem();
        window.notificationSystem.init();
    }
}

// Initialize immediately if DOM is already loaded, otherwise wait for DOMContentLoaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeNotificationSystem);
} else {
    initializeNotificationSystem();
}

// Legacy support for existing code
(function(){
    // Keep the old function names for backward compatibility
    window.setNotificationCount = function(count) {
        if (window.notificationSystem) {
            window.notificationSystem.updateBadgeCount(count);
        }
    };
    
    window.addNotificationPreview = function(notification) {
        if (window.notificationSystem) {
            window.notificationSystem.addNotificationToUI(notification);
        }
    };
    
    // Request notification permission on first user interaction
    document.addEventListener('click', () => {
        if (window.notificationSystem) {
            window.notificationSystem.requestNotificationPermission();
        }
    }, { once: true });
})();