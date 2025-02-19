from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Telegram
    TELEGRAM_TOKEN: str
    
    # Trello
    TRELLO_API_KEY: str
    TRELLO_TOKEN: str
    
    # OpenAI
    OPENAI_API_KEY: str
    
    # Database
    DATABASE_URL: str
    
    # Redis
    REDIS_URL: str
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()