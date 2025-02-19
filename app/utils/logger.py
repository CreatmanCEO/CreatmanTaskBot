import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
import json
from datetime import datetime

class CustomFormatter(logging.Formatter):
    """Пользовательский форматтер для логов с поддержкой цветного вывода в консоль."""
    
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    
    FORMATS = {
        logging.DEBUG: grey + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + reset,
        logging.INFO: grey + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + reset,
        logging.WARNING: yellow + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + reset,
        logging.ERROR: red + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + reset,
        logging.CRITICAL: bold_red + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

def setup_logger(name: str, log_level=logging.INFO):
    """
    Настройка логгера с поддержкой вывода в файл и консоль.
    
    Args:
        name: Имя логгера
        log_level: Уровень логирования
        
    Returns:
        logging.Logger: Настроенный логгер
    """
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # Создаем директорию для логов если её нет
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Настраиваем вывод в файл
    file_handler = RotatingFileHandler(
        filename=log_dir / f"{name}.log",
        maxBytes=5*1024*1024,  # 5MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    logger.addHandler(file_handler)

    # Настраиваем вывод в консоль
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(CustomFormatter())
    logger.addHandler(console_handler)

    return logger

class JsonFileHandler(RotatingFileHandler):
    """Обработчик для записи логов в JSON формате."""
    
    def emit(self, record):
        try:
            msg = self.format(record)
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "level": record.levelname,
                "message": record.getMessage(),
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno
            }
            
            if hasattr(record, "extra"):
                log_entry.update(record.extra)
                
            with open(self.baseFilename, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry) + "\n")
                
        except Exception:
            self.handleError(record)

# Создаем основной логгер приложения
app_logger = setup_logger('creatman_bot')

# Пример использования:
# from app.utils.logger import app_logger
# app_logger.info("Сообщение")
# app_logger.error("Ошибка", extra={"user_id": 123, "action": "create_task"}) 