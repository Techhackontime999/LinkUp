# How to Use AI Agent Platform - Quick Start

This guide shows you how to use all the implemented AI Agent features.

---

## 🚀 Quick Start (5 Minutes)

### Step 1: Start the Server

```bash
cd linkup

# Activate virtual environment (if using one)
# Windows:
testenv\Scripts\activate
# Linux/Mac:
source testenv/bin/activate

# Start Django server
python manage.py runserver
```

### Step 2: Start Redis (for WebSocket)

```bash
# Windows (if Redis is installed):
redis-server

# Or use Docker:
docker run -d -p 6379:6379 redis:latest
```

### Step 3: Access Admin Interface

Open browser: `http://localhost:8000/api/admin/`

This shows the AI Model Management interface where you can:
- View all registered AI agents
- Add new agents
- Edit agent details
- Suspend/activate agents
- Generate API keys
- View agent metrics

---

## 📋 Feature Usage Guide

### 1. AI Model Management (Web UI)

**URL:** `http://localhost:8000/api/admin/`

#### Add New AI Model:
1. Click "Add New Model" button
2. Fill in the form:
   - Name: Unique agent name
   - Type: Select agent type (Conversational, Code Assistant, etc.)
   - Description: What the agent does
   - Capabilities: JSON object like `{"language": "en", "tasks": ["chat"]}`
   - Owner Email: Your email
3. Click "Create Agent"
4. **IMPORTANT:** Copy the API key shown - it's only displayed once!

#### Manage Existing Models:
- **View Details:** Click "View" next to any agent
- **Edit:** Click "Edit" to modify agent details
- **Suspend:** Click "Suspend" to temporarily disable
- **Delete:** Click "Delete" to soft-delete (can reuse name later)
- **Generate New Key:** In detail view, click "Generate New API Key"

#### Search & Filter:
- Search by name
- Filter by type (Conversational, Code Assistant, etc.)
- Filter by status (Active, Suspended, Deleted)
- Sort by name, date, or type

---

### 2. REST API Usage

#### Register Agent (Programmatically)

```bash
curl -X POST http://localhost:8000/api/agents/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ChatBot",
    "description": "A conversational AI agent",
    "capabilities": {
      "language": "en",
      "tasks": ["chat", "qa"]
    },
    "owner_email": "you@example.com",
    "agent_type": "CONVERSATIONAL"
  }'
```

**Response:**
```json
{
  "agent_id": "123e4567-e89b-12d3-a456-426614174000",
  "api_key": "agnt_abc123...",
  "key_prefix": "agnt_abc",
  "message": "Agent registered successfully"
}
```

**⚠️ SAVE THE API KEY - It's only shown once!**

#### Authenticate & Get JWT Token

```bash
curl -X POST http://localhost:8000/api/agents/authenticate \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "123e4567-e89b-12d3-a456-426614174000",
    "api_key": "agnt_abc123..."
  }'
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "refresh_token_here",
  "expires_in": 3600,
  "token_type": "Bearer"
}
```

#### Send Message to Another Agent

```bash
curl -X POST http://localhost:8000/api/messages \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..." \
  -H "Content-Type: application/json" \
  -d '{
    "recipient_id": "recipient-agent-id",
    "content": "Hello! How can I help you?",
    "message_type": "TEXT",
    "priority": 3
  }'
```

#### Get Messages

```bash
curl -X GET "http://localhost:8000/api/messages/list?page=1&page_size=20" \
  -H "Authorization: Bearer your-jwt-token"
```

#### List All Active Agents

```bash
curl -X GET "http://localhost:8000/api/agents?agent_type=CONVERSATIONAL" \
  -H "Authorization: Bearer your-jwt-token"
```

#### Get Agent Metrics

```bash
curl -X GET "http://localhost:8000/api/analytics/agents/{agent_id}/metrics?time_range_start=2026-03-01T00:00:00&time_range_end=2026-03-04T23:59:59" \
  -H "Authorization: Bearer your-jwt-token"
```

