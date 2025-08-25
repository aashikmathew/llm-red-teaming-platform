"""
Google Gemini LLM Provider implementation.
"""

import time
from typing import Dict, Any
import google.generativeai as genai
from .base_provider import BaseLLMProvider, LLMResponse


class GoogleProvider(BaseLLMProvider):
    """Google Gemini provider for red teaming."""
    
    def __init__(self, api_key: str, model: str = "gemini-pro"):
        super().__init__(api_key, model)
        genai.configure(api_key=api_key)
        self.client = genai.GenerativeModel(model)
        
        # Available models
        self.available_models = [
            "gemini-pro",
            "gemini-pro-vision", 
            "gemini-1.5-pro",
            "gemini-1.5-flash"
        ]
    
    async def generate_response(
        self, 
        prompt: str, 
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> LLMResponse:
        """Generate response using Google Gemini API."""
        start_time = time.time()
        
        try:
            # Configure generation parameters
            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                **kwargs
            )
            
            response = await self.client.generate_content_async(
                prompt,
                generation_config=generation_config
            )
            
            response_time = self._calculate_response_time(start_time)
            content = response.text if response.text else ""
            
            metadata = {
                "finish_reason": response.candidates[0].finish_reason.name if response.candidates else None,
                "safety_ratings": [
                    {
                        "category": rating.category.name,
                        "probability": rating.probability.name
                    }
                    for rating in response.candidates[0].safety_ratings
                ] if response.candidates and response.candidates[0].safety_ratings else [],
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            return self._create_response(content, response_time, metadata)
            
        except Exception as e:
            response_time = self._calculate_response_time(start_time)
            error_msg = str(e)
            
            # Check for specific error types
            if "quota" in error_msg.lower() or "rate" in error_msg.lower():
                error_msg = f"Rate limit or quota exceeded: {error_msg}"
            elif "auth" in error_msg.lower() or "key" in error_msg.lower():
                error_msg = f"Authentication error: {error_msg}"
            else:
                error_msg = f"Unexpected error: {error_msg}"
                
            return self._create_response("", response_time, {}, error_msg)
    
    async def test_connection(self) -> bool:
        """Test Google Gemini API connection."""
        try:
            response = await self.generate_response("Hello, world!", max_tokens=10)
            return response.success
        except Exception:
            return False
