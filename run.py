import uvicorn
import os
from app.core.config import settings
from app.db.base import Base, engine
from app.utils.logger import app_logger

def init_db():
    """Инициализация базы данных."""
    try:
        # Создаем таблицы
        Base.metadata.create_all(bind=engine)
        app_logger.info("База данных инициализирована успешно")
    except Exception as e:
        app_logger.error(f"Ошибка при инициализации базы данных: {str(e)}")
        raise

def main():
    """Основная функция запуска приложения."""
    try:
        # Инициализируем базу данных
        init_db()
        
        # Получаем порт из переменных окружения (Render устанавливает PORT)
        port = int(os.environ.get("PORT", 8000))
        
        # Запускаем приложение
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=port,
            reload=settings.DEBUG,
            workers=1
        )
    except Exception as e:
        app_logger.error(f"Ошибка при запуске приложения: {str(e)}")
        raise

if __name__ == "__main__":
    main()