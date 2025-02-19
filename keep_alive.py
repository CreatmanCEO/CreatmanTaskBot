import requests
import time
import os
from datetime import datetime
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def keep_alive():
    """
    Скрипт для предотвращения засыпания приложения на Render.com
    Отправляет запрос каждые 14 минут
    """
    app_url = os.environ.get("APP_URL", "https://your-app.onrender.com")
    
    while True:
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            response = requests.get(f"{app_url}/")
            
            if response.status_code == 200:
                logger.info(f"[{current_time}] Приложение активно")
            else:
                logger.warning(f"[{current_time}] Неожиданный статус: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Ошибка при проверке активности: {str(e)}")
            
        # Ждем 14 минут
        time.sleep(840)

if __name__ == "__main__":
    keep_alive() 