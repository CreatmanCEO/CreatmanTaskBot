# app/ai/processor.py
import logging
import json
from typing import Optional, Dict, Any, List
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import Board, List, Card
from app.config import get_settings
import redis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()
redis_client = redis.from_url(settings.REDIS_URL)

SYSTEM_PROMPT = """
Ты - AI-ассистент в системе управления задачами Trello через Telegram бота. 
Твоя роль - анализировать сообщения и помогать в создании и управлении задачами.

КОНТЕКСТ СИСТЕМЫ:
- Пользователи могут пересылать сообщения из чатов или создавать задачи напрямую
- У пользователя есть доски Trello с разными списками задач
- Каждая задача может иметь: название, описание, метки, сроки, участников
- Система поддерживает чек-листы и вложения

ОПРЕДЕЛЕНИЕ ПРОЕКТА:
1. Анализируй контекст сообщений:
   - Название чата, откуда пересланы сообщения
   - Упоминания проектов, над которыми работает команда
   - Имена участников и их роли
   - Используемые метки и терминологию

2. Сопоставляй с существующими досками:
   - Названия досок и их тематика
   - Текущие задачи на досках
   - Участники досок
   - Используемые метки

3. Если не можешь точно определить проект:
   - Укажи низкий уровень уверенности (confidence)
   - Предложи несколько вариантов досок
   - Объясни причины своих предположений

ФОРМАТ ОТВЕТА:
{
    "tasks": [
        {
            "name": "Название задачи",
            "description": "Описание задачи",
            "due_date": "YYYY-MM-DD",
            "members": ["@username1", "@username2"],
            "labels": ["#label1", "#label2"],
            "priority": "high/medium/low",
            "recommended_board": {
                "id": "board_id",
                "confidence": 0.0-1.0,
                "reasoning": "Причины выбора доски"
            },
            "recommended_list": "name_of_list",
            "source_messages": [1, 2]  // Индексы сообщений, из которых извлечена задача
        }
    ],
    "context_analysis": {
        "chat_type": "project/general/unknown",
        "project_mentions": ["Project A", "Project B"],
        "key_participants": ["@user1", "@user2"],
        "confidence": 0.0-1.0
    },
    "suggestions": {
        "create_checklists": bool,
        "needs_attachments": bool,
        "additional_actions": []
    }
}

ПРИМЕРЫ АНАЛИЗА:

1. Один пересланный диалог:
Менеджер: "@developer нужно исправить баг с авторизацией до завтра"
Разработчик: "Понял, сделаю"

Ответ:
{
    "tasks": [{
        "name": "Исправить баг авторизации",
        "description": "Обнаружена проблема в системе авторизации, требуется срочное исправление",
        "due_date": "2024-03-23",
        "members": ["@developer"],
        "labels": ["#bug", "#auth", "#urgent"],
        "priority": "high",
        "recommended_board": {
            "id": "main_project",
            "confidence": 0.9,
            "reasoning": "Задача связана с основным функционалом, упоминается авторизация"
        },
        "recommended_list": "Баги",
        "source_messages": [0, 1]
    }],
    "context_analysis": {
        "chat_type": "project",
        "project_mentions": ["авторизация"],
        "key_participants": ["@developer"],
        "confidence": 0.9
    }
}

2. Несколько несвязанных сообщений:
"Нужно обновить дизайн главной страницы"
"@tester проверь производительность API"
"Давайте обсудим новые фичи на следующей неделе"

Ответ:
{
    "tasks": [
        {
            "name": "Обновление дизайна главной страницы",
            "description": "Требуется обновление дизайна главной страницы",
            "labels": ["#design", "#frontend"],
            "priority": "medium",
            "recommended_board": {
                "id": "frontend_board",
                "confidence": 0.8,
                "reasoning": "Задача связана с дизайном и фронтендом"
            },
            "source_messages": [0]
        },
        {
            "name": "Тестирование производительности API",
            "members": ["@tester"],
            "labels": ["#testing", "#api"],
            "priority": "medium",
            "recommended_board": {
                "id": "backend_board",
                "confidence": 0.8,
                "reasoning": "Задача связана с API и тестированием"
            },
            "source_messages": [1]
        }
    ],
    "context_analysis": {
        "chat_type": "general",
        "key_participants": ["@tester"],
        "confidence": 0.7
    }
}

КОНТЕКСТ ПРОЕКТА:
{context}
"""

