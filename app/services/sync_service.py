# app/services/sync_service.py
import redis
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from app.db.models import Board, List, Card
from app.config import get_settings

settings = get_settings()
redis_client = redis.from_url(settings.REDIS_URL)

class TrelloSyncService:
    def __init__(self, db_session: AsyncSession, trello_client):
        self.db = db_session
        self.trello = trello_client
        
    async def sync_all(self):
        """Полная синхронизация данных с Trello"""
        boards = await self.trello.get_boards_with_details()
        for board in boards:
            await self.sync_board(board)
            
    async def sync_board(self, board_data):
        """Синхронизация доски"""
        board = await self._update_board(board_data)
        lists = await self.trello.get_board_lists(board.trello_id)
        
        for list_data in lists:
            list_obj = await self._update_list(list_data, board.id)
            cards = await self.trello.get_list_cards(list_data['id'])
            
            for card_data in cards:
                await self._update_card(card_data, list_obj.id)
                
    async def _update_board(self, data):
        """Обновление/создание доски в БД"""
        query = select(Board).where(Board.trello_id == data['id'])
        result = await self.db.execute(query)
        board = result.scalar_one_or_none()
        
        if not board:
            board = Board(
                trello_id=data['id'],
                name=data['name'],
                description=data.get('desc', ''),
                metadata=data
            )
            self.db.add(board)
        else:
            board.name = data['name']
            board.description = data.get('desc', '')
            board.metadata = data
            board.last_synced = datetime.utcnow()
            
        await self.db.commit()
        return board
        
    async def _update_list(self, data, board_id):
        """Обновление/создание списка"""
        query = select(List).where(List.trello_id == data['id'])
        result = await self.db.execute(query)
        list_obj = result.scalar_one_or_none()
        
        if not list_obj:
            list_obj = List(
                trello_id=data['id'],
                board_id=board_id,
                name=data['name'],
                position=data.get('pos', 0),
                metadata=data
            )
            self.db.add(list_obj)
        else:
            list_obj.name = data['name']
            list_obj.position = data.get('pos', 0)
            list_obj.metadata = data
            list_obj.last_synced = datetime.utcnow()
            
        await self.db.commit()
        return list_obj
        
    async def _update_card(self, data, list_id):
        """Обновление/создание карточки"""
        query = select(Card).where(Card.trello_id == data['id'])
        result = await self.db.execute(query)
        card = result.scalar_one_or_none()
        
        if not card:
            card = Card(
                trello_id=data['id'],
                list_id=list_id,
                name=data['name'],
                description=data.get('desc', ''),
                due_date=data.get('due'),
                labels=data.get('labels', []),
                members=data.get('idMembers', []),
                position=data.get('pos', 0),
                metadata=data
            )
            self.db.add(card)
        else:
            card.name = data['name']
            card.description = data.get('desc', '')
            card.due_date = data.get('due')
            card.labels = data.get('labels', [])
            card.members = data.get('idMembers', [])
            card.position = data.get('pos', 0)
            card.metadata = data
            card.last_synced = datetime.utcnow()
            
        await self.db.commit()
        return card
        
    def cache_board_data(self, board_id: str, data: dict):
        """Кэширование данных доски в Redis"""
        key = f"board:{board_id}"
        redis_client.setex(key, timedelta(hours=1), json.dumps(data))
        
    def get_cached_board(self, board_id: str) -> dict:
        """Получение кэшированных данных доски"""
        key = f"board:{board_id}"
        data = redis_client.get(key)
        return json.loads(data) if data else None