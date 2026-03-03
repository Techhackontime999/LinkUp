# Agent Communication Service Implementation

## Overview

This document summarizes the implementation of Task 6: Agent Communication Service for the AI-to-AI Interaction Research Platform.

## Implementation Date

Completed: 2024

## Components Implemented

### 1. AgentCommunicationService Class

**Location:** `linkup/ai_agents/services.py`

**Purpose:** Facilitates message exchange between AI agents with support for real-time delivery, queuing, threading, and status tracking.

#### Key Methods Implemented:

##### 1.1 `send_message()`
- **Requirements:** 4.1, 4.4, 4.5, 4.6, 14.1, 17.1
- **Functionality:**
  - Validates sender and recipient agents
  - Checks rate limits before sending
  - Creates message record with unique ID
  - Supports message threading via parent_message_id
  - Routes message via WebSocket (online) or queues (offline)
  - Logs interaction for research purposes
  - Updates agent metrics
  - Records message size in bytes

##### 1.2 `receive_messages()`
- **Requirements:** 10.1, 10.2, 10.3, 10.4, 10.5
- **Functionality:**
  - Retrieves messages for a specific agent
  - Supports filtering by sender, date range, and status
  - Implements pagination (default 50 messages per page)
  - Returns complete message metadata including timestamps and status

##### 1.3 `broadcast_message()`
- **Functionality:**
  - Sends a message to multiple recipients
  - Returns success/failure count for each recipient
  - Useful for group communications

##### 1.4 `get_conversation_history()`
- **Requirements:** 10.6
- **Functionality:**
  - Retrieves all messages between two specific agents
  - Supports bidirectional conversation retrieval
  - Implements pagination
  - Orders messages chronologically

##### 1.5 `mark_message_as_read()`
- **Requirements:** 14.4
- **Functionality:**
  - Updates message status to READ
  - Records read timestamp
  - Validates that only the recipient can mark as read

##### 1.6 `get_conversation_thread()`
- **Requirements:** 17.2, 17.3
- **Functionality:**
  - Retrieves all messages in a conversation thread
  - Finds root message and traverses entire thread tree
  - Calculates thread depth
  - Supports nested conversations

#### Private Helper Methods:

##### 1.7 `_validate_message_data()`
- **Requirements:** 4.4
- Validates message content size (100KB limit)
- Ensures sender and recipient are different
- Checks required fields

##### 1.8 `_route_message()`
- **Requirements:** 4.2, 4.3, 4.7, 4.8, 4.9, 4.10, 14.2, 14.3, 14.5
- Determines if recipient is online
- Routes to WebSocket for online recipients
- Queues for offline recipients
- Updates message status (DELIVERED, SENT, FAILED)
- Calculates message latency in milliseconds
- Logs delivery failures

##### 1.9 `_is_agent_online()`
- Checks cache for active WebSocket connection
- Uses cache key pattern: `agent_online:{agent_id}`

##### 1.10 `_send_via_websocket()`
- **Requirements:** 4.2, 13.3, 14.3
- Sends message via Django Channels
- Uses channel name pattern: `agent_{agent_id}`
- Handles delivery errors gracefully

##### 1.11 `_update_agent_metrics()`
- Increments total_interactions for both sender and recipient
- Updates agent statistics for research analytics

### 2. InteractionLogger Class

**Location:** `linkup/ai_agents/services.py`

**Purpose:** Logs all AI-to-AI interactions for research analysis.

#### Key Methods Implemented:

##### 2.1 `log_interaction()`
- **Requirements:** 6.1, 6.2
- **Functionality:**
  - Logs interactions between agents
  - Groups related messages into sessions
  - Finds or creates interaction records
  - Considers interactions active if within 5 minutes
  - Increments message count for existing sessions
  - Stores interaction metadata

## Requirements Coverage

### Fully Implemented Requirements:

- **4.1:** Message creation with sender/recipient validation ✓
- **4.2:** Real-time delivery via WebSocket for online recipients ✓
- **4.3:** Message queuing for offline recipients ✓
- **4.4:** Message content size validation (100KB limit) ✓
- **4.5:** Unique message ID assignment ✓
- **4.6:** Message threading with parent references ✓
- **4.7:** Message status update to DELIVERED ✓
- **4.8:** Message status update to FAILED on error ✓
- **4.9:** Message latency calculation and storage ✓
- **4.10:** Message size recording in bytes ✓
- **6.1:** Interaction logging with timestamp ✓
- **6.2:** Capture sender, recipient, message, and metadata ✓
- **10.1:** Message retrieval for recipient ✓
- **10.2:** Filtering by sender ✓
- **10.3:** Filtering by date range ✓
- **10.4:** Pagination support ✓
- **10.5:** Include message content, metadata, and status ✓
- **10.6:** Conversation history between two agents ✓
- **13.3:** WebSocket message delivery ✓
- **14.1:** Initial message status PENDING ✓
- **14.2:** Status update to SENT ✓
- **14.3:** Status update to DELIVERED ✓
- **14.4:** Mark message as READ ✓
- **14.5:** Status update to FAILED ✓
- **17.1:** Parent message references ✓
- **17.2:** Retrieve messages in thread ✓
- **17.3:** Thread depth tracking ✓

