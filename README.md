# CreatmanTaskBot

[English](#english) | [Русский](#russian)

## English

### About
CreatmanTaskBot is a task management bot that integrates with various services to help streamline your workflow.

### Features
- Task management integration with Trello
- AI-powered task analysis and suggestions
- Multi-language support (English/Russian)
- Secure configuration management
- Comprehensive logging system

### Installation
1. Clone the repository:
```bash
git clone https://github.com/yourusername/CreatmanTaskBot.git
cd CreatmanTaskBot
```

2. Create and activate virtual environment:
```bash
python -m venv venv
.\venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
- Copy `.env.example` to `.env`
- Fill in your API keys and configuration

### Usage
1. Start the bot:
```bash
python run.py
```

2. Available commands:
- `/start` - Initialize the bot
- `/help` - Show available commands
- `/settings` - Configure bot settings
- `/language` - Change interface language

### Development
- Python 3.8+
- FastAPI for API endpoints
- SQLAlchemy for database management
- Alembic for migrations

### Deployment
The project is configured for deployment on render.com:
1. Connect your GitHub repository
2. Configure environment variables
3. Select Python environment
4. Set start command: `python run.py`

### Support
For support, please create an issue in the GitHub repository or contact support@example.com

---

## Русский

### О проекте
CreatmanTaskBot - это бот для управления задачами, интегрирующийся с различными сервисами для оптимизации рабочего процесса.

### Возможности
- Интеграция с Trello для управления задачами
- AI-анализ задач и рекомендации
- Поддержка нескольких языков (английский/русский)
- Безопасное управление конфигурацией
- Комплексная система логирования

### Установка
1. Клонируйте репозиторий:
```bash
git clone https://github.com/yourusername/CreatmanTaskBot.git
cd CreatmanTaskBot
```

2. Создайте и активируйте виртуальное окружение:
```bash
python -m venv venv
.\venv\Scripts\activate
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Настройте переменные окружения:
- Скопируйте `.env.example` в `.env`
- Заполните ваши API ключи и конфигурацию

### Использование
1. Запустите бота:
```bash
python run.py
```

2. Доступные команды:
- `/start` - Инициализация бота
- `/help` - Показать доступные команды
- `/settings` - Настройки бота
- `/language` - Изменить язык интерфейса

### Разработка
- Python 3.8+
- FastAPI для API эндпоинтов
- SQLAlchemy для работы с базой данных
- Alembic для миграций

### Развертывание
Проект настроен для развертывания на render.com:
1. Подключите ваш GitHub репозиторий
2. Настройте переменные окружения
3. Выберите Python окружение
4. Установите команду запуска: `python run.py`

### Поддержка
Для получения поддержки создайте issue в GitHub репозитории или напишите на support@example.com
