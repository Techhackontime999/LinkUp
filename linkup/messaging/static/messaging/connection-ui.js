/**
 * Connection Health UI Component
 * 
 * Provides visual indicators and controls for connection health monitoring
 * in the WhatsApp-like messaging interface.
 */

(function() {
    'use strict';
    
    class ConnectionHealthUI {
        constructor(containerId = 'connection-health-container') {
            this.container = document.getElementById(containerId);
            this.healthMonitor = null;
            this.isVisible = false;
            
            // UI elements
            this.statusIndicator = null;
            this.qualityIndicator = null;
            this.statsPanel = null;
            this.toggleButton = null;
            
            this.init();
        }
        
        /**
         * Initialize the UI component
         */
        init() {
            if (!this.container) {
                console.warn('Connection health container not found');
                return;
            }
            
            this.createUI();
            this.bindEvents();
        }
        
        /**
         * Create the UI elements
         */
        createUI() {
            this.container.innerHTML = `
                <div class="connection-health-widget">
                    <!-- Main Status Indicator -->
                    <div id="connection-status" class="connection-status">
                        <div class="status-dot" id="status-dot"></div>
                        <span class="status-text" id="status-text">Connecting...</span>
                        <button class="toggle-stats" id="toggle-stats" title="Show connection details">
                            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd" />
                            </svg>
                        </button>
                    </div>
                    
                    <!-- Detailed Stats Panel -->
                    <div id="connection-stats" class="connection-stats hidden">
                        <div class="stats-grid">
                            <div class="stat-item">
                                <label>Quality:</label>
                                <span id="quality-value" class="quality-value">Unknown</span>
                            </div>
                            <div class="stat-item">
                                <label>Latency:</label>
                                <span id="latency-value">-- ms</span>
                            </div>
                            <div class="stat-item">
                                <label>Packet Loss:</label>
                                <span id="packet-loss-value">--%</span>
                            </div>
                            <div class="stat-item">
                                <label>Network:</label>
                                <span id="network-type-value">Unknown</span>
                            </div>
                        </div>
                        
                        <div class="stats-actions">
                            <button id="force-reconnect" class="action-button">
                                <svg class="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                                    <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd" />
                                </svg>
                                Reconnect
                            </button>
                            <button id="reset-stats" class="action-button">
                                <svg class="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                                </svg>
                                Reset Stats
                            </button>
                        </div>
                    </div>
                </div>
            `;
            
            // Get references to UI elements
            this.statusIndicator = document.getElementById('connection-status');
            this.qualityIndicator = document.getElementById('quality-value');
            this.statsPanel = document.getElementById('connection-stats');
            this.toggleButton = document.getElementById('toggle-stats');
            
            // Add CSS styles
            this.addStyles();
        }
        
        /**
         * Add CSS styles for the component
         */
        addStyles() {
            const style = document.createElement('style');
            style.textContent = `
                .connection-health-widget {
                    position: relative;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    font-size: 12px;
                }
                
                .connection-status {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    padding: 6px 12px;
                    background: rgba(255, 255, 255, 0.9);
                    border: 1px solid #e5e7eb;
                    border-radius: 20px;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    backdrop-filter: blur(10px);
                }
                
                .connection-status:hover {
                    background: rgba(255, 255, 255, 1);
                    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                }
                
                .status-dot {
                    width: 8px;
                    height: 8px;
                    border-radius: 50%;
                    background: #6b7280;
                    transition: all 0.3s ease;
                }
                
                .status-dot.connected {
                    background: #10b981;
                    box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.2);
                    animation: pulse-green 2s infinite;
                }
                
                .status-dot.unhealthy {
                    background: #f59e0b;
                    animation: pulse-yellow 1s infinite;
                }
                
                .status-dot.reconnecting {
                    background: #3b82f6;
                    animation: pulse-blue 0.8s infinite;
                }
                
                .status-dot.failed {
                    background: #ef4444;
                    animation: pulse-red 1s infinite;
                }
                
                .status-dot.offline {
                    background: #6b7280;
                }
                
                @keyframes pulse-green {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.5; }
                }
                
                @keyframes pulse-yellow {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.6; }
                }
                
                @keyframes pulse-blue {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.4; }
                }
                
                @keyframes pulse-red {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.7; }
                }
                
                .status-text {
                    color: #374151;
                    font-weight: 500;
                    white-space: nowrap;
                }
                
                .toggle-stats {
                    background: none;
                    border: none;
                    color: #6b7280;
                    cursor: pointer;
                    padding: 2px;
                    border-radius: 4px;
                    transition: all 0.2s ease;
                }
                
                .toggle-stats:hover {
                    color: #374151;
                    background: rgba(0, 0, 0, 0.05);
                }
                
                .toggle-stats.expanded {
                    transform: rotate(180deg);
                }
                
                .connection-stats {
                    position: absolute;
                    top: 100%;
                    left: 0;
                    right: 0;
                    margin-top: 8px;
                    background: white;
                    border: 1px solid #e5e7eb;
                    border-radius: 12px;
                    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
                    padding: 16px;
                    z-index: 1000;
                    min-width: 280px;
                    backdrop-filter: blur(10px);
                }
                
                .connection-stats.hidden {
                    display: none;
                }
                
                .stats-grid {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 12px;
                    margin-bottom: 16px;
                }
                
                .stat-item {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }
                
                .stat-item label {
                    color: #6b7280;
                    font-weight: 500;
                }
                
                .stat-item span {
                    color: #374151;
                    font-weight: 600;
                }
                
                .quality-value {
                    padding: 2px 8px;
                    border-radius: 12px;
                    font-size: 11px;
                    font-weight: 600;
                    text-transform: uppercase;
                }
                
                .quality-excellent {
                    background: #d1fae5;
                    color: #065f46;
                }
                
                .quality-good {
                    background: #dbeafe;
                    color: #1e40af;
                }
                
                .quality-fair {
                    background: #fef3c7;
                    color: #92400e;
                }
                
                .quality-poor {
                    background: #fed7aa;
                    color: #9a3412;
                }
                
                .quality-very-poor {
                    background: #fecaca;
                    color: #991b1b;
                }
                
                .quality-unknown {
                    background: #f3f4f6;
                    color: #6b7280;
                }
                
                .stats-actions {
                    display: flex;
                    gap: 8px;
                    padding-top: 12px;
                    border-top: 1px solid #f3f4f6;
                }
                
                .action-button {
                    flex: 1;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    padding: 8px 12px;
                    background: #f9fafb;
                    border: 1px solid #e5e7eb;
                    border-radius: 8px;
                    color: #374151;
                    font-size: 12px;
                    font-weight: 500;
                    cursor: pointer;
                    transition: all 0.2s ease;
                }
                
                .action-button:hover {
                    background: #f3f4f6;
                    border-color: #d1d5db;
                }
                
                .action-button:active {
                    transform: translateY(1px);
                }
                
                .action-button svg {
                    flex-shrink: 0;
                }
            `;
            
            document.head.appendChild(style);
        }
        
        /**
         * Bind event listeners
         */
        bindEvents() {
            // Toggle stats panel
            if (this.toggleButton) {
                this.toggleButton.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.toggleStats();
                });
            }
            
            // Status indicator click
            if (this.statusIndicator) {
                this.statusIndicator.addEventListener('click', () => {
                    this.toggleStats();
                });
            }
            
            // Action buttons
            const forceReconnectBtn = document.getElementById('force-reconnect');
            if (forceReconnectBtn) {
                forceReconnectBtn.addEventListener('click', () => {
                    this.forceReconnect();
                });
            }
            
            const resetStatsBtn = document.getElementById('reset-stats');
            if (resetStatsBtn) {
                resetStatsBtn.addEventListener('click', () => {
                    this.resetStats();
                });
            }
            
            // Close stats panel when clicking outside
            document.addEventListener('click', (e) => {
                if (this.isVisible && !this.container.contains(e.target)) {
                    this.hideStats();
                }
            });
        }
        
        /**
         * Connect to health monitor
         * @param {ConnectionHealthMonitor} healthMonitor 
         */
        connectToMonitor(healthMonitor) {
            this.healthMonitor = healthMonitor;
            
            // Set up callbacks
            healthMonitor.onConnectionStateChange = (state, message, stats) => {
                this.updateConnectionState(state, message, stats);
            };
            
            healthMonitor.onQualityChange = (quality, oldQuality, rtt) => {
                this.updateConnectionQuality(quality, rtt);
            };
            
            healthMonitor.onReconnectAttempt = (attempt, delay, isActual) => {
                if (isActual) {
                    this.showReconnectingState(attempt);
                }
            };
        }
        
        /**
         * Update connection state display
         * @param {string} state - Connection state
         * @param {string} message - State message
         * @param {Object} stats - Connection statistics
         */
        updateConnectionState(state, message, stats) {
            const statusDot = document.getElementById('status-dot');
            const statusText = document.getElementById('status-text');
            
            if (statusDot) {
                statusDot.className = `status-dot ${state}`;
            }
            
            if (statusText) {
                statusText.textContent = message;
            }
            
            // Update detailed stats
            if (stats) {
                this.updateDetailedStats(stats);
            }
        }
        
        /**
         * Update connection quality display
         * @param {string} quality - Connection quality
         * @param {number} rtt - Round trip time
         */
        updateConnectionQuality(quality, rtt) {
            const qualityElement = document.getElementById('quality-value');
            const latencyElement = document.getElementById('latency-value');
            
            if (qualityElement) {
                qualityElement.textContent = quality.replace('-', ' ');
                qualityElement.className = `quality-value quality-${quality}`;
            }
            
            if (latencyElement) {
                latencyElement.textContent = `${Math.round(rtt)} ms`;
            }
        }
        
        /**
         * Update detailed statistics
         * @param {Object} stats - Connection statistics
         */
        updateDetailedStats(stats) {
            const elements = {
                'quality-value': stats.quality.replace('-', ' '),
                'latency-value': `${stats.averageRtt} ms`,
                'packet-loss-value': `${stats.packetLossRate}%`,
                'network-type-value': stats.networkType || 'Unknown'
            };
            
            Object.entries(elements).forEach(([id, value]) => {
                const element = document.getElementById(id);
                if (element) {
                    element.textContent = value;
                    
                    // Update quality styling
                    if (id === 'quality-value') {
                        element.className = `quality-value quality-${stats.quality}`;
                    }
                }
            });
        }
        
        /**
         * Show reconnecting state
         * @param {number} attempt - Reconnection attempt number
         */
        showReconnectingState(attempt) {
            const statusText = document.getElementById('status-text');
            if (statusText) {
                statusText.textContent = `Reconnecting... (${attempt})`;
            }
        }
        
        /**
         * Toggle stats panel visibility
         */
        toggleStats() {
            if (this.isVisible) {
                this.hideStats();
            } else {
                this.showStats();
            }
        }
        
        /**
         * Show stats panel
         */
        showStats() {
            if (this.statsPanel) {
                this.statsPanel.classList.remove('hidden');
                this.isVisible = true;
                
                if (this.toggleButton) {
                    this.toggleButton.classList.add('expanded');
                }
                
                // Update stats if monitor is available
                if (this.healthMonitor) {
                    const stats = this.healthMonitor.getConnectionStats();
                    this.updateDetailedStats(stats);
                }
            }
        }
        
        /**
         * Hide stats panel
         */
        hideStats() {
            if (this.statsPanel) {
                this.statsPanel.classList.add('hidden');
                this.isVisible = false;
                
                if (this.toggleButton) {
                    this.toggleButton.classList.remove('expanded');
                }
            }
        }
        
        /**
         * Force reconnection
         */
        forceReconnect() {
            if (this.healthMonitor) {
                this.healthMonitor.attemptReconnection();
            }
            
            // Trigger reconnection through global chat system
            if (window.connectWebSocket) {
                window.connectWebSocket();
            }
            
            this.hideStats();
        }
        
        /**
         * Reset statistics
         */
        resetStats() {
            if (this.healthMonitor) {
                this.healthMonitor.resetStats();
                
                // Update display
                const stats = this.healthMonitor.getConnectionStats();
                this.updateDetailedStats(stats);
            }
        }
        
        /**
         * Set visibility of the entire widget
         * @param {boolean} visible - Whether to show the widget
         */
        setVisible(visible) {
            if (this.container) {
                this.container.style.display = visible ? 'block' : 'none';
            }
        }
        
        /**
         * Get current connection statistics
         * @returns {Object} Connection statistics
         */
        getStats() {
            return this.healthMonitor ? this.healthMonitor.getConnectionStats() : null;
        }
    }
    
    // Export to global scope
    window.ConnectionHealthUI = ConnectionHealthUI;
    
})();