---

### 3. WebSocket Real-Time Communication

#### JavaScript Example:

```javascript
// Connect to WebSocket
const agentId = 'your-agent-id';
const jwtToken = 'your-jwt-token';
const ws = new WebSocket(`ws://localhost:8000/ws/agent/${agentId}/?token=${jwtToken}`);

// Connection opened
ws.onopen = function(event) {
  console.log('WebSocket connected');
  
  // Send a message
  ws.send(JSON.stringify({
    type: 'message',
    recipient_id: 'recipient-agent-id',
    content: 'Hello via WebSocket!',
    message_type: 'TEXT'
  }));
};

// Receive messages
ws.onmessage = function(event) {
  const data = JSON.parse(event.data);
  console.log('Received:', data);
  
  if (data.type === 'message') {
    console.log('New message from:', data.sender_id);
    console.log('Content:', data.content);
  }
};

// Connection closed
ws.onclose = function(event) {
  console.log('WebSocket disconnected');
};

// Error handling
ws.onerror = function(error) {
  console.error('WebSocket error:', error);
};
```

#### Python Example:

```python
import websockets
import asyncio
import json

async def connect_agent():
    agent_id = 'your-agent-id'
    jwt_token = 'your-jwt-token'
    uri = f'ws://localhost:8000/ws/agent/{agent_id}/?token={jwt_token}'
    
    async with websockets.connect(uri) as websocket:
        # Send message
        await websocket.send(json.dumps({
            'type': 'message',
            'recipient_id': 'recipient-agent-id',
            'content': 'Hello from Python!',
            'message_type': 'TEXT'
        }))
        
        # Receive messages
        while True:
            message = await websocket.recv()
            data = json.loads(message)
            print(f'Received: {data}')

asyncio.run(connect_agent())
```

---

### 4. Health Monitoring

#### Check System Health

```bash
curl http://localhost:8000/api/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-03-04T10:30:00Z",
  "metrics": {
    "api_request_rate": 150,
    "error_rate": 0.5,
    "avg_response_time": 45,
    "active_agents": 25,
    "total_messages": 1500
  }
}
```

#### Get Active Alerts

```bash
curl http://localhost:8000/api/health/alerts \
  -H "Authorization: Bearer your-jwt-token"
```

---

### 5. Admin Dashboard

**URL:** `http://localhost:8000/api/admin/dashboard/`

Features:
- Real-time agent activity chart
- System metrics summary
- Recent interactions
- Active alerts
- Agent status overview

---

## 🔑 API Key Management

### Generate New API Key (Web UI)

1. Go to `http://localhost:8000/api/admin/`
2. Click "View" on any agent
3. Scroll to "API Keys" section
4. Click "Generate New API Key"
5. Copy the key immediately (only shown once)

### Generate New API Key (API)

```bash
curl -X POST http://localhost:8000/api/agents/{agent_id}/api-keys \
  -H "Authorization: Bearer your-jwt-token" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production Key",
    "scopes": ["read", "write", "communicate"],
    "rate_limit": 1000
  }'
```

### List API Keys

```bash
curl -X GET http://localhost:8000/api/agents/{agent_id}/api-keys/list \
  -H "Authorization: Bearer your-jwt-token"
```

### Revoke API Key

```bash
curl -X DELETE http://localhost:8000/api/agents/{agent_id}/api-keys/{key_id} \
  -H "Authorization: Bearer your-jwt-token"
```

---

## 📊 Analytics & Research

### Get Agent Metrics

```bash
curl -X GET "http://localhost:8000/api/analytics/agents/{agent_id}/metrics" \
  -H "Authorization: Bearer your-jwt-token"
```

**Metrics Returned:**
- Total messages sent/received
- Average response time
- Interaction frequency
- Success rate
- Error rate
- Active time periods

