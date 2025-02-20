import uvicorn
import os
from app.core.config import settings
from app.utils.logger import app_logger

def main():
    """Основная функция запуска приложения."""
    try:
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