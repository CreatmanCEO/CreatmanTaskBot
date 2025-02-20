# app/db/session.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.config import get_settings
import os

settings = get_settings()

# Создаем директорию для базы данных если её нет
os.makedirs('data', exist_ok=True)

# Используем SQLite для локальной базы данных
SQLITE_URL = "sqlite+aiosqlite:///data/app.db"

# Создаем асинхронный движок SQLAlchemy
engine = create_async_engine(
    SQLITE_URL,
    echo=settings.DEBUG  # Включаем логирование SQL только в режиме отладки
)

# Создаем фабрику сессий
async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Функция для получения сессии
async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session