# Polling Service Usage Guide

## Overview

The `PollingService` provides a fallback mechanism for real-time updates when WebSocket connections are unavailable. It implements efficient incremental updates by tracking last update timestamps and only fetching new content.

## Features

- **Feed Polling**: 30-second interval for new posts
- **Message Polling**: 15-second interval for new messages
- **Notification Polling**: 60-second interval for new notifications
- **Efficient Updates**: Only fetches content created since last poll
- **Error Handling**: Automatic retry logic with max error threshold
- **State Integration**: Automatically updates StateManager with new data
- **WebSocket Integration**: Automatically triggered when WebSocket fails

## Installation

The PollingService is part of the core modules and is automatically available:

```javascript
import { PollingService, initPollingService } from './core/polling-service.js';
import { apiClient } from './core/api-client.js';
import { stateManager } from './core/state-manager.js';
```

## Basic Usage

### Initialize the Polling Service

```javascript
// Create a new instance
const pollingService = new PollingService(apiClient, stateManager);

// Or use the singleton initialization
import { initPollingService } from './core/polling-service.js';
const pollingService = initPollingService(apiClient, stateManager);
```

### Start Feed Polling

```javascript
// Start polling for new posts (30s interval)
pollingService.startFeedPolling((newPosts) => {
  console.log('New posts available:', newPosts);
  // Handle new posts
});
```

### Start Message Polling

```javascript
// Start polling for new messages (15s interval)
pollingService.startMessagePolling((newMessages) => {
  console.log('New messages available:', newMessages);
  // Handle new messages
});
```

### Start Notification Polling

```javascript
// Start polling for new notifications (60s interval)
pollingService.startNotificationPolling((newNotifications) => {
  console.log('New notifications available:', newNotifications);
  // Handle new notifications
});
```

### Stop Polling

```javascript
// Stop individual polling types
pollingService.stopFeedPolling();
pollingService.stopMessagePolling();
pollingService.stopNotificationPolling();

// Stop all polling
pollingService.stopAllPolling();
```

## WebSocket Integration

The PollingService is automatically triggered when WebSocket fails:

```javascript
import { WebSocketManager } from './core/websocket-manager.js';

const wsManager = new WebSocketManager(wsUrl, authToken);
wsManager.setPollingFallback(() => {
  // This callback is invoked when WebSocket fails after 3 reconnection attempts
  pollingService.startFeedPolling();
  pollingService.startMessagePolling();
  pollingService.startNotificationPolling();
});
```

## Advanced Usage

### Get Polling Status

```javascript
const status = pollingService.getStatus();
console.log(status);
// Output:
// {
//   feedPolling: true,
//   messagePolling: false,
//   notificationPolling: true,
//   lastFeedUpdate: "2024-01-15T10:30:00Z",
//   lastMessageUpdate: null,
//   lastNotificationUpdate: "2024-01-15T10:29:00Z",
//   feedErrors: 0,
//   messageErrors: 0,
//   notificationErrors: 0
// }
```

### Reset Polling Service

```javascript
// Clear all polling state and stop all timers
pollingService.reset();
```

### Custom Callbacks

```javascript
// Set custom callbacks for handling new data
pollingService.onFeedUpdate = (newPosts) => {
  // Custom feed update logic
  newPosts.forEach(post => {
    console.log('New post:', post.id);
  });
};

pollingService.onMessageUpdate = (newMessages) => {
  // Custom message update logic
};

pollingService.onNotificationUpdate = (newNotifications) => {
  // Custom notification update logic
};
```

## Polling Intervals

The service uses the following polling intervals:

| Type | Interval | Reason |
|------|----------|--------|
| Feed | 30 seconds | Posts are less frequent, can tolerate longer delays |
| Messages | 15 seconds | Messages are more time-sensitive |
| Notifications | 60 seconds | Notifications are informational, can tolerate longer delays |

## Error Handling

The PollingService includes automatic error handling:

- **Max Errors**: 3 consecutive errors before stopping
- **Error Tracking**: Each polling type tracks its own error count
- **Automatic Recovery**: Error count resets on successful poll
- **Graceful Degradation**: Stops polling if errors exceed threshold

