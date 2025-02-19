from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

@dataclass
class UserState:
    """Состояние пользователя."""
    user_id: int
    current_action: Optional[str] = None
    selected_board_id: Optional[str] = None
    selected_list_id: Optional[str] = None
    forwarded_messages: List[Dict] = field(default_factory=list)
    message_context: Dict = field(default_factory=dict)
    temp_data: Dict = field(default_factory=dict)
    last_activity: datetime = field(default_factory=datetime.now)

    def clear(self):
        """Очистка состояния."""
        self.current_action = None
        self.selected_board_id = None
        self.selected_list_id = None
        self.forwarded_messages.clear()
        self.message_context.clear()
        self.temp_data.clear()
        self.last_activity = datetime.now()

class StateManager:
    """Менеджер состояний пользователей."""
    
    def __init__(self):
        self._states: Dict[int, UserState] = {}
        self._board_preferences: Dict[int, Dict] = {}

    def get_user_state(self, user_id: int) -> UserState:
        """
        Получение состояния пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            UserState: Состояние пользователя
        """
        if user_id not in self._states:
            self._states[user_id] = UserState(user_id=user_id)
        return self._states[user_id]

    def clear_user_state(self, user_id: int):
        """
        Очистка состояния пользователя.
        
        Args:
            user_id: ID пользователя
        """
        if user_id in self._states:
            self._states[user_id].clear()

    def add_forwarded_message(self, user_id: int, message: Dict):
        """
        Добавление пересланного сообщения.
        
        Args:
            user_id: ID пользователя
            message: Информация о сообщении
        """
        state = self.get_user_state(user_id)
        state.forwarded_messages.append(message)
        state.last_activity = datetime.now()

    def get_forwarded_messages(self, user_id: int) -> List[Dict]:
        """
        Получение пересланных сообщений.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            List[Dict]: Список пересланных сообщений
        """
        state = self.get_user_state(user_id)
        return state.forwarded_messages

    def clear_forwarded_messages(self, user_id: int):
        """
        Очистка пересланных сообщений.
        
        Args:
            user_id: ID пользователя
        """
        state = self.get_user_state(user_id)
        state.forwarded_messages.clear()

    def set_board_preferences(self, user_id: int, preferences: Dict):
        """
        Установка предпочтений по доскам.
        
        Args:
            user_id: ID пользователя
            preferences: Предпочтения пользователя
        """
        self._board_preferences[user_id] = preferences

    def get_board_preferences(self, user_id: int) -> Dict:
        """
        Получение предпочтений по доскам.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Dict: Предпочтения пользователя
        """
        return self._board_preferences.get(user_id, {})

    def update_message_context(self, user_id: int, context: Dict):
        """
        Обновление контекста сообщений.
        
        Args:
            user_id: ID пользователя
            context: Новый контекст
        """
        state = self.get_user_state(user_id)
        state.message_context.update(context)

    def get_message_context(self, user_id: int) -> Dict:
        """
        Получение контекста сообщений.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Dict: Контекст сообщений
        """
        state = self.get_user_state(user_id)
        return state.message_context

    def update_state(self, user_id: int, **kwargs):
        """Обновляет состояние пользователя"""
        state = self.get_user_state(user_id)
        for key, value in kwargs.items():
            if hasattr(state, key):
                setattr(state, key, value)
            else:
                state.temp_data[key] = value
                
    def get_preferred_board(self, user_id: int, chat_id: int) -> Optional[str]:
        """Получает предпочитаемую доску для чата"""
        if user_id in self._board_preferences and chat_id in self._board_preferences[user_id]:
            pref = self._board_preferences[user_id][chat_id]
            # Проверяем, не устарели ли предпочтения
            if datetime.now() - pref['last_used'] < timedelta(days=7):
                return pref['board_id']
        return None
    
    def cleanup_expired_states(self, timeout_minutes: int = 30):
        """Очищает устаревшие состояния"""
        expired_users = [
            user_id for user_id, state in self._states.items()
            if state.is_expired(timeout_minutes)
        ]
        for user_id in expired_users:
            del self._states[user_id]
            logger.info(f"Cleaned up expired state for user {user_id}")

# Создаем глобальный экземпляр для использования во всем приложении
state_manager = StateManager()