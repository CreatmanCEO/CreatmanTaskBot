# app/db/models.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Board(Base):
    __tablename__ = 'boards'
    
    id = Column(String, primary_key=True)
    trello_id = Column(String, unique=True)
    name = Column(String)
    description = Column(String)
    last_synced = Column(DateTime, default=datetime.utcnow)
    metadata = Column(JSON)
    
    lists = relationship("List", back_populates="board")

class List(Base):
    __tablename__ = 'lists'
    
    id = Column(String, primary_key=True)
    trello_id = Column(String, unique=True)
    board_id = Column(String, ForeignKey('boards.id'))
    name = Column(String)
    position = Column(Integer)
    last_synced = Column(DateTime, default=datetime.utcnow)
    metadata = Column(JSON)
    
    board = relationship("Board", back_populates="lists")
    cards = relationship("Card", back_populates="list")

class Card(Base):
    __tablename__ = 'cards'
    
    id = Column(String, primary_key=True)
    trello_id = Column(String, unique=True)
    list_id = Column(String, ForeignKey('lists.id'))
    name = Column(String)
    description = Column(String)
    due_date = Column(DateTime)
    labels = Column(JSON)
    members = Column(JSON)
    position = Column(Integer)
    last_synced = Column(DateTime, default=datetime.utcnow)
    metadata = Column(JSON)
    
    list = relationship("List", back_populates="cards")