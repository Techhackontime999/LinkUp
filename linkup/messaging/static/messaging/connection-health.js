/**
 * Connection Health Monitor for WhatsApp-like Messaging System
 * 
 * Provides comprehensive connection health monitoring, heartbeat management,
 * and connection quality indicators for real-time messaging.
 * 
 * Features:
 * - 30-second WebSocket heartbeat pings
 * - Connection health indicators with RTT measurement
 * - Automatic reconnection with exponential backoff
 * - Connection quality assessment and display
 * - Network change detection and handling
 */

(function() {
    'use strict';
    
    // Configuration constants
    const CONFIG = {
        HEARTBEAT_INTERVAL: 30000,      // 30 seconds
        HEALTH_CHECK_INTERVAL: 5000,    // 5 seconds
        CONNECTION_TIMEOUT: 60000,      // 1 minute
        MAX_RECONNECT_ATTEMPTS: 10,
        RECONNECT_BASE_DELAY: 1000,     // 1 second
        RECONNECT_MAX_DELAY: 30000,     // 30 seconds
        RTT_SAMPLES: 10,                // Number of RTT samples to keep
        QUALITY_THRESHOLDS: {
            EXCELLENT: 100,   // < 100ms
            GOOD: 300,        // < 300ms
            FAIR: 800,        // < 800ms
            POOR: 1500        // < 1500ms
            // > 1500ms = Very Poor
        }
    };
    
    class ConnectionHealthMonitor {
        constructor() {
            this.isActive = false;
            this.heartbeatInterval = null;
            this.healthCheckInterval = null;
            this.reconnectTimeout = null;
            
            // Connection state
            this.connectionState = 'disconnected';
            this.lastHeartbeat = null;
            this.lastPong = null;
            this.reconnectAttempts = 0;
            
            // Performance metrics
            this.rttSamples = [];
            this.averageRtt = 0;
            this.connectionQuality = 'unknown';
            this.packetsLost = 0;
            this.totalPackets = 0;
            
            // Callbacks
            this.onConnectionStateChange = null;
            this.onQualityChange = null;
            this.onReconnectAttempt = null;
            
            // Network detection
            this.networkType = this.detectNetworkType();
            this.isOnline = navigator.onLine;
            
            this.bindEvents();
        }
        
        /**
         * Start connection health monitoring
         * @param {WebSocket} websocket - WebSocket connection to monitor
         * @param {Object} callbacks - Event callbacks
         */
        start(websocket, callbacks = {}) {
            if (this.isActive) {
                this.stop();
            }
            
            this.websocket = websocket;
            this.onConnectionStateChange = callbacks.onConnectionStateChange;
            this.onQualityChange = callbacks.onQualityChange;
            this.onReconnectAttempt = callbacks.onReconnectAttempt;
            
            this.isActive = true;
            this.connectionState = 'connected';
            this.reconnectAttempts = 0;
            
            this.startHeartbeat();
            this.startHealthCheck();
            
            this.notifyStateChange('connected', 'Connection established');
            
            console.log('Connection health monitoring started');
        }
        
        /**
         * Stop connection health monitoring
         */
        stop() {
            this.isActive = false;
            
            if (this.heartbeatInterval) {
                clearInterval(this.heartbeatInterval);
                this.heartbeatInterval = null;
            }
            
            if (this.healthCheckInterval) {
                clearInterval(this.healthCheckInterval);
                this.healthCheckInterval = null;
            }
            
            if (this.reconnectTimeout) {
                clearTimeout(this.reconnectTimeout);
                this.reconnectTimeout = null;
            }
            
            this.connectionState = 'disconnected';
            this.notifyStateChange('disconnected', 'Monitoring stopped');
            
            console.log('Connection health monitoring stopped');
        }
        
        /**
         * Start heartbeat mechanism
         */
        startHeartbeat() {
            if (this.heartbeatInterval) {
                clearInterval(this.heartbeatInterval);
            }
            
            this.heartbeatInterval = setInterval(() => {
                this.sendHeartbeat();
            }, CONFIG.HEARTBEAT_INTERVAL);
            
            // Send initial heartbeat
            setTimeout(() => this.sendHeartbeat(), 1000);
        }
        
        /**
         * Start health check mechanism
         */
        startHealthCheck() {
            if (this.healthCheckInterval) {
                clearInterval(this.healthCheckInterval);
            }
            
            this.healthCheckInterval = setInterval(() => {
                this.checkConnectionHealth();
            }, CONFIG.HEALTH_CHECK_INTERVAL);
        }
        
        /**
         * Send heartbeat ping
         */
        sendHeartbeat() {
            if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
                return;
            }
            
            const timestamp = Date.now();
            this.lastHeartbeat = timestamp;
            this.totalPackets++;
            
            try {
                this.websocket.send(JSON.stringify({
                    type: 'ping',
                    timestamp: timestamp,
                    sequence: this.totalPackets
                }));
            } catch (error) {
                console.error('Failed to send heartbeat:', error);
                this.handleConnectionError('heartbeat_failed');
            }
        }
        
        /**
         * Handle pong response
         * @param {Object} data - Pong message data
         */
        handlePong(data) {
            const now = Date.now();
            this.lastPong = now;
            
            if (data.timestamp) {
                const rtt = now - data.timestamp;
                this.updateRttMetrics(rtt);
                this.updateConnectionQuality(rtt);
            }
            
            // Reset connection state if it was unhealthy
            if (this.connectionState !== 'connected') {
                this.connectionState = 'connected';
                this.reconnectAttempts = 0;
                this.notifyStateChange('connected', 'Connection restored');
            }
        }
        
        /**
         * Check overall connection health
         */
        checkConnectionHealth() {
            if (!this.isActive || !this.websocket) {
                return;
            }
            
            const now = Date.now();
            const timeSinceLastPong = this.lastPong ? now - this.lastPong : Infinity;
            const timeSinceLastHeartbeat = this.lastHeartbeat ? now - this.lastHeartbeat : 0;
            
            // Check if connection is stale
            if (timeSinceLastPong > CONFIG.CONNECTION_TIMEOUT) {
                this.handleConnectionError('timeout');
                return;
            }
            
            // Check WebSocket state
            if (this.websocket.readyState === WebSocket.CLOSED || 
                this.websocket.readyState === WebSocket.CLOSING) {
                this.handleConnectionError('websocket_closed');
                return;
            }
            
            // Check for missed heartbeats
            if (timeSinceLastHeartbeat > CONFIG.HEARTBEAT_INTERVAL * 2) {
                console.warn('Missed heartbeat detected');
                this.sendHeartbeat(); // Try to send heartbeat immediately
            }
            
            // Update packet loss statistics
            this.updatePacketLossStats();
        }
        
        /**
         * Handle connection errors
         * @param {string} errorType - Type of error
         */
        handleConnectionError(errorType) {
            console.warn(`Connection error detected: ${errorType}`);
            
            if (this.connectionState === 'connected') {
                this.connectionState = 'unhealthy';
                this.notifyStateChange('unhealthy', `Connection issue: ${errorType}`);
            }
            
            // Attempt to recover
            this.attemptReconnection();
        }
        
        /**
         * Attempt to reconnect with exponential backoff
         */
        attemptReconnection() {
            if (this.reconnectAttempts >= CONFIG.MAX_RECONNECT_ATTEMPTS) {
                this.connectionState = 'failed';
                this.notifyStateChange('failed', 'Max reconnection attempts reached');
                return;
            }
            
            this.reconnectAttempts++;
            
            // Calculate delay with exponential backoff
            const delay = Math.min(
                CONFIG.RECONNECT_BASE_DELAY * Math.pow(2, this.reconnectAttempts - 1),
                CONFIG.RECONNECT_MAX_DELAY
            );
            
            this.connectionState = 'reconnecting';
            this.notifyStateChange('reconnecting', `Reconnecting... (${this.reconnectAttempts}/${CONFIG.MAX_RECONNECT_ATTEMPTS})`);
            
            if (this.onReconnectAttempt) {
                this.onReconnectAttempt(this.reconnectAttempts, delay);
            }
            
            this.reconnectTimeout = setTimeout(() => {
                this.initiateReconnection();
            }, delay);
        }
        
        /**
         * Initiate actual reconnection
         */
        initiateReconnection() {
            if (this.websocket) {
                try {
                    this.websocket.close();
                } catch (error) {
                    console.warn('Error closing websocket during reconnection:', error);
                }
            }
            
            // Trigger reconnection through callback
            if (this.onReconnectAttempt) {
                this.onReconnectAttempt(this.reconnectAttempts, 0, true);
            }
        }
        
        /**
         * Update RTT metrics
         * @param {number} rtt - Round trip time in milliseconds
         */
        updateRttMetrics(rtt) {
            this.rttSamples.push(rtt);
            
            // Keep only recent samples
            if (this.rttSamples.length > CONFIG.RTT_SAMPLES) {
                this.rttSamples.shift();
            }
            
            // Calculate average RTT
            this.averageRtt = this.rttSamples.reduce((sum, sample) => sum + sample, 0) / this.rttSamples.length;
        }
        
        /**
         * Update connection quality based on RTT
         * @param {number} rtt - Current round trip time
         */
        updateConnectionQuality(rtt) {
            let newQuality;
            
            if (rtt < CONFIG.QUALITY_THRESHOLDS.EXCELLENT) {
                newQuality = 'excellent';
            } else if (rtt < CONFIG.QUALITY_THRESHOLDS.GOOD) {
                newQuality = 'good';
            } else if (rtt < CONFIG.QUALITY_THRESHOLDS.FAIR) {
                newQuality = 'fair';
            } else if (rtt < CONFIG.QUALITY_THRESHOLDS.POOR) {
                newQuality = 'poor';
            } else {
                newQuality = 'very-poor';
            }
            
            if (newQuality !== this.connectionQuality) {
                const oldQuality = this.connectionQuality;
                this.connectionQuality = newQuality;
                
                if (this.onQualityChange) {
                    this.onQualityChange(newQuality, oldQuality, rtt);
                }
            }
        }
        
        /**
         * Update packet loss statistics
         */
        updatePacketLossStats() {
            // Simple packet loss calculation based on missed pongs
            const expectedPongs = Math.floor((Date.now() - (this.lastHeartbeat || Date.now())) / CONFIG.HEARTBEAT_INTERVAL);
            const receivedPongs = this.rttSamples.length;
            
            if (expectedPongs > 0) {
                this.packetsLost = Math.max(0, expectedPongs - receivedPongs);
            }
        }
        
        /**
         * Detect network type
         */
        detectNetworkType() {
            if ('connection' in navigator) {
                const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
                return connection ? connection.effectiveType || connection.type : 'unknown';
            }
            return 'unknown';
        }
        
        /**
         * Bind network and visibility events
         */
        bindEvents() {
            // Online/offline events
            window.addEventListener('online', () => {
                this.isOnline = true;
                console.log('Network came online');
                if (this.connectionState !== 'connected') {
                    this.attemptReconnection();
                }
            });
            
            window.addEventListener('offline', () => {
                this.isOnline = false;
                console.log('Network went offline');
                this.connectionState = 'offline';
                this.notifyStateChange('offline', 'Network offline');
            });
            
            // Network change events
            if ('connection' in navigator) {
                const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
                if (connection) {
                    connection.addEventListener('change', () => {
                        const newType = connection.effectiveType || connection.type;
                        if (newType !== this.networkType) {
                            console.log(`Network type changed: ${this.networkType} -> ${newType}`);
                            this.networkType = newType;
                            
                            // Adjust heartbeat interval based on network type
                            this.adjustHeartbeatForNetwork(newType);
                        }
                    });
                }
            }
            
            // Page visibility changes
            document.addEventListener('visibilitychange', () => {
                if (document.hidden) {
                    // Page hidden - reduce heartbeat frequency
                    this.adjustHeartbeatInterval(CONFIG.HEARTBEAT_INTERVAL * 2);
                } else {
                    // Page visible - restore normal heartbeat
                    this.adjustHeartbeatInterval(CONFIG.HEARTBEAT_INTERVAL);
                    
                    // Send immediate heartbeat to check connection
                    setTimeout(() => this.sendHeartbeat(), 100);
                }
            });
        }
        
        /**
         * Adjust heartbeat interval
         * @param {number} interval - New interval in milliseconds
         */
        adjustHeartbeatInterval(interval) {
            if (this.heartbeatInterval) {
                clearInterval(this.heartbeatInterval);
                this.heartbeatInterval = setInterval(() => {
                    this.sendHeartbeat();
                }, interval);
            }
        }
        
        /**
         * Adjust heartbeat based on network type
         * @param {string} networkType - Network type
         */
        adjustHeartbeatForNetwork(networkType) {
            let multiplier = 1;
            
            switch (networkType) {
                case 'slow-2g':
                    multiplier = 3;
                    break;
                case '2g':
                    multiplier = 2;
                    break;
                case '3g':
                    multiplier = 1.5;
                    break;
                case '4g':
                case '5g':
                default:
                    multiplier = 1;
                    break;
            }
            
            const adjustedInterval = CONFIG.HEARTBEAT_INTERVAL * multiplier;
            this.adjustHeartbeatInterval(adjustedInterval);
            
            console.log(`Adjusted heartbeat interval for ${networkType}: ${adjustedInterval}ms`);
        }
        
        /**
         * Notify state change
         * @param {string} state - New connection state
         * @param {string} message - State change message
         */
        notifyStateChange(state, message) {
            if (this.onConnectionStateChange) {
                this.onConnectionStateChange(state, message, this.getConnectionStats());
            }
        }
        
        /**
         * Get connection statistics
         * @returns {Object} Connection statistics
         */
        getConnectionStats() {
            return {
                state: this.connectionState,
                quality: this.connectionQuality,
                averageRtt: Math.round(this.averageRtt),
                packetsLost: this.packetsLost,
                totalPackets: this.totalPackets,
                packetLossRate: this.totalPackets > 0 ? (this.packetsLost / this.totalPackets * 100).toFixed(2) : 0,
                reconnectAttempts: this.reconnectAttempts,
                networkType: this.networkType,
                isOnline: this.isOnline,
                lastHeartbeat: this.lastHeartbeat,
                lastPong: this.lastPong
            };
        }
        
        /**
         * Get connection quality color for UI
         * @returns {string} CSS color class
         */
        getQualityColor() {
            const colors = {
                'excellent': 'text-green-500',
                'good': 'text-blue-500',
                'fair': 'text-yellow-500',
                'poor': 'text-orange-500',
                'very-poor': 'text-red-500',
                'unknown': 'text-gray-500'
            };
            
            return colors[this.connectionQuality] || colors.unknown;
        }
        
        /**
         * Get connection quality icon
         * @returns {string} Icon HTML
         */
        getQualityIcon() {
            const icons = {
                'excellent': '📶',
                'good': '📶',
                'fair': '📶',
                'poor': '📶',
                'very-poor': '📶',
                'unknown': '❓'
            };
            
            return icons[this.connectionQuality] || icons.unknown;
        }
        
        /**
         * Force connection health check
         */
        forceHealthCheck() {
            this.checkConnectionHealth();
            this.sendHeartbeat();
        }
        
        /**
         * Reset connection statistics
         */
        resetStats() {
            this.rttSamples = [];
            this.averageRtt = 0;
            this.packetsLost = 0;
            this.totalPackets = 0;
            this.reconnectAttempts = 0;
        }
    }
    
    // Export to global scope
    window.ConnectionHealthMonitor = ConnectionHealthMonitor;
    
    // Create default instance
    window.connectionHealthMonitor = new ConnectionHealthMonitor();
    
})();