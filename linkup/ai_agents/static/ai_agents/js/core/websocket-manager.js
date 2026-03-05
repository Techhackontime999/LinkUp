/**
 * WebSocket Manager Module
 * 
 * Manages real-time WebSocket connections with automatic reconnection.
 * Handles event subscriptions and message routing.
 * 
 * Features:
 * - Automatic reconnection with exponential backoff (1s, 2s, 4s, 8s, 16s)
 * - Fallback to polling after 3 failed reconnection attempts
 * - Event subscription system for different message types
 * - Proper error handling and connection state management
 */

export class WebSocketManager {
  constructor(url, authToken = null) {
    this.url = url;
    this.authToken = authToken;
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 3;
    this.reconnectDelay = 1000; // Start with 1 second
    this.subscribers = new Map();
    this.isConnected = false;
    this.reconnectTimer = null;
    this.pollingFallback = false;
    this.pollingCallback = null;
  }

  /**
   * Connect to WebSocket server
   * @returns {Promise<void>}
   */
  connect() {
    // Don't attempt connection if already in polling fallback mode
    if (this.pollingFallback) {
      console.log('WebSocket in polling fallback mode, skipping connection');
      return Promise.resolve();
    }

    return new Promise((resolve, reject) => {
      try {
        // Close existing connection if any
        if (this.ws) {
          this.ws.close();
        }

        this.ws = new WebSocket(this.url);
        
        this.ws.onopen = () => {
          console.log('WebSocket connected');
          this.isConnected = true;
          this.reconnectAttempts = 0;
          this.reconnectDelay = 1000; // Reset delay
          
          // Authenticate if token provided
          if (this.authToken) {
            this.send({ type: 'auth', token: this.authToken });
          }

          // Notify subscribers of connection
          this._notifySubscribers('connection.open', { connected: true });
          
          resolve();
        };

        this.ws.onmessage = (event) => {
          this._handleMessage(event);
        };

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          this.isConnected = false;
          reject(error);
        };

        this.ws.onclose = (event) => {
          this._handleClose(event);
        };
      } catch (error) {
        console.error('WebSocket connection error:', error);
        this.isConnected = false;
        reject(error);
      }
    });
  }

  /**
   * Disconnect from WebSocket server
   */
  disconnect() {
    // Clear any pending reconnection timer
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
      this.isConnected = false;
    }

    // Notify subscribers of disconnection
    this._notifySubscribers('connection.close', { connected: false });
  }

  /**
   * Send message through WebSocket
   * @param {Object} message - Message object to send
   * @returns {boolean} - True if message was sent, false otherwise
   */
  send(message) {
    if (this.ws && this.isConnected && this.ws.readyState === WebSocket.OPEN) {
      try {
        this.ws.send(JSON.stringify(message));
        return true;
      } catch (error) {
        console.error('Error sending WebSocket message:', error);
        return false;
      }
    } else {
      console.warn('WebSocket not connected, message not sent:', message);
      return false;
    }
  }

  /**
   * Subscribe to event type
   * @param {string} eventType - Event type to subscribe to (e.g., 'post.created', 'comment.created')
   * @param {Function} callback - Callback function to invoke when event occurs
   */
  subscribe(eventType, callback) {
    if (typeof callback !== 'function') {
      console.error('Callback must be a function');
      return;
    }

    if (!this.subscribers.has(eventType)) {
      this.subscribers.set(eventType, []);
    }
    this.subscribers.get(eventType).push(callback);
  }

  /**
   * Unsubscribe from event type
   * @param {string} eventType - Event type to unsubscribe from
   * @param {Function} callback - Callback function to remove
   */
  unsubscribe(eventType, callback) {
    if (this.subscribers.has(eventType)) {
      const callbacks = this.subscribers.get(eventType);
      const index = callbacks.indexOf(callback);
      if (index > -1) {
        callbacks.splice(index, 1);
      }
    }
  }

  /**
   * Set polling fallback callback
   * This callback will be invoked when WebSocket fails and polling should be used
   * @param {Function} callback - Function to call to initiate polling
   */
  setPollingFallback(callback) {
    this.pollingCallback = callback;
  }

  /**
   * Check if currently in polling fallback mode
   * @returns {boolean}
   */
  isPollingMode() {
    return this.pollingFallback;
  }

  /**
   * Get connection status
   * @returns {Object} - Connection status information
   */
  getStatus() {
    return {
      connected: this.isConnected,
      pollingMode: this.pollingFallback,
      reconnectAttempts: this.reconnectAttempts,
      maxReconnectAttempts: this.maxReconnectAttempts
    };
  }

  /**
   * Handle incoming WebSocket messages
   * @private
   */
  _handleMessage(event) {
    try {
      const message = JSON.parse(event.data);
      const eventType = message.event;
      
      // Log received message for debugging
      console.debug('WebSocket message received:', eventType, message.data);
      
      this._notifySubscribers(eventType, message.data);
    } catch (error) {
      console.error('Error parsing WebSocket message:', error, event.data);
    }
  }

  /**
   * Notify all subscribers of an event
   * @private
   */
  _notifySubscribers(eventType, data) {
    if (this.subscribers.has(eventType)) {
      const callbacks = this.subscribers.get(eventType);
      callbacks.forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error(`Error in subscriber callback for ${eventType}:`, error);
        }
      });
    }
  }

  /**
   * Handle WebSocket close event
   * @private
   */
  _handleClose(event) {
    console.log('WebSocket disconnected', event ? `(code: ${event.code})` : '');
    this.isConnected = false;

    // Don't reconnect if close was intentional (code 1000)
    if (event && event.code === 1000) {
      console.log('WebSocket closed normally, not reconnecting');
      return;
    }

    // Attempt reconnection
    this._reconnect();
  }

  /**
   * Attempt to reconnect with exponential backoff
   * Implements exponential backoff: 1s, 2s, 4s, 8s, 16s
   * Falls back to polling after 3 failed attempts
   * @private
   */
  _reconnect() {
    // Clear any existing reconnect timer
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    // Check if max reconnection attempts reached
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.warn(`Max reconnection attempts (${this.maxReconnectAttempts}) reached, falling back to polling`);
      this._enablePollingFallback();
      return;
    }

    this.reconnectAttempts++;
    
    // Calculate exponential backoff delay: 1s, 2s, 4s, 8s, 16s
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    
    console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
    
    this.reconnectTimer = setTimeout(() => {
      console.log(`Attempting reconnection (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
      this.connect().catch(error => {
        console.error('Reconnection attempt failed:', error);
        // The onclose handler will trigger another reconnect attempt
      });
    }, delay);
  }

  /**
   * Enable polling fallback mode
   * @private
   */
  _enablePollingFallback() {
    this.pollingFallback = true;
    
    // Notify subscribers that we're switching to polling mode
    this._notifySubscribers('connection.polling', { pollingMode: true });
    
    // Invoke polling callback if set
    if (this.pollingCallback && typeof this.pollingCallback === 'function') {
      console.log('Initiating polling fallback');
      try {
        this.pollingCallback();
      } catch (error) {
        console.error('Error in polling fallback callback:', error);
      }
    } else {
      console.warn('No polling fallback callback set. Real-time updates will not be available.');
    }
  }
}

// Export singleton instance (will be initialized when needed)
export let websocketManager = null;

export function initWebSocketManager(url, authToken) {
  websocketManager = new WebSocketManager(url, authToken);
  return websocketManager;
}
