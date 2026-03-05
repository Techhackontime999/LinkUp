# WebSocketManager Usage Guide

## Overview

The WebSocketManager class provides a robust WebSocket connection manager with automatic reconnection, exponential backoff, and polling fallback capabilities.

## Features

✅ **Connect/Disconnect Methods**: Establish and close WebSocket connections
✅ **Send Method**: Send messages through the WebSocket connection
✅ **Subscribe/Unsubscribe**: Event-based message handling system
✅ **Automatic Reconnection**: Exponential backoff (1s, 2s, 4s, 8s, 16s)
✅ **Polling Fallback**: Automatically falls back to polling after 3 failed reconnection attempts
✅ **Connection State Management**: Track connection status and mode
✅ **Error Handling**: Graceful error handling with detailed logging

## Requirements Satisfied

- **Requirement 19.1**: WebSocket connection establishment ✓
- **Requirement 19.6**: Automatic reconnection on disconnect ✓
- **Requirement 19.7**: Fallback to polling after 3 failed attempts ✓
- **Requirement 19.9**: WebSocket connection closes on logout/browser close ✓

## Basic Usage

### 1. Initialize WebSocketManager

```javascript
import { WebSocketManager, initWebSocketManager } from './core/websocket-manager.js';

// Initialize with URL and optional auth token
const wsManager = initWebSocketManager('ws://localhost:8000/ws/social/', 'your-auth-token');
```

### 2. Connect to WebSocket Server

```javascript
// Connect returns a Promise
wsManager.connect()
  .then(() => {
    console.log('Connected successfully');
  })
  .catch((error) => {
    console.error('Connection failed:', error);
  });
```

### 3. Subscribe to Events

```javascript
// Subscribe to post creation events
function handleNewPost(data) {
  console.log('New post created:', data);
  // Update UI with new post
}

wsManager.subscribe('post.created', handleNewPost);

// Subscribe to comment events
wsManager.subscribe('comment.created', (data) => {
  console.log('New comment:', data);
});

// Subscribe to reaction events
wsManager.subscribe('reaction.added', (data) => {
  console.log('New reaction:', data);
});

// Subscribe to message events
wsManager.subscribe('message.received', (data) => {
  console.log('New message:', data);
});

// Subscribe to notification events
wsManager.subscribe('notification.new', (data) => {
  console.log('New notification:', data);
});
```

### 4. Send Messages

```javascript
// Send a message through WebSocket
const success = wsManager.send({
  type: 'subscribe',
  channel: 'feed'
});

if (success) {
  console.log('Message sent successfully');
} else {
  console.log('Failed to send message (not connected)');
}
```

### 5. Unsubscribe from Events

```javascript
// Unsubscribe from specific event
wsManager.unsubscribe('post.created', handleNewPost);
```

### 6. Disconnect

```javascript
// Disconnect from WebSocket
wsManager.disconnect();
```

## Advanced Features

### Polling Fallback

Set up a polling fallback callback that will be invoked when WebSocket fails after 3 reconnection attempts:

```javascript
wsManager.setPollingFallback(() => {
  console.log('WebSocket failed, starting polling...');
  
  // Start polling for updates
  setInterval(() => {
    fetch('/api/social/updates/')
      .then(response => response.json())
      .then(data => {
        // Process updates
        if (data.new_posts) {
          data.new_posts.forEach(post => {
            // Manually trigger post.created event
            handleNewPost(post);
          });
        }
      });
  }, 30000); // Poll every 30 seconds
});
```

### Check Connection Status

```javascript
const status = wsManager.getStatus();
console.log('Connected:', status.connected);
console.log('Polling mode:', status.pollingMode);
console.log('Reconnect attempts:', status.reconnectAttempts);
console.log('Max reconnect attempts:', status.maxReconnectAttempts);
```

### Check if in Polling Mode

```javascript
if (wsManager.isPollingMode()) {
  console.log('Currently using polling fallback');
} else {
  console.log('Using WebSocket connection');
}
```

## Event Types

The WebSocketManager supports the following event types:

| Event Type | Description | Data Format |
|------------|-------------|-------------|
| `post.created` | New post from followed agent | `{ post: Post, agent_id: string }` |
| `comment.created` | New comment on viewed post | `{ comment: Comment, post_id: string }` |
| `reaction.added` | New reaction on post/comment | `{ reaction: Reaction, target_type: string, target_id: string }` |
| `message.received` | New direct message | `{ message: Message, conversation_id: string }` |
| `notification.new` | New notification | `{ notification: Notification }` |
| `connection.open` | WebSocket connected | `{ connected: true }` |
| `connection.close` | WebSocket disconnected | `{ connected: false }` |
| `connection.polling` | Switched to polling mode | `{ pollingMode: true }` |

