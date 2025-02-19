from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import validates
from app.db.base import Base
from app.core.security import token_encryption
import re

class User(Base):
    """Модель пользователя в базе данных."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    _trello_token = Column("trello_token", String)  # Зашифрованный токен
    language = Column(String, default="ru")
    is_authorized = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    @property
    def trello_token(self) -> str:
        """Получение расшифрованного токена Trello."""
        if self._trello_token:
            return token_encryption.decrypt_token(self._trello_token)
        return None

    @trello_token.setter
    def trello_token(self, token: str):
        """Шифрование и сохранение токена Trello."""
        if token:
            self._trello_token = token_encryption.encrypt_token(token)
        else:
            self._trello_token = None

    @validates('email')
    def validate_email(self, key, email):
        """Валидация email."""
        if not email:
            raise ValueError("Email не может быть пустым")
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            raise ValueError("Неверный формат email")
            
        return email.lower()

    @validates('language')
    def validate_language(self, key, language):
        """Валидация языка."""
        if language not in ['ru', 'en']:
            raise ValueError("Поддерживаются только языки: ru, en")
        return language

    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, email={self.email})>" 