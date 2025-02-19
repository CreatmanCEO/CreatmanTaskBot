from typing import Dict, Optional
import json
import os
from pathlib import Path

class Localization:
    def __init__(self):
        self.languages = {'en': 'English', 'ru': 'Русский'}
        self.current_language = 'ru'
        self.translations: Dict[str, Dict[str, str]] = {}
        self._load_translations()

    def _load_translations(self):
        """Загрузка переводов из JSON файлов."""
        locales_dir = Path(__file__).parent.parent / 'locales'
        for lang in self.languages.keys():
            file_path = locales_dir / f'{lang}.json'
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.translations[lang] = json.load(f)

    def set_language(self, language_code: str) -> bool:
        """
        Установка языка интерфейса.
        
        Args:
            language_code: Код языка ('en' или 'ru')
            
        Returns:
            bool: True если язык успешно установлен, False в противном случае
        """
        if language_code in self.languages:
            self.current_language = language_code
            return True
        return False

    def get_text(self, key: str, **kwargs) -> str:
        """
        Получение локализованного текста по ключу.
        
        Args:
            key: Ключ для поиска текста
            **kwargs: Параметры для форматирования строки
            
        Returns:
            str: Локализованный текст
        """
        try:
            text = self.translations[self.current_language].get(
                key,
                self.translations['en'].get(key, key)
            )
            return text.format(**kwargs) if kwargs else text
        except Exception:
            return key

    def get_available_languages(self) -> Dict[str, str]:
        """
        Получение списка доступных языков.
        
        Returns:
            Dict[str, str]: Словарь с кодами и названиями языков
        """
        return self.languages

# Создаем глобальный экземпляр для использования во всем приложении
localization = Localization() 