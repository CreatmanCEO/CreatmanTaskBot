import re
import requests
from typing import Optional, Dict, Any
from app.core.config import settings
from app.utils.logger import app_logger

class TrelloService:
    """Сервис для работы с Trello API."""
    
    BASE_URL = "https://api.trello.com/1"
    TOKEN_PATTERN = r"^[0-9a-f]{64}$"

    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Accept": "application/json"
        }
        self.params = {
            "key": settings.TRELLO_API_KEY,
            "token": token
        }

    @staticmethod
    def validate_token_format(token: str) -> bool:
        """
        Проверка формата токена Trello.
        
        Args:
            token: Токен для проверки
            
        Returns:
            bool: True если формат верный, False в противном случае
        """
        return bool(re.match(TrelloService.TOKEN_PATTERN, token))

    def validate_token(self) -> bool:
        """
        Проверка валидности токена через API Trello.
        
        Returns:
            bool: True если токен валидный, False в противном случае
        """
        try:
            response = requests.get(
                f"{self.BASE_URL}/members/me",
                headers=self.headers,
                params=self.params
            )
            return response.status_code == 200
        except Exception as e:
            app_logger.error(f"Ошибка при валидации токена Trello: {str(e)}")
            return False

    def get_user_email(self) -> Optional[str]:
        """
        Получение email пользователя Trello.
        
        Returns:
            Optional[str]: Email пользователя или None в случае ошибки
        """
        try:
            response = requests.get(
                f"{self.BASE_URL}/members/me",
                headers=self.headers,
                params={**self.params, "fields": "email"}
            )
            if response.status_code == 200:
                return response.json().get("email")
            return None
        except Exception as e:
            app_logger.error(f"Ошибка при получении email пользователя Trello: {str(e)}")
            return None

    def verify_user_email(self, email: str) -> bool:
        """
        Проверка соответствия email пользователя.
        
        Args:
            email: Email для проверки
            
        Returns:
            bool: True если email совпадает, False в противном случае
        """
        trello_email = self.get_user_email()
        return trello_email and trello_email.lower() == email.lower()

    def get_boards(self) -> Optional[list]:
        """
        Получение списка досок пользователя.
        
        Returns:
            Optional[list]: Список досок или None в случае ошибки
        """
        try:
            response = requests.get(
                f"{self.BASE_URL}/members/me/boards",
                headers=self.headers,
                params={**self.params, "fields": "name,url"}
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            app_logger.error(f"Ошибка при получении списка досок Trello: {str(e)}")
            return None 