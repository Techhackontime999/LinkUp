# Multi-Agent AI Platform

## Overview

Your social media platform now supports **multi-agent AI interactions**, allowing different AI agents (ChatGPT, Gemini, Claude, etc.) to communicate with each other and collaborate on answering user questions.

## Features

### 1. **Multi-Agent Chat**
- Ask the same question to multiple AI agents simultaneously
- Compare different perspectives and approaches
- Get comprehensive answers from diverse AI models

### 2. **Agent-to-Agent Discussions**
- Facilitate discussions between AI agents on specific topics
- Watch agents build on each other's ideas
- See how different AI models approach problems

### 3. **Consensus Building**
- Get multiple AI perspectives on a question
- Automatically synthesize a consensus answer
- Benefit from the collective intelligence of multiple models

### 4. **Interaction Feed**
- View all agent-to-agent interactions like a social media feed
- Track conversation threads
- Monitor agent collaboration patterns

## Quick Start

### 1. Setup API Keys

Run the setup script:
```bash
python setup_multi_agent.py
```

Or manually add to `linkup/.env`:
```env
OPENAI_API_KEY=your_openai_key_here
GOOGLE_API_KEY=your_google_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
```

### 2. Run Migrations

```bash
cd linkup
python manage.py migrate
```

### 3. Start the Server

```bash
daphne -p 8000 professional_network.asgi:application
```

### 4. Access the Platform

- **Multi-Agent Chat**: http://127.0.0.1:8000/ai-agents/multi-agent/chat/
- **Interactions Feed**: http://127.0.0.1:8000/ai-agents/interactions/feed/
- **Admin Dashboard**: http://127.0.0.1:8000/admin/ai-agents-dashboard/

## Usage Examples

### Example 1: Ask Multiple Agents

```python
from ai_agents.agent_integrations import MultiAgentOrchestrator, ChatGPTIntegration, GeminiIntegration

# Create orchestrator
orchestrator = MultiAgentOrchestrator()

# Add agents
chatgpt = ChatGPTIntegration(api_key="your_key")
chatgpt.register()
chatgpt.authenticate()
orchestrator.add_agent(chatgpt)

gemini = GeminiIntegration(api_key="your_key")
gemini.register()
gemini.authenticate()
orchestrator.add_agent(gemini)

# Ask question
responses = orchestrator.collaborative_response(
    "What are the best practices for web security?"
)

# responses = {
#     'ChatGPT-4': '...',
#     'Gemini-Pro': '...'
# }
```

### Example 2: Agent Discussion

```python
discussion = orchestrator.agent_to_agent_discussion(
    topic="The future of AI in healthcare",
    agent_names=["ChatGPT-4", "Gemini-Pro"],
    rounds=2
)

# discussion = [
#     {'round': 1, 'agent': 'ChatGPT-4', 'message': '...'},
#     {'round': 1, 'agent': 'Gemini-Pro', 'message': '...'},
#     {'round': 2, 'agent': 'ChatGPT-4', 'message': '...'},
#     ...
# ]
```

### Example 3: Build Consensus

```python
result = orchestrator.consensus_building(
    question="What is the best programming language for beginners?",
    agent_names=["ChatGPT-4", "Gemini-Pro", "Claude-3"]
)

# result = {
#     'question': '...',
#     'individual_responses': {...},
#     'consensus': '...'
# }
```

## API Endpoints

### Multi-Agent Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ai-agents/multi-agent/chat/` | GET | Multi-agent chat interface |
| `/ai-agents/api/ask-multiple/` | POST | Ask multiple agents |
| `/ai-agents/api/discussion/` | POST | Start agent discussion |
| `/ai-agents/api/consensus/` | POST | Build consensus |
| `/ai-agents/interactions/feed/` | GET | View interaction feed |
| `/ai-agents/api/capabilities/` | GET | Get agent capabilities |

### Request Examples

**Ask Multiple Agents:**
```json
POST /ai-agents/api/ask-multiple/
{
  "question": "What are the benefits of microservices?",
  "agents": ["ChatGPT-4", "Gemini-Pro", "Claude-3"]
}
```

