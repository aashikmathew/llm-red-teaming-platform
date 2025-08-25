"""
OpenAI LLM Provider implementation.
"""

import time
from typing import Dict, Any
import openai
import httpx
from .base_provider import BaseLLMProvider, LLMResponse


class ProxySafeHTTPClient:
    """Custom HTTP client that filters out proxy arguments for httpx compatibility."""
    
    def __init__(self, **kwargs):
        # Filter out proxy-related arguments that cause issues with httpx 0.28.1
        safe_kwargs = {k: v for k, v in kwargs.items() 
                       if k not in ['proxies', 'proxy', 'proxy_auth']}
        self.client = httpx.AsyncClient(**safe_kwargs)
    
    async def aclose(self):
        await self.client.aclose()
    
    def __getattr__(self, name):
        return getattr(self.client, name)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT provider for red teaming."""
    
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        super().__init__(api_key, model)
        # Use custom HTTP client to avoid proxy issues with httpx 0.28.1
        custom_http_client = ProxySafeHTTPClient()
        self.client = openai.AsyncOpenAI(
            api_key=api_key,
            http_client=custom_http_client
        )
        
        # Available models
        self.available_models = [
            "gpt-3.5-turbo",
            "gpt-4",
            "gpt-4-turbo-preview",
            "gpt-4o-mini"
        ]
    
    async def generate_response(
        self, 
        prompt: str, 
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> LLMResponse:
        """Generate response using OpenAI API."""
        start_time = time.time()
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            response_time = self._calculate_response_time(start_time)
            content = response.choices[0].message.content
            
            metadata = {
                "finish_reason": response.choices[0].finish_reason,
                "usage": dict(response.usage) if response.usage else {},
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            return self._create_response(content, response_time, metadata)
            
        except openai.RateLimitError as e:
            response_time = self._calculate_response_time(start_time)
            return self._create_response(
                "", response_time, {}, f"Rate limit exceeded: {str(e)}"
            )
        except openai.AuthenticationError as e:
            response_time = self._calculate_response_time(start_time)
            return self._create_response(
                "", response_time, {}, f"Authentication error: {str(e)}"
            )
        except Exception as e:
            response_time = self._calculate_response_time(start_time)
            return self._create_response(
                "", response_time, {}, f"Unexpected error: {str(e)}"
            )
    
    async def test_connection(self) -> bool:
        """Test OpenAI API connection."""
        try:
            response = await self.generate_response("Hello, world!", max_tokens=10)
            return response.success
        except Exception:
            return False

