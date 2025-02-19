# app/db/crud.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import joinedload
from typing import List, Optional
from datetime import datetime
from .models import Board, List, Card

class BoardCRUD:
    def __init__(self, session: AsyncSession):
        self.session = session
        
    async def create(self, **kwargs) -> Board:
        board = Board(**kwargs)
        self.session.add(board)
        await self.session.commit()
        return board
        
    async def get(self, board_id: str) -> Optional[Board]:
        query = select(Board).where(Board.id == board_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
        
    async def get_by_trello_id(self, trello_id: str) -> Optional[Board]:
        query = select(Board).where(Board.trello_id == trello_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
        
    async def get_all(self) -> List[Board]:
        query = select(Board)
        result = await self.session.execute(query)
        return result.scalars().all()
        
    async def update(self, board_id: str, **kwargs) -> Optional[Board]:
        query = update(Board).where(Board.id == board_id).values(**kwargs)
        await self.session.execute(query)
        await self.session.commit()
        return await self.get(board_id)
        
    async def delete(self, board_id: str):
        query = delete(Board).where(Board.id == board_id)
        await self.session.execute(query)
        await self.session.commit()

class ListCRUD:
    def __init__(self, session: AsyncSession):
        self.session = session
        
    async def create(self, **kwargs) -> List:
        list_obj = List(**kwargs)
        self.session.add(list_obj)
        await self.session.commit()
        return list_obj
        
    async def get(self, list_id: str) -> Optional[List]:
        query = select(List).where(List.id == list_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
        
    async def get_by_trello_id(self, trello_id: str) -> Optional[List]:
        query = select(List).where(List.trello_id == trello_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
        
    async def get_board_lists(self, board_id: str) -> List[List]:
        query = select(List).where(List.board_id == board_id)
        result = await self.session.execute(query)
        return result.scalars().all()
        
    async def update(self, list_id: str, **kwargs) -> Optional[List]:
        query = update(List).where(List.id == list_id).values(**kwargs)
        await self.session.execute(query)
        await self.session.commit()
        return await self.get(list_id)
        
    async def delete(self, list_id: str):
        query = delete(List).where(List.id == list_id)
        await self.session.execute(query)
        await self.session.commit()

class CardCRUD:
    def __init__(self, session: AsyncSession):
        self.session = session
        
    async def create(self, **kwargs) -> Card:
        card = Card(**kwargs)
        self.session.add(card)
        await self.session.commit()
        return card
        
    async def get(self, card_id: str) -> Optional[Card]:
        query = select(Card).where(Card.id == card_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
        
    async def get_by_trello_id(self, trello_id: str) -> Optional[Card]:
        query = select(Card).where(Card.trello_id == trello_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
        
    async def get_list_cards(self, list_id: str) -> List[Card]:
        query = select(Card).where(Card.list_id == list_id)
        result = await self.session.execute(query)
        return result.scalars().all()
        
    async def update(self, card_id: str, **kwargs) -> Optional[Card]:
        query = update(Card).where(Card.id == card_id).values(**kwargs)
        await self.session.execute(query)
        await self.session.commit()
        return await self.get(card_id)
        
    async def delete(self, card_id: str):
        query = delete(Card).where(Card.id == card_id)
        await self.session.execute(query)
        await self.session.commit()
        
    async def search_similar(self, name: str) -> List[Card]:
        """Поиск похожих карточек по названию"""
        query = select(Card).where(Card.name.ilike(f"%{name}%"))
        result = await self.session.execute(query)
        return result.scalars().all()