from pydantic_settings import BaseSettings
from typing import List, Optional
import secrets
from functools import lru_cache
from datetime import datetime
import pytz

class Settings(BaseSettings):
    """Настройки приложения."""
    
    # Основные настройки приложения
    APP_NAME: str = "CreatmanTaskBot"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    APP_URL: str
    LOG_LEVEL: str = "INFO"
    TIMEZONE: str = "UTC"
    DEFAULT_LANGUAGE: str = "ru"
    
    # Настройки Supabase
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE: str
    JWT_SECRET: str
    
    # Настройки Telegram
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_WEBHOOK_URL: Optional[str] = None
    
    # Настройки OpenAI
    OPENAI_API_KEY: str
    
    # База данных
    DATABASE_URL: str
    
    # Redis
    REDIS_URL: str
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = []
    
    @property
    def current_time(self) -> datetime:
        """Получение текущего времени в настроенном часовом поясе."""
        return datetime.now(pytz.timezone(self.TIMEZONE))
    
    class Config:
        case_sensitive = True
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    """
    Получение настроек приложения с кэшированием.
    
    Returns:
        Settings: Объект настроек
    """
    return Settings()

settings = get_settings() 