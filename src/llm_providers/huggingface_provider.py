"""
HuggingFace LLM Provider implementation.
"""

import time
from typing import Dict, Any
import aiohttp
import json
from .base_provider import BaseLLMProvider, LLMResponse


class HuggingFaceProvider(BaseLLMProvider):
    """HuggingFace Inference API provider for red teaming."""
    
    def __init__(self, api_key: str, model: str = "microsoft/DialoGPT-medium"):
        super().__init__(api_key, model)
        self.api_url = f"https://api-inference.huggingface.co/models/{model}"
        self.headers = {"Authorization": f"Bearer {api_key}"}
        
        # Available models
        self.available_models = [
            "microsoft/DialoGPT-medium",
            "microsoft/DialoGPT-large",
            "facebook/blenderbot-400M-distill",
            "microsoft/GODEL-v1_1-base-seq2seq",
            "EleutherAI/gpt-j-6B",
            "bigscience/bloom-560m"
        ]
    
    async def generate_response(
        self, 
        prompt: str, 
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> LLMResponse:
        """Generate response using HuggingFace Inference API."""
        start_time = time.time()
        
        try:
            payload = {
                "inputs": prompt,
                "parameters": {
                    "temperature": temperature,
                    "max_new_tokens": max_tokens,
                    "return_full_text": False,
                    **kwargs
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload
                ) as response:
                    response_time = self._calculate_response_time(start_time)
                    
                    if response.status == 200:
                        result = await response.json()
                        
                        # Handle different response formats
                        if isinstance(result, list) and len(result) > 0:
                            if "generated_text" in result[0]:
                                content = result[0]["generated_text"]
                            else:
                                content = str(result[0])
                        else:
                            content = str(result)
                        
                        metadata = {
                            "status_code": response.status,
                            "temperature": temperature,
                            "max_tokens": max_tokens,
                            "model_type": "huggingface_inference"
                        }
                        
                        return self._create_response(content, response_time, metadata)
                    
                    elif response.status == 429:
                        error_text = await response.text()
                        return self._create_response(
                            "", response_time, {}, f"Rate limit exceeded: {error_text}"
                        )
                    elif response.status == 401:
                        error_text = await response.text()
                        return self._create_response(
                            "", response_time, {}, f"Authentication error: {error_text}"
                        )
                    else:
                        error_text = await response.text()
                        return self._create_response(
                            "", response_time, {}, f"HTTP {response.status}: {error_text}"
                        )
                        
        except aiohttp.ClientError as e:
            response_time = self._calculate_response_time(start_time)
            return self._create_response(
                "", response_time, {}, f"Network error: {str(e)}"
            )
        except Exception as e:
            response_time = self._calculate_response_time(start_time)
            return self._create_response(
                "", response_time, {}, f"Unexpected error: {str(e)}"
            )
    
    async def test_connection(self) -> bool:
        """Test HuggingFace API connection."""
        try:
            response = await self.generate_response("Hello, world!", max_tokens=10)
            return response.success
        except Exception:
            return False
