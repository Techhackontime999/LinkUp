/**
 * Polling Service Module
 * 
 * Provides polling fallback for real-time updates when WebSocket is unavailable.
 * Implements efficient incremental updates by tracking last update timestamps.
 * 
 * Features:
 * - Feed polling (30s interval)
 * - Message polling (15s interval)
 * - Notification polling (60s interval)
 * - Efficient incremental updates (fetch only new content)
 * - Automatic start/stop based on WebSocket availability
 * - State manager integration for UI updates
 */

export class PollingService {
  constructor(apiClient, stateManager) {
    this.apiClient = apiClient;
    this.stateManager = stateManager;
    
    // Polling intervals and timers
    this.feedPollingInterval = 30000; // 30 seconds
    this.messagePollingInterval = 15000; // 15 seconds
    this.notificationPollingInterval = 60000; // 60 seconds
    
    this.feedPollingTimer = null;
    this.messagePollingTimer = null;
    this.notificationPollingTimer = null;
    
    // Track last update timestamps for incremental updates
    this.lastFeedUpdate = null;
    this.lastMessageUpdate = null;
    this.lastNotificationUpdate = null;
    
    // Track active polling
    this.isPollingFeed = false;
    this.isPollingMessages = false;
    this.isPollingNotifications = false;
    
    // Callbacks for new data
    this.onFeedUpdate = null;
    this.onMessageUpdate = null;
    this.onNotificationUpdate = null;
    
    // Error tracking
    this.feedPollingErrors = 0;
    this.messagePollingErrors = 0;
    this.notificationPollingErrors = 0;
    this.maxPollingErrors = 3;
  }

  /**
   * Start polling for feed updates
   * Only polls when WebSocket is unavailable
   * @param {Function} callback - Callback function when new posts are available
   */
  startFeedPolling(callback = null) {
    if (this.isPollingFeed) {
      console.log('Feed polling already active');
      return;
    }

    this.isPollingFeed = true;
    this.onFeedUpdate = callback;
    this.feedPollingErrors = 0;
    
    // Set initial timestamp to now
    this.lastFeedUpdate = new Date().toISOString();
    
    console.log('Starting feed polling (30s interval)');
    
    // Poll immediately, then set interval
    this._pollFeed();
    this.feedPollingTimer = setInterval(() => {
      this._pollFeed();
    }, this.feedPollingInterval);
  }

  /**
   * Stop polling for feed updates
   */
  stopFeedPolling() {
    if (this.feedPollingTimer) {
      clearInterval(this.feedPollingTimer);
      this.feedPollingTimer = null;
    }
    this.isPollingFeed = false;
    console.log('Stopped feed polling');
  }

  /**
   * Start polling for message updates
   * Only polls when WebSocket is unavailable
   * @param {Function} callback - Callback function when new messages are available
   */
  startMessagePolling(callback = null) {
    if (this.isPollingMessages) {
      console.log('Message polling already active');
      return;
    }

    this.isPollingMessages = true;
    this.onMessageUpdate = callback;
    this.messagePollingErrors = 0;
    
    // Set initial timestamp to now
    this.lastMessageUpdate = new Date().toISOString();
    
    console.log('Starting message polling (15s interval)');
    
    // Poll immediately, then set interval
    this._pollMessages();
    this.messagePollingTimer = setInterval(() => {
      this._pollMessages();
    }, this.messagePollingInterval);
  }

  /**
   * Stop polling for message updates
   */
  stopMessagePolling() {
    if (this.messagePollingTimer) {
      clearInterval(this.messagePollingTimer);
      this.messagePollingTimer = null;
    }
    this.isPollingMessages = false;
    console.log('Stopped message polling');
  }

  /**
   * Start polling for notification updates
   * Only polls when WebSocket is unavailable
   * @param {Function} callback - Callback function when new notifications are available
   */
  startNotificationPolling(callback = null) {
    if (this.isPollingNotifications) {
      console.log('Notification polling already active');
      return;
    }

    this.isPollingNotifications = true;
    this.onNotificationUpdate = callback;
    this.notificationPollingErrors = 0;
    
    // Set initial timestamp to now
    this.lastNotificationUpdate = new Date().toISOString();
    
    console.log('Starting notification polling (60s interval)');
    
    // Poll immediately, then set interval
    this._pollNotifications();
    this.notificationPollingTimer = setInterval(() => {
      this._pollNotifications();
    }, this.notificationPollingInterval);
  }

  /**
   * Stop polling for notification updates
   */
  stopNotificationPolling() {
    if (this.notificationPollingTimer) {
      clearInterval(this.notificationPollingTimer);
      this.notificationPollingTimer = null;
    }
    this.isPollingNotifications = false;
    console.log('Stopped notification polling');
  }

  /**
   * Stop all polling
   */
  stopAllPolling() {
    this.stopFeedPolling();
    this.stopMessagePolling();
    this.stopNotificationPolling();
  }

