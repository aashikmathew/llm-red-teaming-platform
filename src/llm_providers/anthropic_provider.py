"""
Anthropic Claude LLM Provider implementation.
"""

import time
from typing import Dict, Any
import anthropic
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


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude provider for red teaming."""
    
    def __init__(self, api_key: str, model: str = "claude-3-sonnet-20240229"):
        super().__init__(api_key, model)
        # Use custom HTTP client to avoid proxy issues with httpx 0.28.1
        custom_http_client = ProxySafeHTTPClient()
        self.client = anthropic.AsyncAnthropic(
            api_key=api_key,
            http_client=custom_http_client
        )
        
        # Available models
        self.available_models = [
            "claude-3-sonnet-20240229",
            "claude-3-opus-20240229", 
            "claude-3-haiku-20240307",
            "claude-3-5-sonnet-20241022"
        ]
    
    async def generate_response(
        self, 
        prompt: str, 
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> LLMResponse:
        """Generate response using Anthropic API."""
        start_time = time.time()
        
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
                **kwargs
            )
            
            response_time = self._calculate_response_time(start_time)
            content = response.content[0].text if response.content else ""
            
            metadata = {
                "stop_reason": response.stop_reason,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                } if response.usage else {},
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            return self._create_response(content, response_time, metadata)
            
        except anthropic.RateLimitError as e:
            response_time = self._calculate_response_time(start_time)
            return self._create_response(
                "", response_time, {}, f"Rate limit exceeded: {str(e)}"
            )
        except anthropic.AuthenticationError as e:
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
        """Test Anthropic API connection."""
        try:
            response = await self.generate_response("Hello, world!", max_tokens=10)
            return response.success
        except Exception:
            return False

