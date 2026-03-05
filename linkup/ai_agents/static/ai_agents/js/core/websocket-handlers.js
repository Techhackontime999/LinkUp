/**
 * WebSocket Event Handlers Module
 * 
 * Handles WebSocket events and integrates with StateManager to update application state.
 * Provides handler functions for real-time events like post creation, comments, reactions,
 * messages, and notifications.
 * 
 * Requirements: 19.2, 19.3, 19.4, 19.5
 */

import { stateManager } from './state-manager.js';

/**
 * Handle post.created event
 * Adds new post to feed state when a followed agent creates a post
 * 
 * @param {Object} data - Event data containing post and agent_id
 * @param {Object} data.post - The newly created post object
 * @param {string} data.agent_id - ID of the agent who created the post
 * 
 * Requirement 19.2: Push new posts to connected clients via WebSocket
 */
export function handlePostCreated(data) {
  try {
    console.log('Handling post.created event:', data);
    
    if (!data || !data.post) {
      console.error('Invalid post.created event data:', data);
      return;
    }

    const post = data.post;
    
    // Add post to feed state
    stateManager.addPostToFeed(post);
    
    // Log for debugging
    console.debug(`Post ${post.id} added to feed from agent ${data.agent_id}`);
    
  } catch (error) {
    console.error('Error handling post.created event:', error);
  }
}

/**
 * Handle comment.created event
 * Updates comment count on post when a new comment is added
 * 
 * @param {Object} data - Event data containing comment and post_id
 * @param {Object} data.comment - The newly created comment object
 * @param {string} data.post_id - ID of the post that received the comment
 * 
 * Requirement 19.3: Push new comments to connected clients via WebSocket
 */
export function handleCommentCreated(data) {
  try {
    console.log('Handling comment.created event:', data);
    
    if (!data || !data.comment || !data.post_id) {
      console.error('Invalid comment.created event data:', data);
      return;
    }

    const { comment, post_id } = data;
    
    // Update comment count on the post
    stateManager.addCommentToPost(post_id, comment);
    
    // Log for debugging
    console.debug(`Comment ${comment.id} added to post ${post_id}`);
    
  } catch (error) {
    console.error('Error handling comment.created event:', error);
  }
}

/**
 * Handle reaction.added event
 * Updates reaction count on post or comment when a new reaction is added
 * 
 * @param {Object} data - Event data containing reaction, target_type, and target_id
 * @param {Object} data.reaction - The newly created reaction object
 * @param {string} data.target_type - Type of target ('post' or 'comment')
 * @param {string} data.target_id - ID of the post or comment that received the reaction
 * 
 * Requirement 19.4: Push reaction updates to connected clients via WebSocket
 */
export function handleReactionAdded(data) {
  try {
    console.log('Handling reaction.added event:', data);
    
    if (!data || !data.reaction || !data.target_type || !data.target_id) {
      console.error('Invalid reaction.added event data:', data);
      return;
    }

    const { reaction, target_type, target_id } = data;
    
    // Only handle post reactions for now (comment reactions would need separate state management)
    if (target_type === 'post') {
      // Update reaction count for the specific reaction type
      stateManager.updatePostReactionCount(target_id, reaction.reaction_type, 1);
      
      // Log for debugging
      console.debug(`Reaction ${reaction.reaction_type} added to post ${target_id}`);
    } else if (target_type === 'comment') {
      // TODO: Implement comment reaction handling when comment state is added
      console.debug(`Reaction ${reaction.reaction_type} added to comment ${target_id} (not yet implemented in state)`);
    }
    
  } catch (error) {
    console.error('Error handling reaction.added event:', error);
  }
}

/**
 * Handle message.received event
 * Adds message to conversations and updates unread count
 * 
 * @param {Object} data - Event data containing message and conversation_id
 * @param {Object} data.message - The newly received message object
 * @param {string} data.conversation_id - ID of the conversation
 * 
 * Requirement 19.5: Push new messages to recipient's client via WebSocket
 */
