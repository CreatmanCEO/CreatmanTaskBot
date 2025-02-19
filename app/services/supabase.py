from supabase import create_client, Client
from app.core.config import settings
from app.utils.logger import app_logger
from typing import Optional, Dict, Any

class SupabaseService:
    """Сервис для работы с Supabase."""
    
    def __init__(self):
        self.supabase: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_ANON_KEY
        )
        
    async def get_user_trello_token(self, telegram_id: str) -> Optional[str]:
        """
        Получение токена Trello пользователя.
        
        Args:
            telegram_id: Telegram ID пользователя
            
        Returns:
            Optional[str]: Токен Trello или None
        """
        try:
            response = self.supabase.table('users').select('trello_token').eq('telegram_id', telegram_id).execute()
            if response.data:
                return response.data[0].get('trello_token')
            return None
        except Exception as e:
            app_logger.error(f"Ошибка при получении токена Trello: {str(e)}")
            return None
            
    async def save_user_trello_token(self, telegram_id: str, token: str) -> bool:
        """
        Сохранение токена Trello пользователя.
        
        Args:
            telegram_id: Telegram ID пользователя
            token: Токен Trello
            
        Returns:
            bool: True если успешно, False в случае ошибки
        """
        try:
            response = self.supabase.table('users').upsert({
                'telegram_id': telegram_id,
                'trello_token': token
            }).execute()
            return bool(response.data)
        except Exception as e:
            app_logger.error(f"Ошибка при сохранении токена Trello: {str(e)}")
            return False
            
    async def get_user_preferences(self, telegram_id: str) -> Dict[str, Any]:
        """
        Получение предпочтений пользователя.
        
        Args:
            telegram_id: Telegram ID пользователя
            
        Returns:
            Dict[str, Any]: Предпочтения пользователя
        """
        try:
            response = self.supabase.table('user_preferences').select('*').eq('telegram_id', telegram_id).execute()
            if response.data:
                return response.data[0]
            return {}
        except Exception as e:
            app_logger.error(f"Ошибка при получении предпочтений: {str(e)}")
            return {}
            
    async def save_user_preferences(self, telegram_id: str, preferences: Dict[str, Any]) -> bool:
        """
        Сохранение предпочтений пользователя.
        
        Args:
            telegram_id: Telegram ID пользователя
            preferences: Предпочтения для сохранения
            
        Returns:
            bool: True если успешно, False в случае ошибки
        """
        try:
            data = {
                'telegram_id': telegram_id,
                **preferences
            }
            response = self.supabase.table('user_preferences').upsert(data).execute()
            return bool(response.data)
        except Exception as e:
            app_logger.error(f"Ошибка при сохранении предпочтений: {str(e)}")
            return False

# Создаем глобальный экземпляр для использования во всем приложении
supabase_service = SupabaseService() 