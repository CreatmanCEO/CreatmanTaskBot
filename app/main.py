from fastapi import FastAPI, Request
from app.bot.handlers import router as bot_router
from app.core.config import settings
import logging

# Настройка логирования
logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.PROJECT_NAME)

# Добавляем роутер для вебхуков
app.include_router(bot_router)

# Эндпоинт для проверки работоспособности
@app.get("/health")
async def health_check():
    return {"status": "ok"}

# Эндпоинт для предотвращения засыпания
@app.get("/")
async def keep_alive():
    return {"status": "alive"}

# Обработка ошибок
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global error handler: {str(exc)}")
    return {"error": str(exc)}