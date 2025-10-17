"""Environment configuration for the Stack Overflow MCP server."""

import logging
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Config(BaseSettings):
    """Configuration manager for Stack Overflow MCP server.
    
    Uses Pydantic for automatic validation and type coercion.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    stack_exchange_api_key: str = Field(
        ...,
        description="Stack Exchange API key for increased rate limits",
        validation_alias="STACK_EXCHANGE_API_KEY",
    )
    
    max_requests_per_window: int = Field(
        default=30,
        ge=1,
        le=100,
        description="Maximum requests allowed per rate limit window",
    )
    
    rate_limit_window_ms: int = Field(
        default=60000,
        ge=1000,
        description="Rate limit window duration in milliseconds",
    )
    
    retry_after_ms: int = Field(
        default=2000,
        ge=100,
        description="Delay after hitting rate limit in milliseconds",
    )

    @field_validator("stack_exchange_api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Validate API key is not empty."""
        if not v or v.isspace():
            raise ValueError(
                "STACK_EXCHANGE_API_KEY is required and cannot be empty. "
                "Get your API key at: https://stackapps.com/apps/oauth/register"
            )
        return v.strip()


@lru_cache
def get_config() -> Config:
    """Get cached configuration instance.
    
    Returns:
        Config: Validated configuration instance.
        
    Raises:
        ValidationError: If configuration is invalid.
    """
    logger.info("Loading configuration from environment")
    return Config()  # type: ignore[call-arg]


# Global config instance for backward compatibility
config = get_config()