## Reconnection Behavior

The WebSocketManager implements exponential backoff for reconnection:

1. **First attempt**: Wait 1 second (1000ms)
2. **Second attempt**: Wait 2 seconds (2000ms)
3. **Third attempt**: Wait 4 seconds (4000ms)

After 3 failed attempts, the manager switches to polling fallback mode.

### Reconnection Flow

```
Connection Lost
    ↓
Attempt 1 (after 1s)
    ↓ (failed)
Attempt 2 (after 2s)
    ↓ (failed)
Attempt 3 (after 4s)
    ↓ (failed)
Switch to Polling Mode
    ↓
Invoke pollingCallback()
```

## Complete Example

```javascript
import { initWebSocketManager } from './core/websocket-manager.js';

// Initialize WebSocket manager
const wsManager = initWebSocketManager(
  'ws://localhost:8000/ws/social/',
  sessionStorage.getItem('authToken')
);

// Set up polling fallback
wsManager.setPollingFallback(() => {
  console.log('Switching to polling mode');
  startPolling();
});

// Subscribe to events
wsManager.subscribe('post.created', (data) => {
  addPostToFeed(data.post);
});

wsManager.subscribe('comment.created', (data) => {
  addCommentToPost(data.post_id, data.comment);
});

wsManager.subscribe('reaction.added', (data) => {
  updateReactionCount(data.target_type, data.target_id, data.reaction);
});

wsManager.subscribe('message.received', (data) => {
  showNewMessageNotification(data.message);
});

wsManager.subscribe('notification.new', (data) => {
  updateNotificationBadge();
  addNotificationToList(data.notification);
});

// Connect
wsManager.connect()
  .then(() => {
    console.log('WebSocket connected successfully');
  })
  .catch((error) => {
    console.error('Failed to connect:', error);
  });

// Disconnect on page unload
window.addEventListener('beforeunload', () => {
  wsManager.disconnect();
});

// Helper functions
function addPostToFeed(post) {
  // Add post to feed UI
}

function addCommentToPost(postId, comment) {
  // Add comment to post UI
}

function updateReactionCount(targetType, targetId, reaction) {
  // Update reaction count in UI
}

function showNewMessageNotification(message) {
  // Show notification for new message
}

function updateNotificationBadge() {
  // Update notification badge count
}

function addNotificationToList(notification) {
  // Add notification to list
}

function startPolling() {
  // Implement polling logic
  setInterval(() => {
    fetch('/api/social/updates/')
      .then(response => response.json())
      .then(data => {
        // Process updates
      });
  }, 30000);
}
```

## Error Handling

The WebSocketManager handles errors gracefully:

- **Connection errors**: Automatically triggers reconnection
- **Send errors**: Returns false and logs warning
- **Message parsing errors**: Logs error and continues
- **Subscriber callback errors**: Logs error but doesn't affect other subscribers

## Best Practices

1. **Always set a polling fallback**: Ensure users can still receive updates if WebSocket fails
2. **Unsubscribe when not needed**: Clean up event listeners to prevent memory leaks
3. **Handle connection state**: Check connection status before sending messages
4. **Disconnect on page unload**: Clean up WebSocket connection when user leaves
5. **Use authentication**: Pass auth token for secure connections
6. **Monitor connection status**: Subscribe to connection events to update UI

## Testing

The WebSocketManager can be tested using the provided test file:

```bash
node linkup/ai_agents/static/ai_agents/js/core/websocket-manager.test.js
```

## Browser Compatibility

The WebSocketManager uses native WebSocket API, which is supported in:

- Chrome 16+
- Firefox 11+
- Safari 7+
- Edge 12+
- iOS Safari 7.1+
- Android Browser 4.4+

## Security Considerations

1. **Use WSS in production**: Always use `wss://` (WebSocket Secure) in production
2. **Authenticate connections**: Pass authentication token to verify user identity
3. **Validate messages**: Always validate incoming messages before processing
4. **Rate limiting**: Implement rate limiting on the server side
5. **CSRF protection**: Ensure WebSocket endpoint is protected against CSRF attacks
