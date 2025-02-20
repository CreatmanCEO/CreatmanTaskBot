from fastapi import APIRouter, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram import Bot
from telegram import Message
from app.config import get_settings
from app.trello.client import TrelloClient
from app.ai.processor import AIProcessor
from app.bot.state_manager import state_manager
try:
    from app.utils.context import context_analyzer
except ImportError:
    # Создаем заглушку если модуль недоступен
    context_analyzer = None
    logger.warning("Context analyzer not available")
import logging
from typing import List, Dict, Any, Optional
from telegram.ext import ContextTypes
from app.services.trello import TrelloService
from app.models.user import User
from app.utils.localization import localization
from app.utils.logger import app_logger
from app.db.session import SessionLocal
from sqlalchemy.orm import Session

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация компонентов
router = APIRouter(prefix="/webhook", tags=["telegram"])
settings = get_settings()
trello_client = TrelloClient()
ai_processor = AIProcessor()

# Создаем бота
bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)

# Клавиатура для основного меню
def get_main_keyboard():
    keyboard = [
        [KeyboardButton('📋 Создать задачу'), KeyboardButton('📊 Мои доски')],
        [KeyboardButton('⚙️ Настройки'), KeyboardButton('❓ Помощь')]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Вспомогательные функции для работы с клавиатурой
def get_board_keyboard(boards: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Создает клавиатуру для выбора доски"""
    keyboard = []
    for board in boards:
        keyboard.append([InlineKeyboardButton(
            board['name'],
            callback_data=f"board_{board['id']}"
        )])
    keyboard.append([InlineKeyboardButton("🔄 Обновить", callback_data="refresh_boards")])
    return InlineKeyboardMarkup(keyboard)

def get_list_keyboard(lists: List[Dict[str, Any]], board_id: str) -> InlineKeyboardMarkup:
    """Создает клавиатуру для выбора списка"""
    keyboard = []
    for lst in lists:
        keyboard.append([InlineKeyboardButton(
            f"📑 {lst['name']}",
            callback_data=f"list_{lst['id']}"
        )])
    keyboard.append([InlineKeyboardButton("⬅️ К доскам", callback_data="back_to_boards")])
    return InlineKeyboardMarkup(keyboard)

# Предыдущие обработчики команд и сообщений
     
async def handle_list_selection(update: Update, list_id: str):
    try:
        lst = await trello_client.get_list(list_id)
        cards = await trello_client.get_list_cards(list_id)
        
        reply_text = f"📋 *Список: {lst['name']}*\n"
        reply_text += f"_Последнее обновление: {lst.get('dateLastActivity', 'не указано')}_\n\n"
        
        if cards:
            reply_text += "*Текущие задачи:*\n"
            for card in cards:
                # Название задачи (жирным)
                reply_text += f"• *{card['name']}*\n"
                
                # Метки с цветовым обозначением
                if card.get('labels'):
                    labels = []
                    for label in card['labels']:
                        color_emoji = {
                            'green': '🟢',
                            'yellow': '🟡',
                            'orange': '🟠',
                            'red': '🔴',
                            'purple': '🟣',
                            'blue': '🔵',
                            'sky': '💠',
                            'lime': '💚',
                            'pink': '💗',
                            'black': '⚫'
                        }.get(label.get('color', ''), '⚪')
                        label_text = label.get('name', label.get('color', 'метка'))
                        labels.append(f"{color_emoji}{label_text}")
                    if labels:
                        reply_text += f"  _{' '.join(labels)}_\n"
                
                # Прогресс чек-листа (если есть)
                if card.get('badges', {}).get('checkItems', 0) > 0:
                    total = card['badges']['checkItems']
                    checked = card['badges'].get('checkItemsChecked', 0)
                    reply_text += f"  ✓ {checked}/{total}\n"
                
                # Участники (только никнеймы)
                if card.get('idMembers'):
                    members = await trello_client.get_card_members(card['id'])
                    if members:
                        usernames = [m.get('username', '') for m in members if m.get('username')]
                        if usernames:
                            reply_text += f"  👥 {', '.join(usernames)}\n"
                
                # Дата обновления (курсивом)
                if card.get('dateLastActivity'):
                    date_str = card['dateLastActivity'][:10]
                    reply_text += f"  _Обновлено: {date_str}_\n"
                
                reply_text += "\n"
        else:
            reply_text += "_Список пока пуст_\n\n"
        
        reply_text += "📝 *Чтобы создать новую задачу:*\n"
        reply_text += "Отправьте описание задачи одним сообщением\n"
        reply_text += "Можно указать срок в формате 'до ДД.ММ.YYYY'"
        
        # Сохраняем выбранный список для пользователя
        user_state = state_manager.get_user_state(update.callback_query.from_user.id)
        user_state.selected_list_id = list_id
        user_state.selected_board_id = lst['idBoard']
        
        keyboard = [
            [InlineKeyboardButton("⬅️ К спискам", callback_data=f"board_{lst['idBoard']}")],
            [InlineKeyboardButton("❌ Отменить создание", callback_data="cancel_create")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.message.edit_text(
            reply_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"Error in list selection: {e}")
        await update.callback_query.message.edit_text(
            "Произошла ошибка при получении информации о списке."
        )
     
async def handle_board_selection(update: Update, board_id: str):
    """Обработка выбора доски"""
    try:
        # Получаем списки на доске
        lists = await trello_client.get_board_lists(board_id)
        
        keyboard = []
        reply_text = "Выберите список для просмотра или создания задачи:\n\n"
        
        for lst in lists:
            cards_count = len(await trello_client.get_list_cards(lst['id']))
            reply_text += f"📑 *{lst['name']}* ({cards_count} задач)\n"
            keyboard.append([InlineKeyboardButton(
                f"📑 {lst['name']}",
                callback_data=f"list_{lst['id']}"
            )])
        
        # Добавляем кнопку возврата к доскам
        keyboard.append([InlineKeyboardButton("⬅️ К доскам", callback_data="back_to_boards")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.message.edit_text(
            reply_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        # Сохраняем текущую доску в состоянии пользователя
        user_state = state_manager.get_user_state(update.callback_query.from_user.id)
        user_state.selected_board_id = board_id
        
    except Exception as e:
        logger.error(f"Error in board selection: {e}")
        await update.callback_query.message.edit_text(
            "Произошла ошибка при получении списков доски."
        )
        
# Основные обработчики команд и сообщений
async def handle_start(update: Update):
    """Обработка команды /start"""
    user_state = state_manager.get_user_state(update.message.from_user.id)
    user_state.clear()
    
    await update.message.reply_text(
        "Привет! Я CreatmanTaskBot. Я помогу вам управлять задачами в Trello.\n\n"
        "Вы можете:\n"
        "1. Пересылать мне сообщения для создания задач\n"
        "2. Создавать задачи напрямую\n"
        "3. Просматривать и управлять досками Trello",
        reply_markup=get_main_keyboard()
    )

# app/bot/handlers.py

async def handle_forwarded_messages(update: Update):
    """Обработка пересланных сообщений"""
    logger.info("Starting handle_forwarded_messages")
    user_id = update.message.from_user.id
    user_state = state_manager.get_user_state(user_id)
    
    try:
        forward_info = {
            'text': update.message.text,
            'from_user': update.message.forward_from.username if update.message.forward_from else 'Unknown',
            'chat_id': update.message.forward_from_chat.id if update.message.forward_from_chat else None,
            'chat_title': update.message.forward_from_chat.title if update.message.forward_from_chat else None,
            'date': update.message.forward_date.isoformat() if update.message.forward_date else None
        }
        
        state_manager.add_forwarded_message(user_id, forward_info)
        messages = state_manager.get_forwarded_messages(user_id)
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Завершить и проанализировать", callback_data="analyze_messages")
        ]])
        
        count_text = f"Сообщение добавлено. Всего собрано: {len(messages)}."
        await update.message.reply_text(count_text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error in handle_forwarded_messages: {e}", exc_info=True)
        await update.message.reply_text("Произошла ошибка при обработке сообщения.")

async def analyze_forwarded_messages(update: Update):
    """Анализ пересланных сообщений через AI"""
    user_id = update.callback_query.from_user.id
    user_state = state_manager.get_user_state(user_id)
    
    if not user_state.forwarded_messages:
        await update.callback_query.message.reply_text("Нет сообщений для анализа.")
        return
        
    try:
        context = {
            'boards': await trello_client.get_boards_with_details(),
            'preferences': state_manager.get_board_preferences(user_id),
            'chat_context': user_state.message_context
        }
        
        analysis = await ai_processor.analyze_messages(
            user_state.forwarded_messages,
            context
        )
        
        if not analysis:
            raise Exception("AI analysis failed")
            
        tasks = analysis.get('tasks', [])
        if not tasks:
            await update.callback_query.message.reply_text(
                "Не удалось найти задачи в сообщениях."
            )
            return
            
        user_state.temp_data['analysis'] = analysis
        await show_analysis_results(update.callback_query.message, tasks)
        
    except Exception as e:
        logger.error(f"Error in analyze_forwarded_messages: {e}", exc_info=True)
        await update.callback_query.message.reply_text(
            "Произошла ошибка при анализе сообщений."
        )

async def handle_direct_task_creation(update: Update):
    """Обработка прямого создания задачи"""
    user_id = update.message.from_user.id
    user_state = state_manager.get_user_state(user_id)
    
    try:
        task_analysis = await ai_processor.process_direct_task_creation(
            update.message.text
        )
        
        if task_analysis and task_analysis.get('tasks'):
            user_state.temp_data['analysis'] = task_analysis
            await show_analysis_results(update.message, task_analysis['tasks'])
        else:
            await update.message.reply_text(
                "Не удалось создать задачу. Попробуйте описать задачу подробнее."
            )
            
    except Exception as e:
        logger.error(f"Error in direct task creation: {e}", exc_info=True)
        await update.message.reply_text(
            "Произошла ошибка при создании задачи."
        )

async def handle_task_creation_from_analysis(update: Update, task_index: int):
    """Создание задачи на основе анализа"""
    user_id = update.callback_query.from_user.id
    user_state = state_manager.get_user_state(user_id)
    
    analysis = user_state.temp_data.get('analysis')
    if not analysis or 'tasks' not in analysis:
        await update.callback_query.message.edit_text(
            "Произошла ошибка: данные анализа не найдены. Попробуйте заново."
        )
        return
    
    try:
        task_data = analysis['tasks'][task_index]
        board_info = task_data.get('recommended_board', {})
        
        # Если уверенность в выборе доски высокая, создаем задачу
        if board_info.get('confidence', 0) > 0.7:
            task = await trello_client.create_task_from_analysis(task_data)
            if task:
                await show_task_creation_result(update.callback_query.message, task)
            else:
                raise Exception("Failed to create task")
        else:
            # Запрашиваем подтверждение доски
            await request_board_selection(
                update.callback_query.message,
                task_data,
                analysis['context_analysis'].get('project_hints', [])
            )
            
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        await update.callback_query.message.edit_text(
            "Произошла ошибка при создании задачи. Попробуйте еще раз или создайте задачу вручную."
        )

async def show_analysis_results(message, tasks: List[Dict]):
    """Отображение результатов анализа задач"""
    reply_text = "📋 *Найденные задачи:*\n\n"
    
    for i, task in enumerate(tasks, 1):
        reply_text += f"{i}. *{task['name']}*\n"
        if task.get('description'):
            reply_text += f"📝 _{task['description']}_\n"
        if task.get('due_date'):
            reply_text += f"📅 Срок: {task['due_date']}\n"
        if task.get('members'):
            reply_text += f"👥 Участники: {', '.join(task['members'])}\n"
        if task.get('labels'):
            reply_text += f"🏷 Метки: {', '.join(task['labels'])}\n"
        
        board_info = task.get('recommended_board', {})
        if board_info.get('confidence', 0) > 0.7:
            reply_text += f"📊 Рекомендуемая доска: *{board_info.get('name', '')}*\n"
            if board_info.get('reasoning'):
                reply_text += f"💡 _{board_info['reasoning']}_\n"
        
        reply_text += "\n"

    keyboard = []
    if len(tasks) == 1:
        keyboard.append([
            InlineKeyboardButton("✅ Создать задачу", callback_data="create_analyzed_task_0")
        ])
    else:
        for i, _ in enumerate(tasks):
            keyboard.append([
                InlineKeyboardButton(f"✅ Создать задачу {i+1}", 
                                   callback_data=f"create_analyzed_task_{i}")
            ])

    keyboard.append([
        InlineKeyboardButton("🔄 Изменить", callback_data="edit_analysis"),
        InlineKeyboardButton("❌ Отмена", callback_data="cancel_analysis")
    ])

    if isinstance(message, Message):
        await message.reply_text(
            reply_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    else:
        await message.edit_text(
            reply_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

async def show_task_creation_result(message, task: Dict):
    """Показывает результат создания задачи"""
    reply_text = "✅ *Задача создана успешно!*\n\n"
    reply_text += f"*{task['name']}*\n"
    
    if task.get('desc'):
        reply_text += f"📝 _{task['desc']}_\n"
    if task.get('due'):
        reply_text += f"📅 Срок: {task['due'][:10]}\n"
    if task.get('labels'):
        labels = [f"#{label['name']}" for label in task['labels']]
        reply_text += f"🏷 Метки: {', '.join(labels)}\n"
    if task.get('members'):
        members = [member.get('username', 'Unknown') for member in task['members']]
        reply_text += f"👥 Участники: {', '.join(members)}\n"
    
    keyboard = [
        [InlineKeyboardButton("🔗 Открыть в Trello", url=task['url'])],
        [
            InlineKeyboardButton("✏️ Редактировать", 
                               callback_data=f"edit_task_{task['id']}"),
            InlineKeyboardButton("📋 Создать ещё", 
                               callback_data="create_new_task")
        ]
    ]
    
    await message.edit_text(
        reply_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def request_board_selection(message, task_data: Dict, project_hints: List[Dict]):
    """Запрашивает выбор доски для задачи"""
    reply_text = "📋 *Выберите доску для задачи:*\n\n"
    reply_text += f"Задача: *{task_data['name']}*\n\n"
    
    if project_hints:
        reply_text += "*Рекомендации на основе анализа:*\n"
        for hint in project_hints:
            reply_text += f"• {hint['board_name']}: _{hint['reason']}_\n"
    
    boards = await trello_client.get_boards()
    keyboard = get_board_keyboard(boards)
    
    await message.edit_text(
        reply_text,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

async def handle_boards(message):
    """Показывает список досок пользователя"""
    try:
        boards = await trello_client.get_boards_with_details()
        if not boards:
            await message.reply_text(
                "У вас пока нет досок в Trello!",
                reply_markup=get_main_keyboard()
            )
            return
        
        reply_text = "📋 *Ваши доски Trello:*\n\n"
        for board in boards:
            reply_text += f"*{board['name']}*\n"
            if board.get('desc'):
                reply_text += f"_{board['desc']}_\n"
            
            lists_count = len(board.get('lists', []))
            cards_count = sum(len(lst.get('cards', [])) for lst in board.get('lists', []))
            
            reply_text += f"📑 Списков: {lists_count}\n"
            reply_text += f"📌 Задач: {cards_count}\n"
            reply_text += f"[Открыть в Trello]({board.get('url')})\n\n"
        
        keyboard = get_board_keyboard(boards)
        
        await message.reply_text(
            reply_text,
            reply_markup=keyboard,
            parse_mode='Markdown',
            disable_web_page_preview=True
        )
        
    except Exception as e:
        logger.error(f"Error getting boards: {e}")
        await message.reply_text(
            "Произошла ошибка при получении списка досок.",
            reply_markup=get_main_keyboard()
        )

async def handle_edit_task(update: Update, task_id: str):
    """Обработка редактирования задачи"""
    try:
        task = await trello_client.get_card(task_id)
        if not task:
            raise Exception("Task not found")
        
        keyboard = [
            [InlineKeyboardButton("📝 Описание", callback_data=f"edit_desc_{task_id}")],
            [InlineKeyboardButton("📅 Срок", callback_data=f"edit_due_{task_id}")],
            [InlineKeyboardButton("🏷 Метки", callback_data=f"edit_labels_{task_id}")],
            [InlineKeyboardButton("👥 Участники", callback_data=f"edit_members_{task_id}")],
            [InlineKeyboardButton("📋 Чек-лист", callback_data=f"edit_checklist_{task_id}")],
            [InlineKeyboardButton("❌ Закрыть", callback_data="close_edit")]
        ]
        
        reply_text = f"*Редактирование задачи:*\n\n"
        reply_text += f"📌 *{task['name']}*\n"
        if task.get('desc'):
            reply_text += f"📝 _{task['desc']}_\n"
        if task.get('due'):
            reply_text += f"📅 Срок: {task['due'][:10]}\n"
        if task.get('labels'):
            labels = [f"#{label['name']}" for label in task['labels']]
            reply_text += f"🏷 Метки: {', '.join(labels)}\n"
        if task.get('members'):
            members = [member.get('username', 'Unknown') for member in task['members']]
            reply_text += f"👥 Участники: {', '.join(members)}\n"
        
        await update.callback_query.message.edit_text(
            reply_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error editing task: {e}")
        await update.callback_query.message.edit_text(
            "Произошла ошибка при редактировании задачи."
        )

async def handle_callback_query(update: Update):
    """Обработка callback запросов"""
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    
    try:
        if data.startswith('board_'):
            board_id = data.replace('board_', '')
            await handle_board_selection(update, board_id)
            
        elif data.startswith('list_'):
            list_id = data.replace('list_', '')
            await handle_list_selection(update, list_id)
            
        elif data == 'analyze_messages':
            await analyze_forwarded_messages(update)
            
        elif data.startswith('create_analyzed_task_'):
            task_index = int(data.split('_')[-1])
            await handle_task_creation_from_analysis(update, task_index)
            
        elif data.startswith('edit_task_'):
            task_id = data.replace('edit_task_', '')
            await handle_edit_task(update, task_id)
            
        elif data == 'refresh_boards':
            await handle_boards(query.message)
            
        elif data == 'back_to_boards':
            await handle_boards(query.message)
            
        elif data == 'cancel_analysis':
            user_state = state_manager.get_user_state(user_id)
            user_state.clear()
            await query.message.edit_text(
                "Анализ отменен. Вы можете начать заново.",
                reply_markup=get_main_keyboard()
            )
            
        elif data == 'close_edit':
            await query.message.delete()
            
        await query.answer()
        
    except Exception as e:
        logger.error(f"Error in callback query: {e}")
        await query.message.edit_text(
            "Произошла ошибка при обработке запроса."
        )

async def handle_help(message):
    """Обработка команды помощи"""
    help_text = (
        "*Как пользоваться ботом:*\n\n"
        "1. *Создание задач:*\n"
        "   • Перешлите сообщения для анализа\n"
        "   • Используйте команду 'Создать задачу'\n\n"
        "2. *Работа с досками:*\n"
        "   • Просматривайте через 'Мои доски'\n"
        "   • Выбирайте списки для задач\n\n"
        "3. *Дополнительно:*\n"
        "   • Используйте #тэги для меток\n"
        "   • Указывайте @пользователей\n"
        "   • Добавляйте сроки 'до ДД.ММ.ГГГГ'\n\n"
        "Команды:\n"
        "/start - Начать работу\n"
        "/boards - Показать доски\n"
        "/create - Создать задачу\n"
        "/help - Показать эту справку"
    )
    
    await message.reply_text(
        help_text,
        parse_mode='Markdown',
        reply_markup=get_main_keyboard()
    )

# Основной обработчик webhook
@router.post("/{token}")
async def telegram_webhook(token: str, request: Request):
    if token != settings.TELEGRAM_BOT_TOKEN:
        return {"error": "Invalid token"}
    
    try:
        update_data = await request.json()
        logger.info(f"Received update: {update_data}")
        
        update = Update.de_json(update_data, bot)
        
        # Обработка callback query
        if update.callback_query:
            await handle_callback_query(update)
            return {"ok": True}
        
        # Обработка сообщений
        if update.message:
            user_id = update.message.from_user.id
            user_state = state_manager.get_user_state(user_id)
            
            # Проверяем пересланные сообщения
            if getattr(update.message, 'forward_date', None):
                await handle_forwarded_messages(update)
                
            # Обработка команд и текстовых сообщений
            elif update.message.text:
                text = update.message.text
                logger.info(f"Processing text message: {text}")
                
                if text == '/start':
                    await handle_start(update)
                elif text == '📊 Мои доски' or text == '/boards':
                    await handle_boards(update.message)
                elif text == '📋 Создать задачу' or text == '/create':
                    user_state.current_action = 'creating_task'
                    await update.message.reply_text(
                        "Опишите задачу или перешлите сообщения для анализа"
                    )
                elif text == '❓ Помощь' or text == '/help':
                    await handle_help(update.message)
                # Обработка прямого создания задачи
                elif user_state.current_action == 'creating_task':
                    await handle_direct_task_creation(update)
                
        return {"ok": True}
        
    except Exception as e:
        logger.error(f"Error processing update: {e}", exc_info=True)
        return {"error": str(e)}

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start."""
    try:
        # Получаем или создаем пользователя
        db = SessionLocal()
        user = db.query(User).filter(User.telegram_id == str(update.effective_user.id)).first()
        
        if not user:
            user = User(telegram_id=str(update.effective_user.id))
            db.add(user)
            db.commit()
            
            # Запрашиваем выбор языка
            keyboard = [
                [
                    InlineKeyboardButton("English 🇬🇧", callback_data="lang_en"),
                    InlineKeyboardButton("Русский 🇷🇺", callback_data="lang_ru")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "Please select your language / Пожалуйста, выберите язык:",
                reply_markup=reply_markup
            )
        else:
            # Если пользователь уже авторизован
            if user.is_authorized:
                await update.message.reply_text(
                    localization.get_text("welcome_back", language=user.language)
                )
            else:
                # Если не авторизован, но язык уже выбран
                await request_trello_token(update, context)
                
    except Exception as e:
        app_logger.error(f"Ошибка в команде /start: {str(e)}")
        await update.message.reply_text("An error occurred. Please try again.")
    finally:
        db.close()

async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выбора языка."""
    query = update.callback_query
    lang = query.data.split('_')[1]
    
    try:
        db = SessionLocal()
        user = db.query(User).filter(User.telegram_id == str(update.effective_user.id)).first()
        
        if user:
            user.language = lang
            db.commit()
            
            # Устанавливаем язык в локализации
            localization.set_language(lang)
            
            # Отправляем приветственное сообщение
            await query.message.edit_text(localization.get_text("welcome_message"))
            
            # Запрашиваем токен Trello
            await request_trello_token(update, context)
            
    except Exception as e:
        app_logger.error(f"Ошибка при выборе языка: {str(e)}")
        await query.message.edit_text("An error occurred. Please try again. /start")
    finally:
        db.close()

async def request_trello_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запрос токена Trello."""
    message = """
Для работы с ботом необходимо получить API токен Trello. Следуйте инструкции:

1. Перейдите по ссылке: https://trello.com/app-key
2. Войдите в свой аккаунт Trello
3. Нажмите "Generate a Token"
4. Скопируйте полученный токен и отправьте его мне

Отправьте токен в следующем сообщении.
"""
    await update.effective_message.reply_text(message)
    context.user_data['waiting_for'] = 'trello_token'

async def handle_trello_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка полученного токена Trello."""
    token = update.message.text
    
    # Проверка формата токена
    if not TrelloService.validate_token_format(token):
        await update.message.reply_text(
            "❌ Неверный формат токена. Токен должен состоять из 64 символов (цифры и буквы a-f). "
            "Пожалуйста, проверьте токен и отправьте его снова."
        )
        return
    
    # Создаем сервис Trello и проверяем валидность токена
    trello_service = TrelloService(token)
    if not trello_service.validate_token():
        await update.message.reply_text(
            "❌ Токен недействителен. Пожалуйста, убедитесь, что вы правильно скопировали токен "
            "и отправьте его снова."
        )
        return
    
    # Запрашиваем email для верификации
    await update.message.reply_text(
        "✅ Токен прошел проверку. Пожалуйста, введите email, который использовался "
        "для регистрации в Trello:"
    )
    context.user_data['trello_token'] = token
    context.user_data['waiting_for'] = 'email'

async def handle_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка email для верификации."""
    email = update.message.text
    token = context.user_data.get('trello_token')
    
    if not token:
        await update.message.reply_text("❌ Произошла ошибка. Пожалуйста, начните процесс заново с /start")
        return
    
    trello_service = TrelloService(token)
    if not trello_service.verify_user_email(email):
        await update.message.reply_text(
            "❌ Email не соответствует указанному в профиле Trello. "
            "Пожалуйста, проверьте email и отправьте его снова."
        )
        return
    
    try:
        # Сохраняем данные пользователя
        db = SessionLocal()
        user = db.query(User).filter(User.telegram_id == str(update.effective_user.id)).first()
        
        if user:
            user.email = email
            user.trello_token = token
            user.is_authorized = True
            db.commit()
            
            await update.message.reply_text(
                "🎉 Поздравляем! Авторизация успешно завершена. "
                "Теперь вы можете использовать все возможности бота.\n\n"
                "Используйте /help для просмотра доступных команд."
            )
            
    except Exception as e:
        app_logger.error(f"Ошибка при сохранении данных пользователя: {str(e)}")
        await update.message.reply_text("❌ Произошла ошибка при сохранении данных. Попробуйте позже.")
    finally:
        db.close()

async def change_token_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды смены токена."""
    await request_trello_token(update, context)

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик входящих сообщений."""
    waiting_for = context.user_data.get('waiting_for')
    
    if waiting_for == 'trello_token':
        await handle_trello_token(update, context)
    elif waiting_for == 'email':
        await handle_email(update, context)
    else:
        # Обработка других сообщений
        pass