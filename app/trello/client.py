import aiohttp
import logging
from typing import List, Dict, Any, Optional
from app.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

class TrelloClient:
    BASE_URL = "https://api.trello.com/1"
    
    def __init__(self):
        self.key = settings.TRELLO_API_KEY
        self.token = settings.TRELLO_TOKEN
        logger.info(f"TrelloClient initialized with key: {self.key[:10]}...")
        
    async def _make_request(self, method: str, endpoint: str, params: dict = None, data: dict = None):
        if params is None:
            params = {}
        
        params.update({
            'key': self.key,
            'token': self.token
        })
        
        url = f"{self.BASE_URL}/{endpoint}"
        logger.info(f"Making request to Trello: {method} {url}")
        logger.info(f"Params: {params}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(method, url, params=params, json=data) as response:
                    response_text = await response.text()
                    logger.info(f"Response status: {response.status}")
                    logger.info(f"Response text: {response_text[:200]}...")
                    
                    if response.status != 200:
                        logger.error(f"Trello API error. Status: {response.status}, Response: {response_text}")
                        return {"error": f"API Error: {response.status}"}
                    
                    return await response.json()
        except Exception as e:
            logger.error(f"Error making request to Trello: {str(e)}")
            raise

    async def get_boards_with_details(self) -> List[Dict[str, Any]]:
        """Получить расширенную информацию о досках"""
        try:
            # Получаем базовую информацию о досках
            boards = await self._make_request('GET', 'members/me/boards', params={
                'fields': 'all',
                'lists': 'open',
                'labels': 'all',
                'members': 'all'
            })
            
            # Для каждой доски получаем дополнительную информацию
            detailed_boards = []
            for board in boards:
                board_id = board['id']
                
                # Получаем списки
                lists = await self._make_request('GET', f'boards/{board_id}/lists', params={
                    'fields': 'all'
                })
                
                # Получаем метки
                labels = await self._make_request('GET', f'boards/{board_id}/labels')
                
                # Получаем последние активные карточки
                cards = await self._make_request('GET', f'boards/{board_id}/cards', params={
                    'fields': 'name,desc,dateLastActivity,labels,members',
                    'limit': 10
                })
                
                detailed_boards.append({
                    **board,
                    'lists': lists,
                    'labels': labels,
                    'recent_cards': cards
                })
            
            return detailed_boards
        except Exception as e:
            logger.error(f"Error getting boards with details: {e}")
            raise

    async def create_task_from_analysis(self, task_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Создает задачу на основе анализа ИИ"""
        try:
            # Создаем карточку
            card_data = {
                'name': task_data['name'],
                'desc': task_data.get('description', ''),
                'idList': task_data['list_id'],
                'pos': 'top'
            }
            
            if task_data.get('due_date'):
                card_data['due'] = task_data['due_date']
            
            card = await self._make_request('POST', 'cards', data=card_data)
            
            if 'error' in card:
                return None
                
            card_id = card['id']
            
            # Добавляем метки
            if task_data.get('labels'):
                for label_name in task_data['labels']:
                    label = await self._find_or_create_label(
                        task_data['board_id'],
                        label_name
                    )
                    if label:
                        await self._make_request('POST', f'cards/{card_id}/idLabels',
                                               data={'value': label['id']})
            
            # Добавляем участников
            if task_data.get('members'):
                for member in task_data['members']:
                    member_data = await self._find_board_member(
                        task_data['board_id'],
                        member
                    )
                    if member_data:
                        await self._make_request('POST', f'cards/{card_id}/idMembers',
                                               data={'value': member_data['id']})
            
            # Создаем чек-лист если есть
            if task_data.get('checklist_items'):
                checklist = await self._make_request('POST', 'checklists',
                                                   data={'idCard': card_id,
                                                        'name': 'ToDo'})
                
                for item in task_data['checklist_items']:
                    await self._make_request('POST', f'checklists/{checklist["id"]}/checkItems',
                                           data={'name': item})
            
            # Получаем обновленную карточку
            return await self._make_request('GET', f'cards/{card_id}')
            
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            return None

    async def _find_or_create_label(self, board_id: str, label_name: str) -> Optional[Dict]:
        """Находит или создает метку на доске"""
        try:
            # Получаем существующие метки
            labels = await self._make_request('GET', f'boards/{board_id}/labels')
            
            # Ищем подходящую метку
            for label in labels:
                if label['name'].lower() == label_name.lower():
                    return label
            
            # Создаем новую метку
            return await self._make_request('POST', 'labels', data={
                'name': label_name,
                'idBoard': board_id,
                'color': 'blue'  # Можно добавить логику выбора цвета
            })
        except Exception as e:
            logger.error(f"Error with label: {e}")
            return None

    async def _find_board_member(self, board_id: str, username: str) -> Optional[Dict]:
        """Находит участника доски по имени пользователя"""
        try:
            members = await self._make_request('GET', f'boards/{board_id}/members')
            return next(
                (m for m in members if m.get('username', '').lower() == username.lower()),
                None
            )
        except Exception as e:
            logger.error(f"Error finding member: {e}")
            return None

    async def get_board(self, board_id: str):
        """Получить информацию о конкретной доске"""
        return await self._make_request('GET', f'boards/{board_id}')

    async def get_board_lists(self, board_id: str):
        """Получить списки на доске"""
        return await self._make_request('GET', f'boards/{board_id}/lists')
        
    async def get_list(self, list_id: str):
        """Получить информацию о списке"""
        return await self._make_request('GET', f'lists/{list_id}')

    async def get_list_cards(self, list_id: str):
        """Получить карточки списка"""
        return await self._make_request('GET', f'lists/{list_id}/cards')
        
    async def get_card_members(self, card_id: str):
        """Получить участников карточки"""
        return await self._make_request('GET', f'cards/{card_id}/members')    
        
    async def get_card_checklists(self, card_id: str):
        """Получить чек-листы карточки"""
        return await self._make_request('GET', f'cards/{card_id}/checklists')    

    async def create_card(self, list_id: str, name: str, desc: str = "", due: str = None):
        """Создать карточку в списке"""
        data = {
            'name': name,
            'desc': desc,
            'idList': list_id
        }
        if due:
            data['due'] = due
        return await self._make_request('POST', 'cards', data=data)

    async def update_card(self, card_id: str, data: dict):
        """Обновить карточку"""
        return await self._make_request('PUT', f'cards/{card_id}', data=data)

    async def get_card(self, card_id: str):
        """Получить информацию о карточке"""
        return await self._make_request('GET', f'cards/{card_id}')

    async def get_member(self):
        """Получить информацию о текущем пользователе"""
        return await self._make_request('GET', 'members/me')

    async def get_board_members(self, board_id: str):
        """Получить список участников доски"""
        return await self._make_request('GET', f'boards/{board_id}/members')