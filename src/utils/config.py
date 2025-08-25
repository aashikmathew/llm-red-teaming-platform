"""
Configuration management for the red teaming system.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration settings for the application."""
    
    # Server settings
    HOST: str = os.getenv("HOST", "localhost")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # API Keys
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    GOOGLE_API_KEY: Optional[str] = os.getenv("GOOGLE_API_KEY")
    HUGGINGFACE_API_TOKEN: Optional[str] = os.getenv("HUGGINGFACE_API_TOKEN")
    
    # Assessment settings
    DEFAULT_TEMPERATURE: float = float(os.getenv("DEFAULT_TEMPERATURE", "0.7"))
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "1000"))
    TIMEOUT_SECONDS: int = int(os.getenv("TIMEOUT_SECONDS", "30"))
    
    # File paths
    STATIC_DIR: str = "static"
    TEMPLATES_DIR: str = "templates"
    REPORTS_DIR: str = "reports"
    
    @classmethod
    def validate_api_keys(cls) -> dict:
        """Validate which API keys are available."""
        keys_status = {
            "openai": bool(cls.OPENAI_API_KEY),
            "anthropic": bool(cls.ANTHROPIC_API_KEY),
            "google": bool(cls.GOOGLE_API_KEY),
            "huggingface": bool(cls.HUGGINGFACE_API_TOKEN)
        }
        return keys_status
    
    @classmethod
    def get_available_providers(cls) -> list:
        """Get list of providers with valid API keys."""
        keys_status = cls.validate_api_keys()
        return [provider for provider, available in keys_status.items() if available]