  /**
   * Poll for new feed posts since last update
   * Implements efficient incremental updates
   * @private
   */
  async _pollFeed() {
    try {
      // Fetch only posts created since last update
      const params = {
        since: this.lastFeedUpdate,
        per_page: 50,
      };
      
      const response = await this.apiClient.get('/social/agents/feed/', params);
      
      if (response && response.data && response.data.results) {
        const newPosts = response.data.results;
        
        if (newPosts.length > 0) {
          console.log(`Polling: Found ${newPosts.length} new posts`);
          
          // Update last update timestamp
          this.lastFeedUpdate = new Date().toISOString();
          
          // Update state manager with new posts
          if (this.stateManager) {
            newPosts.forEach(post => {
              this.stateManager.addPostToFeed(post);
            });
          }
          
          // Invoke callback if provided
          if (this.onFeedUpdate && typeof this.onFeedUpdate === 'function') {
            this.onFeedUpdate(newPosts);
          }
        }
        
        // Reset error count on success
        this.feedPollingErrors = 0;
      }
    } catch (error) {
      this.feedPollingErrors++;
      console.error(`Feed polling error (${this.feedPollingErrors}/${this.maxPollingErrors}):`, error);
      
      // Stop polling after max errors
      if (this.feedPollingErrors >= this.maxPollingErrors) {
        console.warn('Feed polling stopped due to repeated errors');
        this.stopFeedPolling();
      }
    }
  }

  /**
   * Poll for new messages since last update
   * Implements efficient incremental updates
   * @private
   */
  async _pollMessages() {
    try {
      // Fetch only messages created since last update
      const params = {
        since: this.lastMessageUpdate,
        per_page: 50,
      };
      
      const response = await this.apiClient.get('/messages/', params);
      
      if (response && response.data && response.data.results) {
        const newMessages = response.data.results;
        
        if (newMessages.length > 0) {
          console.log(`Polling: Found ${newMessages.length} new messages`);
          
          // Update last update timestamp
          this.lastMessageUpdate = new Date().toISOString();
          
          // Invoke callback if provided
          if (this.onMessageUpdate && typeof this.onMessageUpdate === 'function') {
            this.onMessageUpdate(newMessages);
          }
        }
        
        // Reset error count on success
        this.messagePollingErrors = 0;
      }
    } catch (error) {
      this.messagePollingErrors++;
      console.error(`Message polling error (${this.messagePollingErrors}/${this.maxPollingErrors}):`, error);
      
      // Stop polling after max errors
      if (this.messagePollingErrors >= this.maxPollingErrors) {
        console.warn('Message polling stopped due to repeated errors');
        this.stopMessagePolling();
      }
    }
  }

  /**
   * Poll for new notifications since last update
   * Implements efficient incremental updates
   * @private
   */
  async _pollNotifications() {
    try {
      // Fetch only unread notifications created since last update
      const params = {
        since: this.lastNotificationUpdate,
        unread_only: true,
        per_page: 50,
      };
      
      const response = await this.apiClient.get('/social/notifications/', params);
      
      if (response && response.data && response.data.results) {
        const newNotifications = response.data.results;
        
        if (newNotifications.length > 0) {
          console.log(`Polling: Found ${newNotifications.length} new notifications`);
          
          // Update last update timestamp
          this.lastNotificationUpdate = new Date().toISOString();
          
          // Update state manager with new notifications
          if (this.stateManager) {
            newNotifications.forEach(notification => {
              // Add to notifications state
              const currentNotifications = this.stateManager.getState('notifications.items') || [];
              this.stateManager.setState('notifications.items', [notification, ...currentNotifications]);
              
              // Update unread count
              const unreadCount = this.stateManager.getState('notifications.unreadCount') || 0;
              this.stateManager.setState('notifications.unreadCount', unreadCount + 1);
            });
          }
          
          // Invoke callback if provided
          if (this.onNotificationUpdate && typeof this.onNotificationUpdate === 'function') {
            this.onNotificationUpdate(newNotifications);
          }
        }
        
        // Reset error count on success
        this.notificationPollingErrors = 0;
      }
    } catch (error) {
      this.notificationPollingErrors++;
      console.error(`Notification polling error (${this.notificationPollingErrors}/${this.maxPollingErrors}):`, error);
      
      // Stop polling after max errors
      if (this.notificationPollingErrors >= this.maxPollingErrors) {
        console.warn('Notification polling stopped due to repeated errors');
        this.stopNotificationPolling();
      }
    }
  }

  /**
   * Get polling status
   * @returns {Object} Status of all polling operations
   */
  getStatus() {
    return {
      feedPolling: this.isPollingFeed,
      messagePolling: this.isPollingMessages,
      notificationPolling: this.isPollingNotifications,
      lastFeedUpdate: this.lastFeedUpdate,
      lastMessageUpdate: this.lastMessageUpdate,
      lastNotificationUpdate: this.lastNotificationUpdate,
      feedErrors: this.feedPollingErrors,
      messageErrors: this.messagePollingErrors,
      notificationErrors: this.notificationPollingErrors,
    };
  }

  /**
   * Reset polling service
   */
  reset() {
    this.stopAllPolling();
    this.lastFeedUpdate = null;
    this.lastMessageUpdate = null;
    this.lastNotificationUpdate = null;
    this.feedPollingErrors = 0;
    this.messagePollingErrors = 0;
    this.notificationPollingErrors = 0;
  }
}