from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, Union, List
from pydantic import field_validator
import json


# Known weak/default secrets that should never be used
BLOCKED_SECRETS = {
    "your-secret-key-change-in-production",
    "your-super-secret-key-change-in-production",
    "your_secret_key_change_in_production",
    "changeme",
    "secret",
    "secret-key",
    "secret_key",
    "123456",
    "password",
    "admin",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)
    
    # Application
    PROJECT_NAME: str = "GPS Assessment Platform"
    VERSION: str = "2.0.0"
    DESCRIPTION: str = "Gift, Passion, Story Assessment Platform API"
    DEBUG: bool = False
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Database - defaults to SQLite for local development
    DATABASE_URL: str = "sqlite:///./gps_local.db"
    
    # CORS
    CORS_ORIGINS: Union[List[str], str] = ["http://localhost:3000", "http://localhost:5173"]
    
    # Stripe
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_PUBLISHABLE_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    STRIPE_PRICE_MONTHLY: Optional[str] = None
    STRIPE_PRICE_YEARLY: Optional[str] = None
    
    # Resend (Email)
    RESEND_API_KEY: Optional[str] = None
    EMAIL_FROM: str = "noreply@giftpassionstory.com"
    
    # Frontend URL
    FRONTEND_URL: str = "http://localhost:5173"
    
    @field_validator('SECRET_KEY')
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validate that SECRET_KEY is not using a default/weak value."""
        if not v:
            raise ValueError(
                "SECRET_KEY is required. Generate a secure key using:\n"
                "python -c \"import secrets; print(secrets.token_urlsafe(32))\""
            )
        
        # Check against known default secrets
        if v.lower().strip() in BLOCKED_SECRETS:
            raise ValueError(
                f"Default/weak SECRET_KEY detected: '{v}'.\n"
                "Generate a secure key using:\n"
                "python -c \"import secrets; print(secrets.token_urlsafe(32))\"\n"
                "Never use default or example secrets in production."
            )
        
        # Check minimum length (256 bits = 32 bytes = ~43 base64 chars)
        if len(v) < 32:
            raise ValueError(
                f"SECRET_KEY is too short ({len(v)} chars). "
                "It must be at least 32 characters for security. "
                "Generate a secure key using:\n"
                "python -c \"import secrets; print(secrets.token_urlsafe(32))\""
            )
        
        return v
    
    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v: Union[List[str], str]) -> List[str]:
        """
        Parse CORS_ORIGINS from string or list.
        
        Handles:
        - List of strings: ["http://localhost:3000"]
        - JSON string: '["http://localhost:3000"]'
        - Comma-separated string: "http://localhost:3000,http://localhost:5173"
        """
        if isinstance(v, str):
            # Try JSON parsing first
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed]
            except json.JSONDecodeError:
                pass
            # Fall back to comma-separated
            return [origin.strip() for origin in v.split(',') if origin.strip()]
        elif isinstance(v, list):
            return [str(item).strip() for item in v]
        return v


settings = Settings()
