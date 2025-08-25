"""
Base LLM Provider interface for red teaming system.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
import time


@dataclass
class LLMResponse:
    """Standardized LLM response format."""
    content: str
    model: str
    provider: str
    response_time: float
    word_count: int
    metadata: Dict[str, Any]
    error: Optional[str] = None
    
    @property
    def success(self) -> bool:
        """Check if response was successful."""
        return self.error is None


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self.provider_name = self.__class__.__name__.replace('Provider', '').lower()
    
    @abstractmethod
    async def generate_response(
        self, 
        prompt: str, 
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> LLMResponse:
        """Generate response from LLM."""
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """Test API connection and credentials."""
        pass
    
    def _calculate_response_time(self, start_time: float) -> float:
        """Calculate response time in seconds."""
        return round(time.time() - start_time, 3)
    
    def _count_words(self, text: str) -> int:
        """Count words in response text."""
        return len(text.split())
    
    def _create_response(
        self,
        content: str,
        response_time: float,
        metadata: Dict[str, Any],
        error: Optional[str] = None
    ) -> LLMResponse:
        """Create standardized LLM response."""
        return LLMResponse(
            content=content,
            model=self.model,
            provider=self.provider_name,
            response_time=response_time,
            word_count=self._count_words(content) if content else 0,
            metadata=metadata,
            error=error
        )

