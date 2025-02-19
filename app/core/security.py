from cryptography.fernet import Fernet
from app.core.config import settings
import base64
from typing import Optional

class TokenEncryption:
    """Класс для шифрования и дешифрования токенов."""
    
    def __init__(self):
        # Генерируем ключ шифрования на основе SECRET_KEY
        key = base64.urlsafe_b64encode(settings.SECRET_KEY[:32].encode().ljust(32)[:32])
        self.cipher_suite = Fernet(key)

    def encrypt_token(self, token: str) -> str:
        """
        Шифрование токена.
        
        Args:
            token: Токен для шифрования
            
        Returns:
            str: Зашифрованный токен
        """
        try:
            encrypted_token = self.cipher_suite.encrypt(token.encode())
            return encrypted_token.decode()
        except Exception as e:
            raise ValueError(f"Ошибка при шифровании токена: {str(e)}")

    def decrypt_token(self, encrypted_token: str) -> Optional[str]:
        """
        Дешифрование токена.
        
        Args:
            encrypted_token: Зашифрованный токен
            
        Returns:
            Optional[str]: Расшифрованный токен или None в случае ошибки
        """
        try:
            decrypted_token = self.cipher_suite.decrypt(encrypted_token.encode())
            return decrypted_token.decode()
        except Exception:
            return None

# Создаем глобальный экземпляр для использования во всем приложении
token_encryption = TokenEncryption() 