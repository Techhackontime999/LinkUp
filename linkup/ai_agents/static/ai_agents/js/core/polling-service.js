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
    
    // Pollin