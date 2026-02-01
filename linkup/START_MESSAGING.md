# Quick Start Guide: Real-Time Messaging

## ✅ What's Already Done

Your real-time messaging system is now fully implemented with:

- ✅ WebSocket-based real-time chat
- ✅ Message history and persistence
- ✅ Read/unread status tracking
- ✅ Real-time notifications
- ✅ Message inbox with conversation list
- ✅ HTTP fallback when WebSocket fails
- ✅ Automatic reconnection
- ✅ Beautiful UI with sender/recipient styling

## 🚀 How to Start Using It

### Step 1: Run the Server

```bash
python manage.py runserver
```

The server now supports both HTTP and WebSocket connections automatically.

### Step 2: Test the Messaging

1. **Open your browser** and go to `http://127.0.0.1:8000/`

2. **Log in** with your account

3. **Visit another user's profile**:
   - Go to Network page
   - Click on any user's profile
   - Click the "Message" button

4. **Start chatting**:
   - Type a message in the input field
   - Press Enter or click "Send"
   - Messages appear in real-time!

5. **View all conversations**:
   - Click the notification bell icon in the navbar
   - Click "See all messages"
   - Or visit `/messages/` directly

### Step 3: Test Real-Time Features

To see real-time messaging in action:

1. **Open two browser windows** (or use incognito mode for the second)
2. **Log in as different users** in each window
3. **Start a conversation** from one window
4. **Watch messages appear instantly** in both windows!

## 📱 Features You Can Use

### 1. Send Messages
- Type and send messages to any user
- Messages are delivered instantly via WebSocket
- Automatic fallback to HTTP if WebSocket fails

### 2. View Message History
- All past messages are loaded when you open a chat
- Scroll to see older messages
- Messages are persisted in the database

### 3. Real-Time Notifications
- Notification badge shows unread message count
- Click the bell icon to see message previews
- Notifications update in real-time

### 4. Message Inbox
- See all your conversations in one place
- Unread message indicators
- Last message preview for each conversation
- Click any conversation to open the chat

### 5. Connection Status
- Green "Connected" = WebSocket is working
- Red "Disconnected" = Using HTTP fallback
- Automatic reconnection attempts

## 🔧 Current Configuration

### Channel Layer: In-Memory (Development Mode)

Your system is currently using **InMemoryChannelLayer**, which:
- ✅ Works immediately without Redis
- ✅ Perfect for development and testing
- ✅ No additional setup required
- ⚠️ Only works with a single server process
- ⚠️ Messages don't persist across server restarts

### Upgrading to Redis (Optional - For Production)

If you want to use Redis for better performance and multi-worker support:

1. **Install Redis**:
   ```bash
   # Ubuntu/Debian
   sudo apt-get install redis-server
   
   # macOS
   brew install redis
   ```

2. **Start Redis**:
   ```bash
   # Ubuntu/Debian
   sudo systemctl start redis-server
   
   # macOS
   brew services start redis
   
   # Or manually
   redis-server
   ```

3. **Update settings.py**:
   Uncomment the Redis configuration in `professional_network/settings.py`:
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

4. **Restart the server**

## 🎯 Usage Examples

### Example 1: Send a Message

1. Go to `/users/profile/john/` (replace 'john' with actual username)
2. Click "Message" button
3. Type "Hello!" and press Enter
4. Message appears instantly

### Example 2: Check Unread Messages

1. Click the notification bell icon (top right)
2. See unread message count in red badge
3. See message previews in dropdown
4. Click "See all messages" to view inbox

### Example 3: View Conversation History

1. Go to `/messages/`
2. See list of all conversations
3. Click any conversation to open chat
4. All message history loads automatically

## 🐛 Troubleshooting

### Messages Not Appearing?

1. **Check connection status** in the chat interface
   - Should show "Connected" in green
   - If red, WebSocket failed but HTTP fallback should work

2. **Check browser console** (F12 → Console tab)
   - Look for any JavaScript errors
   - WebSocket errors are normal if Redis isn't running

3. **Refresh the page**
   - Sometimes helps re-establish WebSocket connection

### WebSocket Connection Failed?

This is normal with InMemoryChannelLayer. The system will automatically use HTTP fallback:
- Messages still send and receive
- Just not in real-time (need to refresh)
- To fix: Install and run Redis (see above)

### Can't See Other User's Messages?

1. Make sure you're logged in as different users
2. Check that messages are being saved:
   ```bash
   python manage.py shell
   >>> from messaging.models import Message
   >>> Message.objects.all()
   ```

## 📚 API Reference

### URLs

- `/messages/` - Message inbox
- `/messages/chat/<username>/` - Chat with specific user
- `/messages/history/<username>/` - Get message history (JSON)
- `/messages/send/<username>/` - Send message via HTTP (JSON)
- `/messages/unread/` - Get unread count (JSON)

### WebSocket Endpoints

- `ws://localhost:8000/ws/chat/<username>/` - Real-time chat
- `ws://localhost:8000/ws/notifications/` - Real-time notifications

## 🎨 Customization

### Change Message Styling

Edit `messaging/static/messaging/chat.js` - look for the `appendMessage` function

### Change Notification Behavior

Edit `messaging/static/messaging/notifications.js`

### Modify Message Model

Edit `messaging/models.py` and run:
```bash
python manage.py makemigrations
python manage.py migrate
```

## ✨ What's Next?

Your messaging system is ready to use! Here are some ideas for enhancements:

- Add typing indicators
- Add file attachments
- Add message reactions (emoji)
- Add group chats
- Add message search
- Add voice/video calls
- Add message encryption

## 📞 Need Help?

1. Check `messaging/README.md` for detailed documentation
2. Run `python check_redis.py` to check Redis status
3. Check browser console for JavaScript errors
4. Check Django logs for server errors

---

**Enjoy your new real-time messaging system! 🎉**
