# app/db/session.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.config import get_settings

settings = get_settings()

# Создаем асинхронный движок SQLAlchemy
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True  # Включаем логирование SQL
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