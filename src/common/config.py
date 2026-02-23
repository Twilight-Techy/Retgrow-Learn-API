import os
from typing import List
from dotenv import load_dotenv
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings

# Load environment variables from the correct .env file
os.environ["APP_ENV"] = "development"  # Default to development
env_file = ".env" if os.getenv("APP_ENV") == "development" else ".env.production"
load_dotenv(env_file)  # Load the .env file

class Settings(BaseSettings):
    APP_ENV: str = "development"
    DEBUG: bool = True
    FRONTEND_URL: str
    SUPPORT_URL: str
    # DB_HOST: str
    # DB_PORT: int
    # DB_USER: str
    # DB_PASSWORD: str
    # DB_NAME: str
    DATABASE_URL: str
    ALEMBIC_DATABASE_URL: str
    JWT_SECRET: str
    JWT_ALGORITHM: str
    JWT_EXPIRATION_MINUTES: int
    JWT_REFRESH_SECRET: str
    JWT_REFRESH_EXPIRATION_DAYS: int = 7
    ALLOWED_ORIGINS: List[str] = ["*"]
    LOG_LEVEL: str = "info"

    # Email settings
    EMAIL_SENDER: str
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USE_TLS: bool
    SMTP_USER: str
    SMTP_PASSWORD: str
    CONTACT_RECIPIENT: str

    # Payment Provider Settings
    PAYSTACK_SECRET_KEY: str = ""
    PAYSTACK_PUBLIC_KEY: str = ""
    OPAY_PUBLIC_KEY: str = ""
    OPAY_SECRET_KEY: str = ""
    OPAY_MERCHANT_ID: str = ""
    OPAY_ENVIRONMENT: str = "sandbox"
    STRIPE_SECRET_KEY: str = ""       # Optional — not yet configured
    STRIPE_WEBHOOK_SECRET: str = ""   # Optional — not yet configured
    CRON_SECRET: str = "secret"
    
    # Google Auth Settings
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/auth/google/callback"

    # Uncomment if you want to support comma-separated ALLOWED_ORIGINS strings
    @field_validator("ALLOWED_ORIGINS", mode="before")
    def split_origins(cls, value):
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def validate_production_secrets(self):
        """Ensure critical secrets are set when running in production."""
        if self.APP_ENV == "production":
            missing = []
            # Payment keys required in production
            for key in [
                "PAYSTACK_SECRET_KEY", "PAYSTACK_PUBLIC_KEY",
                # "OPAY_PUBLIC_KEY", "OPAY_SECRET_KEY", "OPAY_MERCHANT_ID",
                # "STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET",
            ]:
                if not getattr(self, key):
                    missing.append(key)
            if missing:
                raise ValueError(
                    f"Missing required secrets for production: {', '.join(missing)}"
                )
        return self

settings = Settings()