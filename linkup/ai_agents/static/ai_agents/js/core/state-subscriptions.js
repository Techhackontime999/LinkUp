/**
 * State Subscriptions Module
 * 
 * Manages subscriptions between components and the state manager.
 * Ensures components update when state changes.
 */

import { stateManager } from './state-manager.js';
import { NotificationBell } from '../components/notification-bell.js';
import { PostCard } from '../components/post-card.js';

/**
 * Subscribe PostCard components to post state changes
 */
export function subscribePostCardsToState() {
  // Subscribe to feed posts changes
  stateManager.subscribe('feed.posts', (posts) => {
    console.log('Feed posts updated:', posts.length);
    
    // Update all post cards with new data
    document.querySelectorAll('[data-post-id]').forEach(postElement => {
      const postId = postElement.dataset.postId;
      const updatedPost = posts.find(p => p.id === postId);
      
      if (updatedPost) {
        // Update post card with new data
        const postCard = postElement.__postCardInstance;
        if (postCard && typeof postCard.update === 'function') {
          postCard.update(updatedPost);
        }
      }
    });
  });

  // Subscribe to reaction count changes
  stateManager.subscribe('feed.posts', (posts) => {
    posts.forEach(post => {
      const postElement = document.querySelector(`[data-post-id="${post.id}"]`);
      if (postElement) {
        // Update reaction buttons
        const reactionButtons = postElement.querySelectorAll('.reaction-btn');
        reactionButtons.forEach(btn => {
          const reactionType = btn.dataset.type;
          const count = post.reaction_counts?.[reactionType] || 0;
          const countSpan = btn.querySelector('.count');
          if (countSpan) {
            countSpan.textContent = count;
          }
        });
      }
    });
  });
}

/**
 * Subscribe NotificationBell to notification state changes
 */
export function subscribeNotificationBellToState(notificationBell) {
  if (!notificationBell) {
    console.warn('NotificationBell instance not provided');
    return;
  }

  // Subscribe to unread count changes
  stateManager.subscribe('notifications.unreadCount', (count) => {
    console.log('Unread notifications count updated:', count);
    notificationBell.updateCount(count);
  });

  // Subscribe to notification items changes
  stateManager.subscribe('notifications.items', (items) => {
    console.log('Notifications updated:', items.length);
    
    // Update notification bell with new items
    if (Array.isArray(items)) {
      // Clear existing notifications and add new ones
      items.forEach(notification => {
        notificationBell.addNotification(notification);
      });
    }
  });

  // Subscribe to individual notification read status
  stateManager.subscribe('notifications.items', (items) => {
    // Update read status for each notification
    items.forEach(notification => {
      const notificationElement = document.querySelector(
        `[data-notification-id="${notification.id}"]`
      );
      if (notificationElement) {
        if (notification.is_read) {
          notificationElement.classList.add('read');
          notificationElement.classList.remove('unread');
        } else {
          notificationElement.classList.add('unread');
          notificationElement.classList.remove('read');
        }
      }
    });
  });
}

/**
 * Subscribe feed to real-time updates
 */
export function subscribeFeedToRealtimeUpdates() {
  // Subscribe to new posts
  stateManager.subscribe('feed.posts', (posts) => {
    console.log('Feed updated with new posts');
    
    // Trigger feed refresh if needed
    const feedContainer = document.getElementById('feed-container');
    if (feedContainer) {
      // Emit custom event for feed page to handle
      feedContainer.dispatchEvent(new CustomEvent('feed-updated', { detail: { posts } }));
    }
  });

  // Subscribe to feed last update time
  stateManager.subscribe('feed.lastUpdate', (timestamp) => {
    console.log('Feed last updated at:', new Date(timestamp).toLocaleString());
  });
}

/**
 * Subscribe messages to conversation state changes
 */
