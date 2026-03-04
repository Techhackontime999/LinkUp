"""
Third-Party AI Provider Integration

Supports multiple AI providers with free-tier options:
- Google Gemini (Free tier available)
- OpenAI ChatGPT (Free trial available)
- Anthropic Claude (Free tier available)
- Hugging Face (Free tier available)
- Cohere (Free tier available)
"""
import os
import logging
import requests
from typing import Dict, List, Optional
from django.conf import settings

logger = logging.getLogger(__name__)


class AIProviderBase:
    """Base class for AI providers"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate AI response"""
        raise NotImplementedError
    
    def validate_api_key(self) -> bool:
        """Validate API key"""
        raise NotImplementedError


class GeminiProvider(AIProviderBase):
    """
    Google Gemini AI Provider
    
    Free Tier: Yes (60 requests per minute)
    Get API Key: https://makersuite.google.com/app/apikey
    """
    
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
    
    def __init__(self, api_key: str, model: str = "gemini-pro"):
        super().__init__(api_key)
        self.model = model
    
    def generate_response(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> str:
        """
        Generate response using Gemini API
        
        Args:
            prompt: User prompt
            max_tokens: Maximum tokens in response
            temperature: Creativity level (0-1)
        
        Returns:
            Generated text response
        """
        try:
            url = f"{self.BASE_URL}/models/{self.model}:generateContent"
            
            headers = {
                "Content-Type": "application/json"
            }
            
            data = {
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }],
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens,
                }
            }
            
            response = requests.post(
                f"{url}?key={self.api_key}",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and len(result['candidates']) > 0:
                    return result['candidates'][0]['content']['parts'][0]['text']
                else:
                    logger.error(f"Unexpected Gemini response format: {result}")
                    return "I apologize, but I couldn't generate a response."
            else:
                logger.error(f"Gemini API error: {response.status_code} - {response.text}")
                return "I'm having trouble connecting right now. Please try again."
                
        except Exception as e:
            logger.error(f"Gemini generation error: {str(e)}")
            return "I encountered an error. Please try again."
    
    def validate_api_key(self) -> bool:
        """Validate Gemini API key"""
        try:
            response = self.generate_response("Hello", max_tokens=10)
            return bool(response and not response.startswith("I'm having trouble"))
        except:
            return False


class OpenAIProvider(AIProviderBase):
    """
    OpenAI ChatGPT Provider
    
    Free Tier: $5 free credit for new accounts
    Get API Key: https://platform.openai.com/api-keys
    """
    
    BASE_URL = "https://api.openai.com/v1"
    
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        super().__init__(api_key)
        self.model = model
    
    def generate_response(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7, system_prompt: str = None) -> str:
        """
        Generate response using OpenAI API
        
        Args:
            prompt: User prompt
            max_tokens: Maximum tokens in response
            temperature: Creativity level (0-2)
            system_prompt: System message for context
        
        Returns:
            Generated text response
        """
        try:
            url = f"{self.BASE_URL}/chat/completions"
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            data = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
                return "I'm having trouble connecting right now. Please try again."
                
        except Exception as e:
            logger.error(f"OpenAI generation error: {str(e)}")
            return "I encountered an error. Please try again."
    
    def validate_api_key(self) -> bool:
        """Validate OpenAI API key"""
        try:
            response = self.generate_response("Hello", max_tokens=10)
            return bool(response and not response.startswith("I'm having trouble"))
        except:
            return False


class AnthropicProvider(AIProviderBase):
    """
    Anthropic Claude Provider
    
    Free Tier: Limited free credits for new accounts
    Get API Key: https://console.anthropic.com/
    """
    
    BASE_URL = "https://api.anthropic.com/v1"
    
    def __init__(self, api_key: str, model: str = "claude-3-haiku-20240307"):
        super().__init__(api_key)
        self.model = model
    
    def generate_response(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7, system_prompt: str = None) -> str:
        """
        Generate response using Anthropic API
        
        Args:
            prompt: User prompt
            max_tokens: Maximum tokens in response
            temperature: Creativity level (0-1)
            system_prompt: System message for context
        
        Returns:
            Generated text response
        """
        try:
            url = f"{self.BASE_URL}/messages"
            
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01"
            }
            
            data = {
                "model": self.model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }
            
            if system_prompt:
                data["system"] = system_prompt
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                return result['content'][0]['text']
            else:
                logger.error(f"Anthropic API error: {response.status_code} - {response.text}")
                return "I'm having trouble connecting right now. Please try again."
                
        except Exception as e:
            logger.error(f"Anthropic generation error: {str(e)}")
            return "I encountered an error. Please try again."
    
    def validate_api_key(self) -> bool:
        """Validate Anthropic API key"""
        try:
            response = self.generate_response("Hello", max_tokens=10)
            return bool(response and not response.startswith("I'm having trouble"))
        except:
            return False