```javascript
// Check error status
const status = pollingService.getStatus();
if (status.feedErrors > 0) {
  console.warn(`Feed polling has ${status.feedErrors} errors`);
}
```

## State Manager Integration

The PollingService automatically updates the StateManager with new data:

```javascript
// Feed updates
newPosts.forEach(post => {
  stateManager.addPostToFeed(post);
});

// Notification updates
newNotifications.forEach(notification => {
  stateManager.setState('notifications.items', [notification, ...currentItems]);
  stateManager.setState('notifications.unreadCount', unreadCount + 1);
});
```

## Efficient Incremental Updates

The PollingService only fetches new content by using the `since` parameter:

```javascript
// First poll: fetches all recent posts
pollingService.startFeedPolling();

// Subsequent polls: only fetch posts created after lastFeedUpdate
// API call: GET /social/agents/feed/?since=2024-01-15T10:30:00Z&per_page=50
```

## Best Practices

1. **Start Polling on WebSocket Failure**: Use the WebSocket fallback callback
2. **Stop Polling on Cleanup**: Always call `stopAllPolling()` when page unloads
3. **Handle Callbacks**: Implement callbacks to update UI with new data
4. **Monitor Errors**: Check polling status periodically for errors
5. **Use State Manager**: Let the PollingService update state automatically

## Example: Complete Integration

```javascript
import { PollingService, initPollingService } from './core/polling-service.js';
import { WebSocketManager } from './core/websocket-manager.js';
import { apiClient } from './core/api-client.js';
import { stateManager } from './core/state-manager.js';

class SocialFeedPage {
  constructor() {
    this.pollingService = new PollingService(apiClient, stateManager);
    this.wsManager = new WebSocketManager(wsUrl, authToken);
  }

  async init() {
    // Set up WebSocket with polling fallback
    this.wsManager.setPollingFallback(() => {
      console.log('WebSocket failed, starting polling fallback');
      this.pollingService.startFeedPolling();
      this.pollingService.startMessagePolling();
      this.pollingService.startNotificationPolling();
    });

    // Try to connect WebSocket
    try {
      await this.wsManager.connect();
    } catch (error) {
      console.error('WebSocket connection failed:', error);
      // Polling will be started by the fallback callback
    }

    // Subscribe to state changes
    stateManager.subscribe('feed.posts', (posts) => {
      this.renderFeed(posts);
    });
  }

  cleanup() {
    // Stop all polling when page unloads
    this.pollingService.stopAllPolling();
    this.wsManager.disconnect();
  }

  renderFeed(posts) {
    // Update UI with new posts
  }
}

// Usage
const page = new SocialFeedPage();
page.init();

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
  page.cleanup();
});
```

## Troubleshooting

### Polling Not Starting

- Check that APIClient is properly initialized with CSRF token
- Verify StateManager is passed to PollingService constructor
- Check browser console for error messages

### Polling Stops Unexpectedly

- Check polling status: `pollingService.getStatus()`
- Look for error count: if `feedErrors >= 3`, polling stopped due to errors
- Check API endpoints are returning correct response format

### High CPU Usage

- Verify polling intervals are not too short
- Check that callbacks don't perform heavy operations
- Monitor network requests in browser DevTools

### Missing Updates

- Verify `since` parameter is being sent to API
- Check that API supports incremental updates with `since` parameter
- Ensure StateManager is properly updating UI

## API Response Format

The PollingService expects the following response format:

```json
{
  "data": {
    "results": [
      {
        "id": "post-1",
        "content": "Post content",
        "created_at": "2024-01-15T10:30:00Z",
        ...
      }
    ]
  }
}
```

## Performance Considerations

- **Network**: Polling uses more bandwidth than WebSocket
- **CPU**: Polling timers use minimal CPU
- **Battery**: On mobile, polling drains battery faster than WebSocket
- **Latency**: Polling has higher latency (up to 30-60 seconds)

Use WebSocket when available for better performance and lower latency.
