import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import re

logger = logging.getLogger(__name__)

class ContextAnalyzer:
    def __init__(self):
        self.keywords = {
            'project': ['проект', 'задача', 'фича', 'баг', 'ошибка'],
            'deadline': ['срок', 'дедлайн', 'до', 'к'],
            'priority': ['срочно', 'важно', 'критично', 'блокер']
        }
        
    def extract_context(self, messages: List[Dict], current_context: Dict = None) -> Dict[str, Any]:
        """Извлекает контекст из сообщений"""
        context = {
            'keywords': self.extract_keywords(messages),
            'mentions': self.extract_mentions(messages),
            'dates': self.extract_dates(messages),
            'project_hints': self.extract_project_hints(messages),
            'priority': self.determine_priority(messages)
        }
        
        if current_context:
            context = self.merge_contexts(context, current_context)
            
        return context
    
    def extract_keywords(self, messages: List[Dict]) -> Dict[str, List[str]]:
        """Извлекает ключевые слова из сообщений"""
        found_keywords = {category: [] for category in self.keywords}
        
        for message in messages:
            text = message.get('text', '').lower()
            for category, keywords in self.keywords.items():
                for keyword in keywords:
                    if keyword in text:
                        found_keywords[category].append(keyword)
        
        return found_keywords
    
    def extract_mentions(self, messages: List[Dict]) -> List[str]:
        """Извлекает упоминания пользователей"""
        mentions = []
        for message in messages:
            text = message.get('text', '')
            # Ищем @username
            mentions.extend(re.findall(r'@(\w+)', text))
        return list(set(mentions))
    
    def extract_dates(self, messages: List[Dict]) -> List[Dict]:
        """Извлекает даты из сообщений"""
        dates = []
        date_patterns = [
            (r'до (\d{1,2})[./](\d{1,2})[./]?(\d{2,4})?', 'deadline'),
            (r'к (\d{1,2})[./](\d{1,2})', 'deadline'),
            (r'(\d{1,2})[./](\d{1,2})[./]?(\d{2,4})?', 'date')
        ]
        
        for message in messages:
            text = message.get('text', '')
            for pattern, date_type in date_patterns:
                matches = re.finditer(pattern, text)
                for match in matches:
                    try:
                        date_info = self.parse_date_match(match)
                        if date_info:
                            dates.append({
                                'date': date_info,
                                'type': date_type,
                                'message_id': message.get('message_id')
                            })
                    except:
                        continue
        
        return dates
    
    def parse_date_match(self, match) -> Optional[datetime]:
        """Парсит найденное совпадение с датой"""
        groups = match.groups()
        today = datetime.now()
        
        try:
            day = int(groups[0])
            month = int(groups[1])
            year = int(groups[2]) if len(groups) > 2 and groups[2] else today.year
            
            if year < 100:
                year += 2000
                
            return datetime(year, month, day)
        except:
            return None
    
    def extract_project_hints(self, messages: List[Dict]) -> Dict[str, Any]:
        """Извлекает подсказки о проекте"""
        hints = {
            'keywords': [],
            'confidence': 0.0
        }
        
        project_keywords = ['проект', 'задача', 'фича', 'компонент', 'модуль']
        
        for message in messages:
            text = message.get('text', '').lower()
            for keyword in project_keywords:
                if keyword in text:
                    hints['keywords'].append(keyword)
                    hints['confidence'] += 0.2
        
        hints['confidence'] = min(hints['confidence'], 1.0)
        return hints
    
    def determine_priority(self, messages: List[Dict]) -> Dict[str, Any]:
        """Определяет приоритет на основе сообщений"""
        priority_words = {
            'high': ['срочно', 'критично', 'блокер', 'asap'],
            'medium': ['важно', 'нужно', 'надо'],
            'low': ['когда будет время', 'некритично', 'опционально']
        }
        
        found_priorities = {priority: 0 for priority in priority_words.keys()}
        
        for message in messages:
            text = message.get('text', '').lower()
            for priority, words in priority_words.items():
                for word in words:
                    if word in text:
                        found_priorities[priority] += 1
        
        max_priority = max(found_priorities.items(), key=lambda x: x[1])
        return {
            'level': max_priority[0],
            'confidence': min(max_priority[1] * 0.3, 1.0),
            'found_words': [word for priority in priority_words.values() for word in priority]
        }
    
    def merge_contexts(self, new_context: Dict, current_context: Dict) -> Dict:
        """Объединяет новый контекст с текущим"""
        merged = current_context.copy()
        
        # Объединяем ключевые слова
        if 'keywords' in new_context:
            for category in new_context['keywords']:
                if category not in merged.get('keywords', {}):
                    merged.setdefault('keywords', {})[category] = []
                merged['keywords'][category].extend(new_context['keywords'][category])
                merged['keywords'][category] = list(set(merged['keywords'][category]))
        
        # Объединяем упоминания
        if 'mentions' in new_context:
            merged['mentions'] = list(set(
                merged.get('mentions', []) + new_context['mentions']
            ))
        
        # Объединяем даты
        if 'dates' in new_context:
            merged['dates'] = merged.get('dates', []) + new_context['dates']
        
        # Обновляем приоритет если новый более уверенный
        if 'priority' in new_context:
            if new_context['priority']['confidence'] > merged.get('priority', {}).get('confidence', 0):
                merged['priority'] = new_context['priority']
        
        return merged

context_analyzer = ContextAnalyzer()