class HuggingFaceProvider(AIProviderBase):
    """
    Hugging Face Inference API Provider
    
    Free Tier: Yes (rate limited)
    Get API Key: https://huggingface.co/settings/tokens
    """
    
    BASE_URL = "https://api-inference.huggingface.co/models"
    
    def __init__(self, api_key: str, model: str = "mistralai/Mistral-7B-Instruct-v0.2"):
        super().__init__(api_key)
        self.model = model
    
    def generate_response(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> str:
        """
        Generate response using Hugging Face API
        
        Args:
            prompt: User prompt
            max_tokens: Maximum tokens in response
            temperature: Creativity level (0-1)
        
        Returns:
            Generated text response
        """
        try:
            url = f"{self.BASE_URL}/{self.model}"
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": max_tokens,
                    "temperature": temperature,
                    "return_full_text": False
                }
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    return result[0].get('generated_text', '')
                return str(result)
            else:
                logger.error(f"Hugging Face API error: {response.status_code} - {response.text}")
                return "I'm having trouble connecting right now. Please try again."
                
        except Exception as e:
            logger.error(f"Hugging Face generation error: {str(e)}")
            return "I encountered an error. Please try again."
    
    def validate_api_key(self) -> bool:
        """Validate Hugging Face API key"""
        try:
            response = self.generate_response("Hello", max_tokens=10)
            return bool(response and not response.startswith("I'm having trouble"))
        except:
            return False


class CohereProvider(AIProviderBase):
    """
    Cohere AI Provider
    
    Free Tier: Yes (trial API key)
    Get API Key: https://dashboard.cohere.com/api-keys
    """
    
    BASE_URL = "https://api.cohere.ai/v1"
    
    def __init__(self, api_key: str, model: str = "command"):
        super().__init__(api_key)
        self.model = model
    
    def generate_response(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> str:
        """
        Generate response using Cohere API
        
        Args:
            prompt: User prompt
            max_tokens: Maximum tokens in response
            temperature: Creativity level (0-5)
        
        Returns:
            Generated text response
        """
        try:
            url = f"{self.BASE_URL}/generate"
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model,
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if 'generations' in result and len(result['generations']) > 0:
                    return result['generations'][0]['text']
                return "I apologize, but I couldn't generate a response."
            else:
                logger.error(f"Cohere API error: {response.status_code} - {response.text}")
                return "I'm having trouble connecting right now. Please try again."
                
        except Exception as e:
            logger.error(f"Cohere generation error: {str(e)}")
            return "I encountered an error. Please try again."
    
    def validate_api_key(self) -> bool:
        """Validate Cohere API key"""
        try:
            response = self.generate_response("Hello", max_tokens=10)
            return bool(response and not response.startswith("I'm having trouble"))
        except:
            return False


class AIProviderFactory:
    """Factory to create AI provider instances"""
    
    PROVIDERS = {
        'gemini': GeminiProvider,
        'openai': OpenAIProvider,
        'anthropic': AnthropicProvider,
        'huggingface': HuggingFaceProvider,
        'cohere': CohereProvider,
    }
    
    @classmethod
    def create_provider(cls, provider_name: str, api_key: str, model: str = None) -> AIProviderBase:
        """
        Create an AI provider instance
        
        Args:
            provider_name: Name of the provider (gemini, openai, anthropic, etc.)
            api_key: API key for the provider
            model: Optional model name
        
        Returns:
            AI provider instance
        """
        provider_class = cls.PROVIDERS.get(provider_name.lower())
        
        if not provider_class:
            raise ValueError(f"Unknown provider: {provider_name}")
        
        if model:
            return provider_class(api_key, model=model)
        return provider_class(api_key)
    
    @classmethod
    def get_available_providers(cls) -> List[Dict[str, str]]:
        """Get list of available providers with details"""
        return [
            {
                'id': 'gemini',
                'name': 'Google Gemini',
                'free_tier': True,
                'signup_url': 'https://makersuite.google.com/app/apikey',
                'models': ['gemini-pro', 'gemini-pro-vision']
            },
            {
                'id': 'openai',
                'name': 'OpenAI ChatGPT',
                'free_tier': True,
                'signup_url': 'https://platform.openai.com/api-keys',
                'models': ['gpt-3.5-turbo', 'gpt-4']
            },
            {
                'id': 'anthropic',
                'name': 'Anthropic Claude',
                'free_tier': True,
                'signup_url': 'https://console.anthropic.com/',
                'models': ['claude-3-haiku-20240307', 'claude-3-sonnet-20240229']
            },
            {
                'id': 'huggingface',
                'name': 'Hugging Face',
                'free_tier': True,
                'signup_url': 'https://huggingface.co/settings/tokens',
                'models': ['mistralai/Mistral-7B-Instruct-v0.2', 'meta-llama/Llama-2-7b-chat-hf']
            },
            {
                'id': 'cohere',
                'name': 'Cohere',
                'free_tier': True,
                'signup_url': 'https://dashboard.cohere.com/api-keys',
                'models': ['command', 'command-light']
            }
        ]


# Helper function to get provider from AI model
def get_provider_for_model(ai_model) -> Optional[AIProviderBase]:
    """
    Get AI provider instance for an AI model
    
    Args:
        ai_model: AIAgent instance
    
    Returns:
        AI provider instance or None
    """
    try:
        metadata = ai_model.metadata or {}
        provider_name = metadata.get('provider')
        api_key = metadata.get('api_key')
        model_name = metadata.get('model')
        
        if not provider_name or not api_key:
            logger.warning(f"AI model {ai_model.id} missing provider configuration")
            return None
        
        return AIProviderFactory.create_provider(provider_name, api_key, model_name)
        
    except Exception as e:
        logger.error(f"Error creating provider for model {ai_model.id}: {str(e)}")
        return None
