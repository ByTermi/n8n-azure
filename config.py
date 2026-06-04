# Cargador de configuración — lee variables de entorno del archivo .env
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Endpoint de Azure OpenAI Foundry para el modelo de IA del bot
    FOUNDRY_PROJECT_ENDPOINT: str
    # Modelo de IA a usar (predeterminado: gpt-4o-mini, variante más rápida)
    FOUNDRY_MODEL: str = "gpt-4o-mini"
    # Token de autenticación del bot de Telegram
    TELEGRAM_BOT_TOKEN: str
    # ID de chat de Telegram predeterminado cuando sessionId es inválido (respaldo)
    TELEGRAM_DEFAULT_CHAT_ID: str = ""

    class Config:
        # Carga la configuración desde archivo .env en la raíz del proyecto
        env_file = ".env"


# Instancia global de configuración — usada en toda la aplicación
settings = Settings()
