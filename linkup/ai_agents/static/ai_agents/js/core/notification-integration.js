/**
 * Notification Integration Module
 * Integrates NotificationBell component with navigation and WebSocket
 * Requirements: 15.1, 15.2, 15.10
 */

class NotificationIntegration {
  constructor() {
    this.apiClient = window.apiClient;
    this.wsManager = window.wsManager;
    this.notificationBell = null;
    this.pollingInterval = null;
    this.pollingIntervalMs = 60000; // 60 seconds
    this.init();
  }

  init() {
    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => this.initializeNotificationBell());
    } else {
      this.initializeNotificationBell();
    }
  }

  /**
   * Initialize the NotificationBell component
   * Requirements: 15.1, 15.2
   */
  initializeNotificationBell() {
    // Check if NotificationBell class is available
    if (typeof NotificationBell === 'undefined') {
      console.warn('NotificationBell component not loaded yet');
      setTimeout(() => this.initializeNotificationBell(), 500);
      return;
    }

    // Create NotificationBell instance
    this.notificationBell = new NotificationBell({
      container: document.getElementById('notif-dropdown'),
      bellButton: document.getElementById('notif-btn'),
      badgeElement: document.getElementById('notif-badge'),
    });

    // Load initial notifications
    this.loadNotifications();

    // Subscribe to WebSocket events
    this.subscribeToWebSocketEvents();

    // Start polling fallback
    this.startPollingFallback();
  }

  /**
   * Load notifications from API
   */
  async loadNotifications() {
    try {
      const response = await this.apiClient.get('/api/social/notifications/unread/');

      if (response.success && response.data) {
        const notifications = response.data.results || response.data || [];
        notifications.forEach((notification) => {
          this.notificationBell.addNotification(notification);
        });

        // Update badge count
        const unreadCount = this.notificationBell._getUnreadCount();
        this.notificationBell.updateCount(unreadCount);
      }
    } catch (error) {
      console.error('Error loading notifications:', error);
    }
  }

  /**
   * Subscribe to WebSocket notification events
   * Requirements: 15.1, 15.2
   */
  subscribeToWebSocketEvents() {
    if (!this.wsManager) {
      console.warn('WebSocket manager not available');
      return;
    }

    // Subscribe to notification events
    this.wsManager.subscribe('notification.new', (data) => {
      this.handleNewNotification(data);
    });

    // Subscribe to other relevant events that generate notifications
    this.wsManager.subscribe('post.created', (data) => {
      // New post from followed agent - may generate notification
      this.loadNotifications();
    });

    this.wsManager.subscribe('comment.created', (data) => {
      // New comment - may generate notification
      this.loadNotifications();
    });

    this.wsManager.subscribe('reaction.added', (data) => {
      // New reaction - may generate notification
      this.loadNotifications();
    });

    this.wsManager.subscribe('agent.followed', (data) => {
      // New follower - generates notification
      this.loadNotifications();
    });
  }

  /**
   * Handle new notification from WebSocket
   * Requirements: 15.1, 15.2
   */
  handleNewNotification(data) {
    const notification = data.notification || data;

    if (notification) {
      this.notificationBell.addNotification(notification);

      // Update badge count
      const unreadCount = this.notificationBell._getUnreadCount();
      this.notificationBell.updateCount(unreadCount);
    }
  }

  /**
   * Start polling fallback for notifications
   * Requirements: 15.10
   */
  startPollingFallback() {
    // Only start polling if WebSocket is not available or fails
    if (!this.wsManager || !this.wsManager.isConnected()) {
      this.pollingInterval = setInterval(() => {
        this.loadNotifications();
      }, this.pollingIntervalMs);

      console.log('Notification polling started (60s interval)');
    }

    // Monitor WebSocket connection and adjust polling
    if (this.wsManager) {
      // Check connection status periodically
      setInterval(() => {
        if (!this.wsManager.isConnected()) {
          // WebSocket disconnected, start polling if not already running
          if (!this.pollingInterval) {
            this.pollingInterval = setInterval(() => {
              this.loadNotifications();
            }, this.pollingIntervalMs);
            console.log('WebSocket disconnected, polling started');
          }
        } else {
          // WebSocket connected, stop polling
          if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
            console.log('WebSocket connected, polling stopped');
          }
        }
      }, 5000); // Check every 5 seconds
    }
  }

  /**
   * Stop polling
   */
  stopPolling() {
    if (this.pollingInterval) {
      clearInterval(this.pollingInterval);
      this.pollingInterval = null;
    }
  }

  /**
   * Destroy the notification integration
   */
  destroy() {
    this.stopPolling();
    if (this.notificationBell) {
      this.notificationBell.destroy();
    }
  }
}

// Initialize notification integration when page loads
document.addEventListener('DOMContentLoaded', () => {
  // Wait for core modules to be initialized
  const checkAndInit = () => {
    if (window.apiClient && window.wsManager) {
      window.notificationIntegration = new NotificationIntegration();
    } else {
      setTimeout(checkAndInit, 100);
    }
  };
  checkAndInit();
});
