"""
AI Agent Integrations - Connect external AI agents (ChatGPT, Gemini, Claude, etc.)
to the platform for multi-agent interactions.
"""
import requests
import json
from typing import Dict, List, Optional, Any
from django.conf import settings
from .services import (
    AgentRegistryService,
    AgentAuthenticationService,
    AgentCommunicationService
)


class BaseAgentIntegration:
    """Base class for AI agent integrations."""
    
    def __init__(self, agent_name: str, api_key: str):
        self.agent_name = agent_name
        self.external_api_key = api_key
        self.platform_agent_id = None
        self.platform_api_key = None
        self.platform_jwt_token = None
    
    def register_on_platform(self, description: str, capabilities: Dict[str, Any]) -> Dict[str, Any]:
        """Register this AI agent on the platform."""
        result = AgentRegistryService.register_agent(
            name=self.agent_name,
            description=description,
            capabilities=capabilities,
            owner_email=f"{self.agent_name.lower()}@aiagent.platform",
            agent_type='CONVERSATIONAL'
        )
        
        if result['status'] == 'SUCCESS':
            self.platform_agent_id = result['agent_id']
            self.platform_api_key = result['api_key']
            print(f"✓ {self.agent_name} registered successfully!")
            print(f"  Agent ID: {self.platform_agent_id}")
            print(f"  API Key: {result['key_prefix']}...")
            return result
        else:
            print(f"✗ Failed to register {self.agent_name}: {result.get('error')}")
            return result
    
    def authenticate(self) -> Dict[str, Any]:
        """Authenticate and get JWT token."""
        if not self.platform_agent_id or not self.platform_api_key:
            return {'status': 'FAILED', 'error': 'Agent not registered'}
        
        result = AgentAuthenticationService.authenticate_agent(
            agent_id=self.platform_agent_id,
            api_key=self.platform_api_key
        )
        
        if result['status'] == 'SUCCESS':
            self.platform_jwt_token = result['access_token']
            print(f"✓ {self.agent_name} authenticated successfully!")
        
        return result
    
    def send_message_to_agent(
        self,
        recipient_agent_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Send a message to another agent on the platform."""
        return AgentCommunicationService.send_message(
            sender_id=self.platform_agent_id,
            recipient_id=recipient_agent_id,
            content=content,
            metadata=metadata or {},
            message_type='TEXT'
        )
    
    def process_with_external_api(self, prompt: str) -> str:
        """Process prompt with external AI API - to be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement this method")


class ChatGPTIntegration(BaseAgentIntegration):
    """Integration for OpenAI ChatGPT."""
    
    def __init__(self, api_key: str):
        super().__init__("ChatGPT-4", api_key)
        self.api_url = "https://api.openai.com/v1/chat/completions"
    
    def register(self):
        """Register ChatGPT on the platform."""
        return self.register_on_platform(
            description="OpenAI's ChatGPT-4 - Advanced conversational AI with broad knowledge",
            capabilities={
                "conversation": True,
                "code_generation": True,
                "creative_writing": True,
                "analysis": True,
                "languages": ["en", "es", "fr", "de", "zh", "ja"],
                "specialties": ["general_knowledge", "coding", "writing"]
            }
        )
    
    def process_with_external_api(self, prompt: str) -> str:
        """Send prompt to ChatGPT API."""
        # Demo mode - return mock response
        if self.external_api_key == 'demo-key':
            return f"""[ChatGPT-4 Demo Response]

Based on the question: "{prompt[:100]}..."

As ChatGPT-4, I would approach this by:
1. Breaking down the problem into key components
2. Providing practical, actionable advice
3. Drawing from a broad knowledge base

Key considerations:
- Scalability and performance
- Best practices and industry standards
- Real-world implementation examples

This is a demo response. Configure real API keys for actual ChatGPT responses."""
        
        try:
            headers = {
                "Authorization": f"Bearer {self.external_api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "gpt-4",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7
            }
            
            response = requests.post(self.api_url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            return result['choices'][0]['message']['content']
        
        except Exception as e:
            return f"Error calling ChatGPT API: {str(e)}"


class GeminiIntegration(BaseAgentIntegration):
    """Integration for Google Gemini."""
    
    def __init__(self, api_key: str):
        super().__init__("Gemini-Pro", api_key)
        self.api_url = f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={api_key}"
    
    def register(self):
        """Register Gemini on the platform."""
        return self.register_on_platform(
            description="Google's Gemini Pro - Multimodal AI with strong reasoning",
            capabilities={
                "conversation": True,
                "multimodal": True,
                "reasoning": True,
                "analysis": True,
                "languages": ["en", "es", "fr", "de", "zh", "ja", "ko"],
                "specialties": ["reasoning", "analysis", "multimodal"]
            }
        )
    
    def process_with_external_api(self, prompt: str) -> str:
        """Send prompt to Gemini API."""
        # Demo mode - return mock response
        if self.external_api_key == 'demo-key':
            return f"""[Gemini Pro Demo Response]

Analyzing: "{prompt[:100]}..."

From Gemini's multimodal perspective:

🔍 Analysis:
- This question requires reasoning across multiple domains
- I can provide insights from various angles
- Let me break this down systematically

💡 Key Insights:
- Technical accuracy is paramount
- Consider both short-term and long-term implications
- Balance theory with practical application

🎯 Recommendation:
A comprehensive approach that considers all stakeholders and use cases.

This is a demo response. Configure real API keys for actual Gemini responses."""
        
        try:
            headers = {"Content-Type": "application/json"}
            
            data = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }]
            }
            
            response = requests.post(self.api_url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            return result['candidates'][0]['content']['parts'][0]['text']
        
        except Exception as e:
            return f"Error calling Gemini API: {str(e)}"


class ClaudeIntegration(BaseAgentIntegration):
    """Integration for Anthropic Claude."""
    
    def __init__(self, api_key: str):
        super().__init__("Claude-3", api_key)
        self.api_url = "https://api.anthropic.com/v1/messages"
    
    def register(self):
        """Register Claude on the platform."""
        return self.register_on_platform(
            description="Anthropic's Claude 3 - Thoughtful AI with strong ethics",
            capabilities={
                "conversation": True,
                "analysis": True,
                "code_review": True,
                "ethical_reasoning": True,
                "languages": ["en", "es", "fr", "de", "zh", "ja"],
                "specialties": ["analysis", "ethics", "detailed_explanations"]
            }
        )
    
    def process_with_external_api(self, prompt: str) -> str:
        """Send prompt to Claude API."""
        # Demo mode - return mock response
        if self.external_api_key == 'demo-key':
            return f"""[Claude 3 Demo Response]

Thank you for this thoughtful question: "{prompt[:100]}..."

Let me provide a careful, nuanced analysis:

📋 Ethical Considerations:
- We should consider the impact on all stakeholders
- Long-term sustainability is crucial
- Transparency and accountability matter

🔬 Detailed Analysis:
I've examined this from multiple angles, considering both the immediate implications and broader context. Here's what stands out:

1. First Principle: Understanding the core requirements
2. Second Principle: Balancing competing interests
3. Third Principle: Ensuring responsible implementation

⚖️ Balanced Perspective:
While there are valid arguments on multiple sides, the most responsible approach would consider both innovation and caution.

This is a demo response. Configure real API keys for actual Claude responses."""
        
        try:
            headers = {
                "x-api-key": self.external_api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "claude-3-opus-20240229",
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}]
            }
            
            response = requests.post(self.api_url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            return result['content'][0]['text']
        
        except Exception as e:
            return f"Error calling Claude API: {str(e)}"


class MultiAgentOrchestrator:
    """Orchestrates interactions between multiple AI agents."""
    
    def __init__(self):
        self.agents: Dict[str, BaseAgentIntegration] = {}
    
    def add_agent(self, agent: BaseAgentIntegration):
        """Add an agent to the orchestrator."""
        self.agents[agent.agent_name] = agent
    
    def collaborative_response(
        self,
        user_question: str,
        agent_names: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """
        Get responses from multiple agents and combine them.
        
        Args:
            user_question: The question to ask
            agent_names: List of agent names to query (None = all agents)
        
        Returns:
            Dictionary mapping agent names to their responses
        """
        if agent_names is None:
            agent_names = list(self.agents.keys())
        
        responses = {}
        
        for agent_name in agent_names:
            if agent_name not in self.agents:
                continue
            
            agent = self.agents[agent_name]
            
            # Get response from external API
            response = agent.process_with_external_api(user_question)
            responses[agent_name] = response
            
            print(f"\n{'='*60}")
            print(f"{agent_name} Response:")
            print(f"{'='*60}")
            print(response)
        
        return responses
    
    def agent_to_agent_discussion(
        self,
        topic: str,
        agent_names: List[str],
        rounds: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Facilitate a discussion between agents.
        
        Args:
            topic: Discussion topic
            agent_names: List of agents to participate
            rounds: Number of discussion rounds
        
        Returns:
            List of discussion messages
        """
        discussion = []
        context = f"Topic: {topic}\n\n"
        
        for round_num in range(rounds):
            print(f"\n{'#'*60}")
            print(f"Round {round_num + 1}")
            print(f"{'#'*60}")
            
            for agent_name in agent_names:
                if agent_name not in self.agents:
                    continue
                
                agent = self.agents[agent_name]
                
                # Build prompt with context
                prompt = f"{context}Please provide your perspective on this topic."
                
                # Get response
                response = agent.process_with_external_api(prompt)
                
                # Log on platform
                message_data = {
                    'round': round_num + 1,
                    'agent': agent_name,
                    'message': response
                }
                discussion.append(message_data)
                
                # Update context for next agent
                context += f"\n{agent_name}: {response}\n"
                
                print(f"\n{agent_name}:")
                print(response)
        
        return discussion
    
    def consensus_building(
        self,
        question: str,
        agent_names: List[str]
    ) -> Dict[str, Any]:
        """
        Get multiple agent perspectives and build consensus.
        
        Args:
            question: Question to answer
            agent_names: Agents to consult
        
        Returns:
            Dictionary with individual responses and consensus
        """
        # Get initial responses
        responses = self.collaborative_response(question, agent_names)
        
        # Build consensus prompt
        consensus_prompt = f"Question: {question}\n\n"
        consensus_prompt += "Different AI perspectives:\n\n"
        
        for agent_name, response in responses.items():
            consensus_prompt += f"{agent_name}: {response}\n\n"
        
        consensus_prompt += "Based on these perspectives, what is the consensus or best combined answer?"
        
        # Use first agent to synthesize
        if agent_names and agent_names[0] in self.agents:
            synthesizer = self.agents[agent_names[0]]
            consensus = synthesizer.process_with_external_api(consensus_prompt)
        else:
            consensus = "Unable to build consensus"
        
        return {
            'question': question,
            'individual_responses': responses,
            'consensus': consensus
        }


# Utility functions for easy setup

def setup_demo_agents() -> MultiAgentOrchestrator:
    """
    Setup demo agents for testing (uses mock responses if no API keys).
    """
    orchestrator = MultiAgentOrchestrator()
    
    # Note: In production, get these from environment variables
    chatgpt_key = getattr(settings, 'OPENAI_API_KEY', 'demo-key')
    gemini_key = getattr(settings, 'GOOGLE_API_KEY', 'demo-key')
    claude_key = getattr(settings, 'ANTHROPIC_API_KEY', 'demo-key')
    
    # Create and register agents
    chatgpt = ChatGPTIntegration(chatgpt_key)
    chatgpt.register()
    chatgpt.authenticate()
    orchestrator.add_agent(chatgpt)
    
    gemini = GeminiIntegration(gemini_key)
    gemini.register()
    gemini.authenticate()
    orchestrator.add_agent(gemini)
    
    claude = ClaudeIntegration(claude_key)
    claude.register()
    claude.authenticate()
    orchestrator.add_agent(claude)
    
    return orchestrator


def demo_multi_agent_interaction():
    """
    Demo function showing multi-agent interaction.
    """
    print("="*60)
    print("Multi-Agent AI Platform Demo")
    print("="*60)
    
    # Setup agents
    orchestrator = setup_demo_agents()
    
    # Example 1: Collaborative response
    print("\n\n" + "="*60)
    print("Example 1: Collaborative Response")
    print("="*60)
    
    question = "What are the key considerations for building a scalable web application?"
    responses = orchestrator.collaborative_response(question)
    
    # Example 2: Agent discussion
    print("\n\n" + "="*60)
    print("Example 2: Agent-to-Agent Discussion")
    print("="*60)
    
    topic = "The future of artificial intelligence in healthcare"
    discussion = orchestrator.agent_to_agent_discussion(
        topic=topic,
        agent_names=["ChatGPT-4", "Gemini-Pro"],
        rounds=2
    )
    
    # Example 3: Consensus building
    print("\n\n" + "="*60)
    print("Example 3: Consensus Building")
    print("="*60)
    
    question = "What is the best programming language for beginners?"
    consensus = orchestrator.consensus_building(
        question=question,
        agent_names=["ChatGPT-4", "Gemini-Pro", "Claude-3"]
    )
    
    print("\n\nConsensus:")
    print(consensus['consensus'])
    
    return orchestrator
