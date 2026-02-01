# Real-Time Messaging System

This Django application provides real-time messaging functionality using Django Channels and WebSockets.

## Features

- ✅ Real-time one-on-one chat
- ✅ Message history
- ✅ Read/unread status tracking
- ✅ Real-time notifications
- ✅ WebSocket with HTTP fallback
- ✅ Message inbox with conversation list
- ✅ Automatic reconnection

## Architecture

### Backend Components

1. **Models** (`models.py`)
   - `Message`: Stores chat messages with sender, recipient, content, timestamps, and read status

2. **Views** (`views.py`)
   - `messages_inbox`: Lists all conversations
   - `chat_view`: Renders the chat interface
   - `fetch_history`: Returns message history as JSON
   - `send_message_fallback`: HTTP fallback for sending messages
   - `unread_notifications`: Returns unread message count and previews

3. **WebSocket Consumers** (`consumers.py`)
   - `ChatConsumer`: Handles real-time chat messages
   - `NotificationsConsumer`: Handles real-time notifications

4. **URL Routing** (`urls.py`, `routing.py`)
   - HTTP routes for views
   - WebSocket routes for consumers

### Frontend Components

1. **Chat Interface** (`templates/messaging/chat.html`)
   - Message display with sender/recipient styling
   - Input form for sending messages
   - Connection status indicator

2. **Chat JavaScript** (`static/messaging/chat.js`)
   - WebSocket connection management
   - Message sending/receiving
   - Automatic reconnection
   - HTTP fallback

3. **Notifications JavaScript** (`static/messaging/notifications.js`)
   - Real-time notification updates
   - Unread message badge
   - Notification dropdown

4. **Inbox** (`templates/messaging/inbox.html`)
   - List of all conversations
   - Unread message indicators
   - Last message preview

## Setup Instructions

### 1. Install Dependencies

All required packages are in `requirements.txt`:

```bash
pip install -r requirements.txt
```

### 2. Setup Redis

Redis is required for Django Channels to work in production.

**Install Redis:**
- Ubuntu/Debian: `sudo apt-get install redis-server`
- macOS: `brew install redis`
- Windows: Download from https://redis.io/download

**Start Redis:**
```bash
# Ubuntu/Debian
sudo systemctl start redis-server

# macOS
brew services start redis

# Or run manually
redis-server
```

**Verify Redis:**
```bash
redis-cli ping
# Should return: PONG
```

**Check Redis Status:**
```bash
python check_redis.py
```

### 3. Run Migrations

```bash
python manage.py makemigrations messaging
python manage.py migrate
```

### 4. Run the Development Server

Use Daphne (ASGI server) instead of the default Django runserver:

```bash
daphne -b 0.0.0.0 -p 8000 professional_network.asgi:application
```

Or use the standard runserver (which now supports ASGI):

```bash
python manage.py runserver
```

## Usage

### Starting a Conversation

1. Visit a user's profile
2. Click the "Message" button
3. You'll be redirected to the chat interface

### Viewing All Messages

1. Click the notification bell icon in the navbar
2. Click "See all messages" at the bottom
3. Or visit `/messages/` directly

### Sending Messages

1. Type your message in the input field
2. Press Enter or click "Send"
3. Messages are sent via WebSocket (real-time)
4. If WebSocket fails, HTTP fallback is used automatically

## API Endpoints

### HTTP Endpoints

- `GET /messages/` - Message inbox
- `GET /messages/chat/<username>/` - Chat interface
- `GET /messages/history/<username>/` - Fetch message history (JSON)
- `POST /messages/send/<username>/` - Send message via HTTP (fallback)
- `GET /messages/unread/` - Get unread message count and previews (JSON)

### WebSocket Endpoints

- `ws://localhost:8000/ws/chat/<username>/` - Real-time chat
- `ws://localhost:8000/ws/notifications/` - Real-time notifications

## WebSocket Message Format

### Sending a Message

```json
{
  "message": "Hello, how are you?"
}
```

### Receiving a Message

```json
{
  "id": 123,
  "sender": "john_doe",
  "recipient": "jane_smith",
  "content": "Hello, how are you?",
  "created_at": "2026-01-29T10:30:00Z"
}
```

## Configuration

### Channel Layers (settings.py)

**Production (with Redis):**
```python
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [('127.0.0.1', 6379)],
        },
    },
}
```

**Development (without Redis):**
```python
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer'
    }
}
```

Note: InMemoryChannelLayer doesn't support multiple workers and won't work across multiple server instances.

### ASGI Configuration (asgi.py)

The ASGI application is configured to handle both HTTP and WebSocket connections:

```python
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
```

## Troubleshooting

### WebSocket Connection Fails

1. **Check Redis:**
   ```bash
   python check_redis.py
   ```

2. **Check Console Errors:**
   Open browser DevTools → Console tab
   Look for WebSocket connection errors

3. **Verify ASGI Server:**
   Make sure you're using Daphne or another ASGI server, not just `runserver`

4. **Check Firewall:**
   Ensure port 8000 is accessible

### Messages Not Appearing

1. **Check WebSocket Status:**
   Look at the connection status indicator in the chat interface

2. **Check Browser Console:**
   Look for JavaScript errors

3. **Verify Database:**
   ```bash
   python manage.py shell
   >>> from messaging.models import Message
   >>> Message.objects.all()
   ```

### HTTP Fallback Not Working

1. **Check CSRF Token:**
   Ensure CSRF token is present in cookies

2. **Check Network Tab:**
   Open DevTools → Network tab
   Look for failed POST requests

## Security Considerations

1. **Authentication Required:**
   All messaging endpoints require user authentication

2. **CSRF Protection:**
   HTTP fallback uses CSRF tokens

3. **WebSocket Authentication:**
   WebSocket connections use Django session authentication

4. **Message Privacy:**
   Users can only see messages they sent or received

5. **Input Sanitization:**
   All message content is escaped to prevent XSS attacks

## Performance Tips

1. **Use Redis in Production:**
   InMemoryChannelLayer is only for development

2. **Index Database:**
   Message model has indexes on sender/recipient + created_at

3. **Limit Message History:**
   Currently fetches last 200 messages per conversation

4. **Connection Pooling:**
   Configure Redis connection pooling for high traffic

## Future Enhancements

- [ ] Group chat support
- [ ] File attachments
- [ ] Message editing/deletion
- [ ] Typing indicators
- [ ] Message reactions
- [ ] Voice/video calls
- [ ] Message search
- [ ] Push notifications
- [ ] Message encryption

## Testing

### Manual Testing

1. Open two browser windows (or use incognito mode)
2. Log in as different users in each window
3. Start a conversation
4. Send messages and verify they appear in real-time

### Automated Testing

```bash
python manage.py test messaging
```

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review Django Channels documentation: https://channels.readthedocs.io/
3. Check Redis documentation: https://redis.io/documentation