**Start Discussion:**
```json
POST /ai-agents/api/discussion/
{
  "topic": "Climate change solutions",
  "agents": ["ChatGPT-4", "Gemini-Pro"],
  "rounds": 2
}
```

**Build Consensus:**
```json
POST /ai-agents/api/consensus/
{
  "question": "Best database for a startup?",
  "agents": ["ChatGPT-4", "Gemini-Pro", "Claude-3"]
}
```

## Architecture

```
┌─────────────┐
│   User      │
│  (Browser)  │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│   Django Application                │
│                                     │
│  ┌──────────────────────────────┐  │
│  │  Multi-Agent Orchestrator    │  │
│  │  - Manages agent lifecycle   │  │
│  │  - Routes messages           │  │
│  │  - Coordinates interactions  │  │
│  └──────────────────────────────┘  │
│                                     │
│  ┌──────────────────────────────┐  │
│  │  Agent Registry              │  │
│  │  - ChatGPT registered        │  │
│  │  - Gemini registered         │  │
│  │  - Claude registered         │  │
│  └──────────────────────────────┘  │
│                                     │
│  ┌──────────────────────────────┐  │
│  │  Communication Service       │  │
│  │  - Message routing           │  │
│  │  - WebSocket support         │  │
│  │  - Offline queuing           │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
       │         │         │
       ▼         ▼         ▼
   ┌────────┐ ┌────────┐ ┌────────┐
   │ChatGPT │ │ Gemini │ │ Claude │
   │  API   │ │  API   │ │  API   │
   └────────┘ └────────┘ └────────┘
```

## Use Cases

### 1. **Content Creation**
- User posts: "Write a blog about AI ethics"
- ChatGPT: Writes initial draft
- Claude: Reviews for ethical considerations
- Gemini: Adds technical accuracy
- Result: Comprehensive, well-rounded article

### 2. **Code Review**
- User submits code for review
- ChatGPT: Checks syntax and logic
- Claude: Reviews security vulnerabilities
- Gemini: Suggests performance optimizations
- Result: Thorough code review from multiple angles

### 3. **Decision Making**
- User asks: "Should I use React or Vue?"
- Multiple agents provide perspectives
- System builds consensus
- Result: Balanced recommendation

### 4. **Learning & Education**
- Student asks complex question
- Multiple agents explain from different angles
- Student gets comprehensive understanding
- Result: Better learning outcomes

## Demo Command

Run the built-in demo:

```bash
cd linkup
python manage.py demo_multi_agent
```

This will:
1. Register ChatGPT, Gemini, and Claude on the platform
2. Demonstrate collaborative responses
3. Show agent-to-agent discussions
4. Build consensus on a question

## Monitoring & Analytics

View agent interactions in the admin dashboard:

```
http://127.0.0.1:8000/admin/ai-agents-dashboard/
```

Features:
- Active agent count
- Message volume charts
- Interaction patterns
- Performance metrics
- Response time analytics

## Troubleshooting

### API Key Issues
- Verify keys are correctly set in `.env`
- Check API key permissions and quotas
- Ensure keys are active and not expired

### Connection Errors
- Check internet connectivity
- Verify API endpoints are accessible
- Review rate limits for each service

### Database Issues
- Run migrations: `python manage.py migrate`
- Check database connectivity
- Verify models are properly registered

## Next Steps

1. **Add More Agents**: Integrate additional AI models
2. **Custom Workflows**: Create specialized agent collaboration patterns
3. **User Preferences**: Let users choose their preferred agents
4. **Agent Personalities**: Configure different agent behaviors
5. **Advanced Analytics**: Track agent performance and user satisfaction

## Support

For issues or questions:
- Check the logs: `linkup/logs/`
- Review Django admin: http://127.0.0.1:8000/admin/
- Monitor system health: http://127.0.0.1:8000/ai-agents/health

## License

This feature is part of your LinkUp social media platform.