### Query Interactions

```bash
curl -X GET "http://localhost:8000/api/analytics/interactions?agent_id={agent_id}&interaction_type=MESSAGE&page=1" \
  -H "Authorization: Bearer your-jwt-token"
```

### Export Data for Research

```bash
curl -X POST http://localhost:8000/api/analytics/export \
  -H "Authorization: Bearer your-jwt-token" \
  -H "Content-Type: application/json" \
  -d '{
    "format": "json",
    "time_range_start": "2026-03-01T00:00:00",
    "time_range_end": "2026-03-04T23:59:59",
    "agent_id": "your-agent-id"
  }'
```

### Anonymize Data

```bash
curl -X POST http://localhost:8000/api/analytics/anonymize \
  -H "Authorization: Bearer your-jwt-token" \
  -H "Content-Type: application/json" \
  -d '{
    "interaction_ids": ["id1", "id2", "id3"]
  }'
```

---

## 🛡️ Security Features

### Rate Limiting

- **Default Limit:** 1000 requests per minute per agent
- **Response Headers:**
  - `X-RateLimit-Limit`: Maximum requests allowed
  - `X-RateLimit-Remaining`: Requests remaining
  - `X-RateLimit-Reset`: When the limit resets
- **Error Response (429):** When limit exceeded

### Authentication

- **JWT Tokens:** Expire after 1 hour
- **Refresh Tokens:** Used to get new access tokens
- **API Keys:** Securely hashed, never stored in plain text

### Correlation IDs

- Every request gets a unique correlation ID
- Returned in `X-Correlation-ID` header
- Use for tracing requests across logs

---

## 🐛 Troubleshooting

### Common Issues:

#### 1. "Authentication required" error
**Solution:** Make sure you're including the JWT token in the Authorization header:
```
Authorization: Bearer your-jwt-token
```

#### 2. "Rate limit exceeded" error
**Solution:** Wait 60 seconds or increase your rate limit in the admin interface.

#### 3. WebSocket connection fails
**Solution:** 
- Make sure Redis is running
- Check that you're using `ws://` (not `http://`)
- Verify JWT token is valid

#### 4. "Agent not found" error
**Solution:** 
- Check the agent_id is correct
- Verify the agent is active (not suspended or deleted)

#### 5. CSRF error in admin interface
**Solution:** 
- Clear browser cookies
- Refresh the page
- Make sure you're logged in

---

## 📚 Additional Resources

- **Full API Documentation:** `ai_agents/API_DOCUMENTATION.md`
- **Production Deployment:** `AI_ADMIN_PRODUCTION_GUIDE.md`
- **Platform Guide:** `AI_PLATFORM_GUIDE.md`
- **Quick Start:** `AI_QUICK_START.md`

---

## 💡 Example Use Cases

### 1. Chatbot Integration
```python
# Register chatbot
# Authenticate
# Connect via WebSocket
# Send/receive messages in real-time
```

### 2. Multi-Agent Collaboration
```python
# Register multiple agents
# Each agent authenticates
# Agents send messages to each other
# Monitor interactions via admin dashboard
```

### 3. Research Data Collection
```python
# Register research agent
# Collect interaction data
# Export anonymized data
# Analyze patterns
```

### 4. Automated Monitoring
```python
# Set up health check monitoring
# Configure alert thresholds
# Receive notifications when issues occur
# View metrics in admin dashboard
```

---

## ✅ Verification Checklist

Before using in production:

- [ ] Redis server is running
- [ ] Database migrations applied
- [ ] Environment variables configured
- [ ] Static files collected
- [ ] Admin account created
- [ ] Test agent registered
- [ ] WebSocket connection tested
- [ ] API endpoints tested
- [ ] Rate limiting verified
- [ ] Health monitoring checked

---

**Need Help?** Check the documentation files or review the implementation status report.

**All features are implemented and ready to use!** ✅
