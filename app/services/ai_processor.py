from typing import List, Dict, Any, Optional
import openai
from app.core.config import settings
from app.utils.logger import app_logger

class AIProcessor:
    """Сервис для обработки сообщений через AI."""
    
    def __init__(self):
        openai.api_key = settings.OPENAI_API_KEY
        self.system_prompt = """
        Ты - ассистент для анализа сообщений и создания задач в Trello.
        Твоя задача - анализировать сообщения и извлекать из них информацию для создания задач.
        
        Для каждой задачи нужно определить:
        1. Название и описание
        2. Сроки выполнения
        3. Участников
        4. Метки/категории
        5. Приоритет
        6. Рекомендуемую доску и список на основе контекста
        
        Используй контекст проекта для более точных рекомендаций.
        """

    async def analyze_messages(
        self, 
        messages: List[Dict], 
        context: Dict
    ) -> Optional[Dict]:
        """
        Анализ сообщений для создания задач.
        
        Args:
            messages: Список сообщений для анализа
            context: Контекст проекта (доски, списки, предпочтения)
            
        Returns:
            Optional[Dict]: Результаты анализа или None в случае ошибки
        """
        try:
            # Подготовка контекста для AI
            boards_info = self._format_boards_info(context.get('boards', []))
            preferences = context.get('preferences', {})
            
            # Формируем промпт для AI
            messages_text = self._format_messages(messages)
            prompt = f"""
            Контекст проекта:
            {boards_info}
            
            Предпочтения пользователя:
            {self._format_preferences(preferences)}
            
            Сообщения для анализа:
            {messages_text}
            
            Проанализируй сообщения и создай структурированные задачи.
            """
            
            # Отправляем запрос к AI
            response = await openai.ChatCompletion.acreate(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            # Обрабатываем ответ AI
            if response.choices:
                try:
                    analysis = self._parse_ai_response(response.choices[0].message.content)
                    return {
                        "tasks": analysis.get("tasks", []),
                        "context_analysis": analysis.get("context_analysis", {}),
                        "recommendations": analysis.get("recommendations", [])
                    }
                except Exception as e:
                    app_logger.error(f"Ошибка при обработке ответа AI: {str(e)}")
                    return None
                    
            return None
            
        except Exception as e:
            app_logger.error(f"Ошибка при анализе сообщений: {str(e)}")
            return None

    async def process_direct_task_creation(self, text: str) -> Optional[Dict]:
        """
        Обработка прямого создания задачи.
        
        Args:
            text: Текст с описанием задачи
            
        Returns:
            Optional[Dict]: Структурированная задача или None в случае ошибки
        """
        try:
            prompt = f"""
            Создай структурированную задачу из следующего описания:
            {text}
            
            Определи:
            1. Название задачи
            2. Подробное описание
            3. Сроки (если указаны)
            4. Участников (если указаны)
            5. Приоритет
            6. Метки/категории
            """
            
            response = await openai.ChatCompletion.acreate(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            if response.choices:
                return self._parse_ai_response(response.choices[0].message.content)
            return None
            
        except Exception as e:
            app_logger.error(f"Ошибка при создании задачи: {str(e)}")
            return None

    def _format_boards_info(self, boards: List[Dict]) -> str:
        """Форматирование информации о досках для AI."""
        info = "Доступные доски Trello:\n"
        for board in boards:
            info += f"\nДоска: {board['name']}\n"
            if board.get('desc'):
                info += f"Описание: {board['desc']}\n"
            
            lists = board.get('lists', [])
            if lists:
                info += "Списки:\n"
                for lst in lists:
                    info += f"- {lst['name']}\n"
                    
            labels = board.get('labels', [])
            if labels:
                info += "Метки:\n"
                for label in labels:
                    info += f"- {label['name']} ({label['color']})\n"
        
        return info

    def _format_preferences(self, preferences: Dict) -> str:
        """Форматирование предпочтений пользователя для AI."""
        info = "Предпочтения пользователя:\n"
        
        if preferences.get('default_board'):
            info += f"Основная доска: {preferences['default_board']}\n"
            
        if preferences.get('label_preferences'):
            info += "Предпочитаемые метки:\n"
            for label in preferences['label_preferences']:
                info += f"- {label}\n"
                
        if preferences.get('due_date_preferences'):
            info += f"Предпочтения по срокам: {preferences['due_date_preferences']}\n"
            
        return info

    def _format_messages(self, messages: List[Dict]) -> str:
        """Форматирование сообщений для AI."""
        formatted = ""
        for msg in messages:
            formatted += f"\nСообщение от {msg.get('from_user', 'Unknown')}:\n"
            formatted += f"Текст: {msg.get('text', '')}\n"
            if msg.get('chat_title'):
                formatted += f"Из чата: {msg['chat_title']}\n"
            if msg.get('date'):
                formatted += f"Дата: {msg['date']}\n"
        return formatted

    def _parse_ai_response(self, response: str) -> Dict:
        """
        Парсинг ответа AI в структурированный формат.
        
        В случае ошибки парсинга, возвращает базовую структуру с пустыми списками.
        """
        try:
            # Здесь должна быть логика парсинга ответа AI
            # В реальном приложении нужно реализовать более надежный парсинг
            
            # Пример структуры ответа:
            return {
                "tasks": [
                    {
                        "name": "Название задачи",
                        "description": "Описание задачи",
                        "due_date": "2024-01-01",
                        "members": ["@user1", "@user2"],
                        "priority": "high",
                        "labels": ["bug", "urgent"],
                        "recommended_board": {
                            "name": "Development",
                            "list": "To Do",
                            "confidence": 0.8,
                            "reasoning": "Задача связана с разработкой"
                        }
                    }
                ],
                "context_analysis": {
                    "project_type": "development",
                    "urgency_level": "high",
                    "project_hints": [
                        {
                            "board_name": "Development",
                            "reason": "Задача связана с разработкой"
                        }
                    ]
                },
                "recommendations": [
                    "Рекомендуется добавить чек-лист",
                    "Желательно указать конкретные сроки"
                ]
            }
            
        except Exception as e:
            app_logger.error(f"Ошибка при парсинге ответа AI: {str(e)}")
            return {
                "tasks": [],
                "context_analysis": {},
                "recommendations": []
            } 