export function subscribeMessagesToConversationState() {
  // Subscribe to conversation threads
  stateManager.subscribe('conversations.threads', (threads) => {
    console.log('Conversation threads updated:', threads.length);
    
    // Update conversation list
    const conversationList = document.getElementById('conversation-list');
    if (conversationList) {
      conversationList.dispatchEvent(
        new CustomEvent('conversations-updated', { detail: { threads } })
      );
    }
  });

  // Subscribe to active thread changes
  stateManager.subscribe('conversations.activeThreadId', (threadId) => {
    console.log('Active conversation thread changed:', threadId);
    
    // Update message display
    const messageThread = document.getElementById('message-thread');
    if (messageThread) {
      messageThread.dispatchEvent(
        new CustomEvent('active-thread-changed', { detail: { threadId } })
      );
    }
  });
}

/**
 * Subscribe UI state changes
 */
export function subscribeUIStateChanges() {
  // Subscribe to theme changes
  stateManager.subscribe('ui.theme', (theme) => {
    console.log('Theme changed to:', theme);
    
    // Apply theme to document
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  });

  // Subscribe to sidebar state
  stateManager.subscribe('ui.sidebarOpen', (isOpen) => {
    console.log('Sidebar state changed:', isOpen);
    
    const sidebar = document.getElementById('sidebar');
    if (sidebar) {
      if (isOpen) {
        sidebar.classList.add('open');
      } else {
        sidebar.classList.remove('open');
      }
    }
  });

  // Subscribe to modal state
  stateManager.subscribe('ui.modalOpen', (isOpen) => {
    console.log('Modal state changed:', isOpen);
  });
}

/**
 * Set up WebSocket event subscriptions to update state
 */
export function setupWebSocketStateSubscriptions(websocketManager) {
  if (!websocketManager) {
    console.warn('WebSocketManager not provided');
    return;
  }

  // Subscribe to post.created events
  websocketManager.subscribe('post.created', (data) => {
    console.log('New post created via WebSocket:', data);
    if (data.post) {
      stateManager.addPostToFeed(data.post);
    }
  });

  // Subscribe to comment.created events
  websocketManager.subscribe('comment.created', (data) => {
    console.log('New comment created via WebSocket:', data);
    if (data.post_id && data.comment) {
      stateManager.addCommentToPost(data.post_id, data.comment);
    }
  });

  // Subscribe to reaction.added events
  websocketManager.subscribe('reaction.added', (data) => {
    console.log('New reaction added via WebSocket:', data);
    if (data.target_type === 'post' && data.target_id && data.reaction) {
      const reactionType = data.reaction.reaction_type;
      stateManager.updatePostReactionCount(data.target_id, reactionType, 1);
    }
  });

  // Subscribe to message.received events
  websocketManager.subscribe('message.received', (data) => {
    console.log('New message received via WebSocket:', data);
    if (data.message && data.conversation_id) {
      // Update conversation state
      stateManager.updateState('conversations.threads', (threads) => {
        return threads.map(thread => {
          if (thread.id === data.conversation_id) {
            return {
              ...thread,
              last_message: data.message,
              updated_at: data.message.created_at,
            };
          }
          return thread;
        });
      });
    }
  });

  // Subscribe to notification.new events
  websocketManager.subscribe('notification.new', (data) => {
    console.log('New notification via WebSocket:', data);
    if (data.notification) {
      stateManager.updateState('notifications.items', (items) => {
        return [data.notification, ...items];
      });
      stateManager.updateState('notifications.unreadCount', (count) => count + 1);
    }
  });

  // Subscribe to agent.followed events
  websocketManager.subscribe('agent.followed', (data) => {
    console.log('Agent followed via WebSocket:', data);
    if (data.agent_id) {
      stateManager.updateFollowerCount(data.agent_id, 1);
    }
  });
}

/**
 * Initialize all state subscriptions
 */
export function initializeStateSubscriptions(websocketManager, notificationBell) {
  console.log('Initializing state subscriptions...');

  // Subscribe components to state changes
  subscribePostCardsToState();
  subscribeNotificationBellToState(notificationBell);
  subscribeFeedToRealtimeUpdates();
  subscribeMessagesToConversationState();
  subscribeUIStateChanges();

  // Set up WebSocket event subscriptions
  if (websocketManager) {
    setupWebSocketStateSubscriptions(websocketManager);
  }

  console.log('State subscriptions initialized');
}