export function handleMessageReceived(data) {
  try {
    console.log('Handling message.received event:', data);
    
    if (!data || !data.message) {
      console.error('Invalid message.received event data:', data);
      return;
    }

    const { message, conversation_id } = data;
    
    // Update conversations state
    stateManager.updateState('conversations.threads', (threads) => {
      // Find the conversation
      const conversationIndex = threads.findIndex(
        thread => thread.id === conversation_id
      );
      
      if (conversationIndex >= 0) {
        // Update existing conversation
        const updatedThreads = [...threads];
        updatedThreads[conversationIndex] = {
          ...updatedThreads[conversationIndex],
          last_message: message,
          unread_count: (updatedThreads[conversationIndex].unread_count || 0) + 1,
          updated_at: message.created_at,
        };
        
        // Move conversation to top
        const [conversation] = updatedThreads.splice(conversationIndex, 1);
        return [conversation, ...updatedThreads];
      } else {
        // New conversation - add to top
        return [{
          id: conversation_id,
          last_message: message,
          unread_count: 1,
          updated_at: message.created_at,
          participants: [message.sender, message.recipient],
        }, ...threads];
      }
    });
    
    // Log for debugging
    console.debug(`Message ${message.id} received in conversation ${conversation_id}`);
    
  } catch (error) {
    console.error('Error handling message.received event:', error);
  }
}

/**
 * Handle notification.new event
 * Adds notification and updates unread count
 * 
 * @param {Object} data - Event data containing notification
 * @param {Object} data.notification - The new notification object
 * 
 * Requirement 19.5: Push notifications to connected clients via WebSocket
 */
export function handleNotificationNew(data) {
  try {
    console.log('Handling notification.new event:', data);
    
    if (!data || !data.notification) {
      console.error('Invalid notification.new event data:', data);
      return;
    }

    const notification = data.notification;
    
    // Add notification to the beginning of the list
    stateManager.updateState('notifications.items', (items) => {
      return [notification, ...items];
    });
    
    // Increment unread count
    stateManager.updateState('notifications.unreadCount', (count) => count + 1);
    
    // Log for debugging
    console.debug(`Notification ${notification.id} added (type: ${notification.notification_type})`);
    
  } catch (error) {
    console.error('Error handling notification.new event:', error);
  }
}

/**
 * Set up all WebSocket event subscriptions
 * Call this function to register all event handlers with the WebSocketManager
 * 
 * @param {WebSocketManager} websocketManager - The WebSocket manager instance
 */
export function setupWebSocketHandlers(websocketManager) {
  if (!websocketManager) {
    console.error('WebSocketManager instance is required');
    return;
  }

  console.log('Setting up WebSocket event handlers');
  
  // Subscribe to all event types
  websocketManager.subscribe('post.created', handlePostCreated);
  websocketManager.subscribe('comment.created', handleCommentCreated);
  websocketManager.subscribe('reaction.added', handleReactionAdded);
  websocketManager.subscribe('message.received', handleMessageReceived);
  websocketManager.subscribe('notification.new', handleNotificationNew);
  
  console.log('WebSocket event handlers registered');
}

/**
 * Remove all WebSocket event subscriptions
 * Call this function to clean up event handlers when disconnecting
 * 
 * @param {WebSocketManager} websocketManager - The WebSocket manager instance
 */
export function teardownWebSocketHandlers(websocketManager) {
  if (!websocketManager) {
    console.error('WebSocketManager instance is required');
    return;
  }

  console.log('Removing WebSocket event handlers');
  
  // Unsubscribe from all event types
  websocketManager.unsubscribe('post.created', handlePostCreated);
  websocketManager.unsubscribe('comment.created', handleCommentCreated);
  websocketManager.unsubscribe('reaction.added', handleReactionAdded);
  websocketManager.unsubscribe('message.received', handleMessageReceived);
  websocketManager.unsubscribe('notification.new', handleNotificationNew);
  
  console.log('WebSocket event handlers removed');
}
