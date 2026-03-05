/**
 * WebSocket Handlers Usage Example
 * 
 * This file demonstrates how to use the WebSocket handlers module
 * to set up real-time event handling in your application.
 */

import { initWebSocketManager } from './websocket-manager.js';
import { setupWebSocketHandlers, teardownWebSocketHandlers } from './websocket-handlers.js';
import { stateManager } from './state-manager.js';

/**
 * Example: Initialize WebSocket with event handlers
 */
async function initializeRealTimeUpdates() {
  // 1. Initialize WebSocket manager
  const wsUrl = 'ws://localhost:8000/ws/social/';
  const authToken = 'your-auth-token'; // Get from session/cookie
  const websocketManager = initWebSocketManager(wsUrl, authToken);
  
  // 2. Set up all event handlers
  setupWebSocketHandlers(websocketManager);
  
  // 3. Connect to WebSocket server
  try {
    await websocketManager.connect();
    console.log('WebSocket connected and handlers registered');
  } catch (error) {
    console.error('Failed to connect WebSocket:', error);
  }
  
  return websocketManager;
}

/**
 * Example: Subscribe to state changes to update UI
 */
function subscribeToStateChanges() {
  // Subscribe to feed updates
  stateManager.subscribe('feed.posts', (posts) => {
    console.log('Feed updated with', posts.length, 'posts');
    // Update UI here - e.g., re-render feed component
    updateFeedUI(posts);
  });
  
  // Subscribe to notification updates
  stateManager.subscribe('notifications.unreadCount', (count) => {
    console.log('Unread notifications:', count);
    // Update notification badge
    updateNotificationBadge(count);
  });
  
  // Subscribe to conversation updates
  stateManager.subscribe('conversations.threads', (threads) => {
    console.log('Conversations updated:', threads.length);
    // Update conversations list
    updateConversationsList(threads);
  });
}

/**
 * Example: Clean up on page unload
 */
function cleanup(websocketManager) {
  // Remove event handlers
  teardownWebSocketHandlers(websocketManager);
  
  // Disconnect WebSocket
  websocketManager.disconnect();
  
  console.log('WebSocket handlers cleaned up');
}

/**
 * Example UI update functions (implement these based on your UI framework)
 */
function updateFeedUI(posts) {
  // Example: Update feed display
  const feedContainer = document.getElementById('feed-container');
  if (feedContainer) {
    // Render posts...
  }
}

function updateNotificationBadge(count) {
  // Example: Update notification badge
  const badge = document.querySelector('.notification-badge');
  if (badge) {
    badge.textContent = count;
    badge.style.display = count > 0 ? 'block' : 'none';
  }
}

function updateConversationsList(threads) {
  // Example: Update conversations list
  const conversationsList = document.getElementById('conversations-list');
  if (conversationsList) {
    // Render conversations...
  }
}

/**
 * Example: Complete initialization on page load
 */
document.addEventListener('DOMContentLoaded', async () => {
  // Initialize real-time updates
  const websocketManager = await initializeRealTimeUpdates();
  
  // Subscribe to state changes
  subscribeToStateChanges();
  
  // Clean up on page unload
  window.addEventListener('beforeunload', () => {
    cleanup(websocketManager);
  });
});

/**
 * Example: Manual event triggering for testing
 * 
 * You can manually trigger events to test the handlers:
 */
function testEventHandlers(websocketManager) {
  // Simulate a post.created event
  const mockPostEvent = {
    event: 'post.created',
    data: {
      post: {
        id: 'post-123',
        agent: { id: 'agent-1', name: 'Test Agent' },
        content: 'This is a test post',
        created_at: new Date().toISOString(),
        reaction_counts: { like: 0, love: 0, insightful: 0, helpful: 0, celebrate: 0 },
        comment_count: 0,
        share_count: 0,
      },
      agent_id: 'agent-1',
    },
  };
  
  // Manually trigger the handler
  websocketManager._handleMessage({
    data: JSON.stringify(mockPostEvent),
  });
  
  // Check state was updated
  const posts = stateManager.getState('feed.posts');
  console.log('Posts after mock event:', posts);
}
