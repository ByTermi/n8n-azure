# Configuration loader — reads environment variables from .env file
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Azure OpenAI Foundry endpoint for the bot's AI model
    FOUNDRY_PROJECT_ENDPOINT: str
    # AI model to use (default: gpt-4o-mini, a faster variant)
    FOUNDRY_MODEL: str = "gpt-4o-mini"
    # Telegram bot authentication token
    TELEGRAM_BOT_TOKEN: str
    # Default Telegram chat ID when sessionId is invalid (fallback)
    TELEGRAM_DEFAULT_CHAT_ID: str = ""

    class Config:
        # Load configuration from .env file in the project root
        env_file = ".env"


# Global settings instance — used throughout the app
settings = Settings()