class AIProcessor:
    def __init__(self, db_session: AsyncSession):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4-turbo-preview"
        self.db = db_session
        
    async def analyze_messages(self, 
                             messages: List[Dict], 
                             context: Dict[str, Any]) -> Optional[Dict]:
        try:
            # Получаем данные из БД для контекста
            boards_data = await self._get_boards_context()
            messages_text = self._prepare_messages_text(messages)
            
            # Обогащаем контекст данными из БД
            enriched_context = {
                **context,
                'boards_data': boards_data
            }
            
            modified_prompt = SYSTEM_PROMPT.format(context=json.dumps(enriched_context))
            
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": modified_prompt},
                    {"role": "user", "content": f"Сообщения для анализа:\n{messages_text}"}
                ],
                response_format={"type": "json_object"}
            )
            
            response = json.loads(completion.choices[0].message.content)
            logger.info(f"AI Analysis completed successfully")
            
            # Кэшируем результат анализа
            self._cache_analysis_result(messages, response)
            
            return response
            
        except Exception as e:
            logger.error(f"Error in AI analysis: {str(e)}", exc_info=True)
            return None
            
    async def _get_boards_context(self) -> Dict:
        """Получение контекста из БД"""
        try:
            # Получаем все доски
            query = select(Board)
            result = await self.db.execute(query)
            boards = result.scalars().all()
            
            context_data = {}
            for board in boards:
                # Получаем списки для доски
                lists_query = select(List).where(List.board_id == board.id)
                lists_result = await self.db.execute(lists_query)
                lists = lists_result.scalars().all()
                
                board_data = {
                    'id': board.trello_id,
                    'name': board.name,
                    'description': board.description,
                    'lists': []
                }
                
                for list_obj in lists:
                    # Получаем карточки для списка
                    cards_query = select(Card).where(Card.list_id == list_obj.id)
                    cards_result = await self.db.execute(cards_query)
                    cards = cards_result.scalars().all()
                    
                    list_data = {
                        'id': list_obj.trello_id,
                        'name': list_obj.name,
                        'cards': [{
                            'id': card.trello_id,
                            'name': card.name,
                            'description': card.description,
                            'labels': card.labels,
                            'members': card.members
                        } for card in cards]
                    }
                    board_data['lists'].append(list_data)
                
                context_data[board.trello_id] = board_data
                
            return context_data
            
        except Exception as e:
            logger.error(f"Error getting boards context: {str(e)}", exc_info=True)
            return {}
            
    def _prepare_messages_text(self, messages: List[Dict]) -> str:
        """Подготовка текста сообщений для анализа"""
        return "\n---\n".join(
            f"[{msg.get('from_user', 'Unknown')}]: {msg.get('text', '')}"
            for msg in messages
        )
            
    def _cache_analysis_result(self, messages: List[Dict], result: Dict):
        """Кэширование результата анализа"""
        try:
            # Создаем ключ на основе хэша сообщений
            messages_hash = hash(json.dumps(messages, sort_keys=True))
            cache_key = f"analysis:{messages_hash}"
            
            # Сохраняем в Redis на 1 час
            redis_client.setex(
                cache_key,
                3600,  # 1 час
                json.dumps(result)
            )
        except Exception as e:
            logger.error(f"Error caching analysis result: {str(e)}")
            
    def _get_cached_analysis(self, messages: List[Dict]) -> Optional[Dict]:
        """Получение кэшированного результата анализа"""
        try:
            messages_hash = hash(json.dumps(messages, sort_keys=True))
            cache_key = f"analysis:{messages_hash}"
            
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
            return None
        except Exception as e:
            logger.error(f"Error getting cached analysis: {str(e)}")
            return None
            
    async def enhance_task_details(self, task_data: Dict) -> Dict:
        """Обогащение деталей задачи на основе контекста из БД"""
        try:
            # Находим связанные задачи
            if task_data.get('name'):
                query = select(Card).where(
                    Card.name.ilike(f"%{task_data['name']}%")
                )
                result = await self.db.execute(query)
                related_cards = result.scalars().all()
                
                related_data = [{
                    'id': card.trello_id,
                    'name': card.name,
                    'list_name': card.list.name,
                    'board_name': card.list.board.name
                } for card in related_cards]
                
                task_data['related_tasks'] = related_data
            
            return task_data
            
        except Exception as e:
            logger.error(f"Error enhancing task details: {str(e)}", exc_info=True)
            return task_data
            
    async def process_direct_task_creation(self, user_input: str) -> Optional[Dict]:
        """Обработка прямого создания задачи"""
        try:
            # Проверяем кэш
            cached = self._get_cached_analysis([{'text': user_input}])
            if cached:
                return cached
                
            # Получаем контекст из БД
            boards_context = await self._get_boards_context()
            
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Extract task details and find most relevant board/list based on context"},
                    {"role": "user", "content": f"Context: {json.dumps(boards_context)}\nTask: {user_input}"}
                ],
                response_format={"type": "json_object"}
            )
            
            response = json.loads(completion.choices[0].message.content)
            
            # Обогащаем детали задачи
            if response.get('tasks'):
                response['tasks'] = [
                    await self.enhance_task_details(task)
                    for task in response['tasks']
                ]
            
            # Кэшируем результат
            self._cache_analysis_result([{'text': user_input}], response)
            
            return response
            
        except Exception as e:
            logger.error(f"Error in direct task creation: {str(e)}", exc_info=True)
            return None