## Integration Points

### 1. Django Channels Integration
- Uses `get_channel_layer()` for WebSocket communication
- Sends messages to agent-specific channels
- Handles async-to-sync conversion

### 2. Cache Integration
- Checks agent online status via cache
- Uses cache key pattern for WebSocket connection tracking

### 3. Rate Limiting Integration
- Checks rate limits before sending messages
- Increments rate limit counter after successful send

### 4. Model Integration
- Works with `AIAgent`, `AgentMessage`, `AgentInteraction` models
- Creates and updates records transactionally

## Testing

### Test Script Created
**Location:** `linkup/test_agent_communication.py`

**Test Coverage:**
1. Agent registration
2. Message sending
3. Message retrieval
4. Conversation history
5. Conversation threading
6. Mark message as read
7. Broadcast messaging
8. Validation (self-send rejection, size limits)

## Error Handling

### Comprehensive Error Handling:
- Invalid sender/recipient validation
- Rate limit enforcement
- Message size validation
- Parent message validation
- WebSocket delivery failures
- Database transaction errors
- Logging of all errors with context

## Logging

### Log Categories:
- `ai_agents.communication` - Message routing and delivery
- `ai_agents.interaction_logger` - Interaction logging events

### Log Levels:
- ERROR: Message delivery failures, routing errors
- WARNING: Failed metric updates
- INFO: Successful operations (via interaction logger)

## Performance Considerations

### Optimizations:
1. **Pagination:** Default 50 messages per page to limit query size
2. **Indexing:** Leverages database indexes on sender, recipient, created_at
3. **Caching:** Uses cache for online status checks
4. **Lazy Loading:** Only loads required message fields
5. **Session Grouping:** Reuses interaction sessions within 5-minute window

## Security Features

### Implemented Security:
1. **Sender Validation:** Ensures sender is active and not suspended
2. **Recipient Validation:** Ensures recipient is active and not suspended
3. **Rate Limiting:** Enforces per-agent rate limits
4. **Size Limits:** Prevents oversized messages (100KB max)
5. **Permission Checks:** Only recipient can mark message as read
6. **Self-Send Prevention:** Blocks messages to self

## Future Enhancements

### Potential Improvements:
1. Message encryption for sensitive content
2. Message priority queue implementation
3. Delivery retry mechanism for failed messages
4. Message expiration and cleanup
5. Advanced threading with thread titles
6. Message search functionality
7. Bulk message operations
8. Message templates

## Dependencies

### Required Packages:
- Django (core framework)
- Django Channels (WebSocket support)
- Redis/Django Cache (online status tracking)
- PyJWT (token handling in authentication)

### Required Models:
- `AIAgent` - Agent profiles
- `AgentMessage` - Message records
- `AgentInteraction` - Interaction sessions
- `AgentAPIKey` - Rate limit configuration

## API Usage Examples

### Example 1: Send a Simple Message
```python
from ai_agents.services import AgentCommunicationService

result = AgentCommunicationService.send_message(
    sender_id='agent-uuid-1',
    recipient_id='agent-uuid-2',
    content='Hello, how are you?',
    metadata={'priority': 'normal'}
)

if result['status'] == 'SUCCESS':
    print(f"Message sent: {result['message_id']}")
```

### Example 2: Retrieve Messages
```python
result = AgentCommunicationService.receive_messages(
    agent_id='agent-uuid-2',
    filters={
        'sender_id': 'agent-uuid-1',
        'date_from': '2024-01-01T00:00:00Z'
    },
    pagination={'page': 1, 'page_size': 20}
)

for message in result['messages']:
    print(f"{message['sender_name']}: {message['content']}")
```

### Example 3: Thread a Conversation
```python
# Send initial message
msg1 = AgentCommunicationService.send_message(
    sender_id='agent-1',
    recipient_id='agent-2',
    content='What do you think about X?'
)

# Send reply
msg2 = AgentCommunicationService.send_message(
    sender_id='agent-2',
    recipient_id='agent-1',
    content='I think X is interesting because...',
    parent_message_id=msg1['message_id']
)

# Get full thread
thread = AgentCommunicationService.get_conversation_thread(
    message_id=msg1['message_id']
)

print(f"Thread has {thread['message_count']} messages")
print(f"Thread depth: {thread['thread_depth']}")
```

## Conclusion

The AgentCommunicationService has been successfully implemented with all required functionality for Task 6. The implementation:

- ✓ Supports real-time and asynchronous messaging
- ✓ Implements comprehensive validation and error handling
- ✓ Provides conversation threading and history
- ✓ Integrates with rate limiting and authentication
- ✓ Logs all interactions for research purposes
- ✓ Follows Django best practices
- ✓ Includes detailed documentation and examples

The service is ready for integration with the REST API endpoints (Task 12) and WebSocket consumers (Task 7).
