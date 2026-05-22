import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
import json
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота
API_TOKEN = os.getenv('API_TOKEN')  # Токен из переменных окружения Render
ADMIN_ID = os.getenv('ADMIN_ID')  # ID администратора из переменных окружения
ADMIN_PASSWORD = "administartor=1"

# Проверка наличия обязательных переменных
if not API_TOKEN:
    raise ValueError("Не указан API_TOKEN в переменных окружения")
if not ADMIN_ID:
    raise ValueError("Не указан ADMIN_ID в переменных окружения")

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Состояния для админ-панели
class AdminStates(StatesGroup):
    waiting_for_password = State()
    admin_panel = State()
    editing_schedule = State()
    waiting_class_schedule = State()
    waiting_day_schedule = State()
    waiting_lessons_schedule = State()
    editing_events = State()
    waiting_event_title = State()
    waiting_event_date = State()
    waiting_event_description = State()
    editing_teachers = State()
    waiting_teacher_name = State()
    waiting_teacher_subject = State()

# Состояния для анонимных отзывов
class ReviewStates(StatesGroup):
    waiting_for_review = State()

# Загрузка данных из JSON файлов
def load_data():
    try:
        with open('schedule.json', 'r', encoding='utf-8') as f:
            schedule = json.load(f)
    except FileNotFoundError:
        schedule = {}
        save_data(schedule, 'schedule.json')
    
    try:
        with open('events.json', 'r', encoding='utf-8') as f:
            events = json.load(f)
    except FileNotFoundError:
        events = {"events": []}
        save_data(events, 'events.json')
    
    try:
        with open('teachers.json', 'r', encoding='utf-8') as f:
            teachers = json.load(f)
    except FileNotFoundError:
        teachers = {"teachers": []}
        save_data(teachers, 'teachers.json')
    
    try:
        with open('anonymous_reviews.json', 'r', encoding='utf-8') as f:
            reviews = json.load(f)
    except FileNotFoundError:
        reviews = {"reviews": []}
        save_data(reviews, 'anonymous_reviews.json')
    
    return schedule, events, teachers, reviews

def save_data(data, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Только классы А и Б с 5 по 11
CLASSES = [
    "5А", "5Б",
    "6А", "6Б",
    "7А", "7Б",
    "8А", "8Б",
    "9А", "9Б",
    "10А", "10Б",
    "11А", "11Б"
]

# Главное меню для учеников
def get_main_menu():
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    buttons = [
        InlineKeyboardButton("📚 Расписание", callback_data="schedule"),
        InlineKeyboardButton("🎉 События", callback_data="events"),
        InlineKeyboardButton("👨‍🏫 Анонимный отзыв об учителе", callback_data="anonymous_review"),
        InlineKeyboardButton("📝 Обратная связь", callback_data="feedback"),
        InlineKeyboardButton("ℹ️ О лицее", callback_data="about")
    ]
    
    keyboard.add(*buttons)
    return keyboard

# Меню выбора класса для расписания
def get_classes_menu():
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    buttons = []
    for class_name in CLASSES:
        buttons.append(InlineKeyboardButton(
            class_name, 
            callback_data=f"schedule_{class_name}"
        ))
    
    keyboard.add(*buttons)
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_main"))
    return keyboard

# Меню выбора учителя для отзыва
def get_teachers_menu():
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    _, _, teachers, _ = load_data()
    buttons = []
    
    if teachers.get("teachers"):
        for teacher in teachers["teachers"]:
            buttons.append(InlineKeyboardButton(
                teacher["name"], 
                callback_data=f"review_teacher_{teacher['id']}"
            ))
        
        # Размещаем по 2 кнопки в ряду
        for i in range(0, len(buttons), 2):
            if i + 1 < len(buttons):
                keyboard.row(buttons[i], buttons[i + 1])
            else:
                keyboard.row(buttons[i])
    else:
        keyboard.add(InlineKeyboardButton(
            "Список учителей пока не загружен", 
            callback_data="none"
        ))
    
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_main"))
    return keyboard

# Меню админ-панели
def get_admin_menu():
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    buttons = [
        InlineKeyboardButton("📚 Редактировать расписание", callback_data="admin_schedule"),
        InlineKeyboardButton("🎉 Редактировать события", callback_data="admin_events"),
        InlineKeyboardButton("👨‍🏫 Управление учителями", callback_data="admin_teachers"),
        InlineKeyboardButton("📊 Просмотр отзывов", callback_data="admin_reviews"),
        InlineKeyboardButton("❌ Выйти из админ-панели", callback_data="exit_admin")
    ]
    
    keyboard.add(*buttons)
    return keyboard

# Обработчик команды /start
@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    welcome_text = (
        "👋 Добро пожаловать в официального бота МОУ Лицей №4 г. Люберцы!\n\n"
        "🏫 Здесь вы можете:\n"
        "📚 Посмотреть актуальное расписание для 5-11 классов\n"
        "🎉 Узнать о предстоящих событиях лицея\n"
        "👨‍🏫 Оставить анонимный отзыв об учителе\n"
        "📝 Связаться с администрацией\n\n"
        "Выберите нужный раздел:"
    )
    
    await message.answer(welcome_text, reply_markup=get_main_menu())

# Обработчик команды /admin
@dp.message_handler(commands=['admin'])
async def admin_command(message: types.Message):
    await message.answer("🔐 Введите пароль администратора:")
    await AdminStates.waiting_for_password.set()

# Обработчик пароля администратора
@dp.message_handler(state=AdminStates.waiting_for_password)
async def check_admin_password(message: types.Message, state: FSMContext):
    if message.text == ADMIN_PASSWORD:
        await message.answer(
            "✅ Доступ разрешен! Добро пожаловать в админ-панель.\n\n"
            "Здесь вы можете редактировать расписание, события и список учителей.",
            reply_markup=get_admin_menu()
        )
        await AdminStates.admin_panel.set()
    else:
        await message.answer("❌ Неверный пароль! Доступ запрещен.")
        await state.finish()

# ==================== ОБРАБОТЧИКИ CALLBACK ДЛЯ УЧЕНИКОВ ====================

@dp.callback_query_handler(lambda c: c.data == 'back_to_main')
async def back_to_main(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(
        "Выберите нужный раздел:",
        reply_markup=get_main_menu()
    )

@dp.callback_query_handler(lambda c: c.data == 'schedule')
async def show_classes_for_schedule(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(
        "📚 Выберите класс для просмотра расписания:",
        reply_markup=get_classes_menu()
    )

@dp.callback_query_handler(lambda c: c.data.startswith('schedule_'))
async def show_schedule_for_class(callback_query: types.CallbackQuery):
    class_name = callback_query.data.replace('schedule_', '')
    schedule, _, _, _ = load_data()
    
    class_schedule = schedule.get(class_name, {})
    
    if class_schedule:
        schedule_text = f"📚 Расписание для {class_name} класса:\n\n"
        
        days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница"]
        for day in days:
            if day in class_schedule:
                schedule_text += f"📅 {day}:\n"
                for i, lesson in enumerate(class_schedule[day], 1):
                    schedule_text += f"   {i}. {lesson['time']} - {lesson['subject']} (каб. {lesson['room']})\n"
                schedule_text += "\n"
    else:
        schedule_text = f"📚 Расписание для {class_name} класса пока не добавлено.\nАдминистратор скоро добавит информацию."
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🔙 К выбору класса", callback_data="schedule"))
    keyboard.add(InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main"))
    
    await callback_query.message.edit_text(schedule_text, reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data == 'events')
async def show_events(callback_query: types.CallbackQuery):
    _, events, _, _ = load_data()
    
    if events.get("events"):
        events_text = "🎉 Актуальные события лицея:\n\n"
        for i, event in enumerate(events["events"], 1):
            events_text += f"📌 {i}. {event['title']}\n"
            events_text += f"📅 Дата: {event['date']}\n"
            events_text += f"📝 {event['description']}\n"
            events_text += "➖➖➖➖➖➖➖➖➖➖\n"
    else:
        events_text = "🎉 Пока нет актуальных событий.\nСледите за обновлениями!"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main"))
    
    await callback_query.message.edit_text(events_text, reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data == 'anonymous_review')
async def show_teachers_for_review(callback_query: types.CallbackQuery):
    _, _, teachers, _ = load_data()
    
    if teachers.get("teachers"):
        await callback_query.message.edit_text(
            "👨‍🏫 Выберите учителя для анонимного отзыва:",
            reply_markup=get_teachers_menu()
        )
    else:
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main"))
        
        await callback_query.message.edit_text(
            "👨‍🏫 Список учителей пока не загружен администратором.\n"
            "Пожалуйста, зайдите позже.",
            reply_markup=keyboard
        )

@dp.callback_query_handler(lambda c: c.data.startswith('review_teacher_'))
async def start_teacher_review(callback_query: types.CallbackQuery, state: FSMContext):
    teacher_id = callback_query.data.replace('review_teacher_', '')
    _, _, teachers, _ = load_data()
    
    teacher_name = "Неизвестный учитель"
    for teacher in teachers.get("teachers", []):
        if teacher["id"] == teacher_id:
            teacher_name = teacher["name"]
            break
    
    await state.update_data(review_teacher_id=teacher_id, review_teacher_name=teacher_name)
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("❌ Отмена", callback_data="anonymous_review"))
    
    await callback_query.message.edit_text(
        f"📝 Анонимный отзыв об учителе: {teacher_name}\n\n"
        "Пожалуйста, напишите ваш отзыв одним сообщением.\n"
        "Отзыв будет полностью анонимным.\n\n"
        "Для отмены нажмите кнопку ниже.",
        reply_markup=keyboard
    )
    
    await ReviewStates.waiting_for_review.set()

@dp.message_handler(state=ReviewStates.waiting_for_review)
async def process_review(message: types.Message, state: FSMContext):
    data = await state.get_data()
    teacher_id = data.get('review_teacher_id')
    teacher_name = data.get('review_teacher_name')
    
    _, _, _, reviews = load_data()
    
    new_review = {
        "teacher_id": teacher_id,
        "teacher_name": teacher_name,
        "text": message.text,
        "date": datetime.now().strftime("%d.%m.%Y %H:%M")
    }
    
    reviews["reviews"].append(new_review)
    save_data(reviews, 'anonymous_reviews.json')
    
    await message.answer(
        "✅ Ваш анонимный отзыв успешно отправлен!\n"
        "Спасибо за обратную связь.",
        reply_markup=get_main_menu()
    )
    
    await state.finish()

@dp.callback_query_handler(lambda c: c.data == 'feedback')
async def feedback_info(callback_query: types.CallbackQuery):
    feedback_text = (
        "📝 Для обратной связи с администрацией лицея,\n"
        "пожалуйста, напишите нам:\n\n"
        "📧 Email: licey4@mail.ru\n"
        "📞 Телефон: +7 (495) XXX-XX-XX\n\n"
        "Или напишите администратору в Telegram:"
    )
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("💬 Написать администратору", url=f"tg://user?id={ADMIN_ID}"))
    keyboard.add(InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main"))
    
    await callback_query.message.edit_text(feedback_text, reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data == 'about')
async def about_school(callback_query: types.CallbackQuery):
    about_text = (
        "🏫 МОУ Лицей №4 г. Люберцы\n\n"
        "📞 Телефон: +7 (495) XXX-XX-XX\n"
        "📧 Email: licey4@mail.ru\n"
        "📍 Адрес: г. Люберцы, ул. XXX, д. X\n\n"
        "🕐 Часы работы:\n"
        "Пн-Пт: 8:00 - 18:00\n"
        "Сб: 8:00 - 14:00\n"
        "Вс: выходной\n\n"
        "🎓 Мы обучаем учеников с 5 по 11 классы (А и Б)"
    )
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main"))
    
    await callback_query.message.edit_text(about_text, reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data == 'none')
async def none_callback(callback_query: types.CallbackQuery):
    await callback_query.answer("Этот раздел пока недоступен", show_alert=True)

# ==================== АДМИН-ПАНЕЛЬ ====================

@dp.callback_query_handler(lambda c: c.data == 'admin_schedule', state=AdminStates.admin_panel)
async def admin_schedule_menu(callback_query: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("➕ Добавить расписание", callback_data="add_schedule"),
        InlineKeyboardButton("❌ Удалить расписание класса", callback_data="delete_schedule"),
        InlineKeyboardButton("📋 Показать все расписания", callback_data="show_all_schedules"),
        InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin")
    )
    
    await callback_query.message.edit_text(
        "📚 Управление расписанием\n\n"
        "Выберите действие:",
        reply_markup=keyboard
    )

@dp.callback_query_handler(lambda c: c.data == 'add_schedule', state=AdminStates.admin_panel)
async def start_add_schedule(callback_query: types.CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(row_width=2)
    buttons = []
    for class_name in CLASSES:
        buttons.append(InlineKeyboardButton(
            class_name, 
            callback_data=f"admin_class_{class_name}"
        ))
    keyboard.add(*buttons)
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="admin_schedule"))
    
    await callback_query.message.edit_text(
        "📚 Выберите класс для добавления расписания:",
        reply_markup=keyboard
    )
    await AdminStates.waiting_class_schedule.set()

@dp.callback_query_handler(lambda c: c.data == 'delete_schedule', state=AdminStates.admin_panel)
async def start_delete_schedule(callback_query: types.CallbackQuery):
    schedule, _, _, _ = load_data()
    
    if schedule:
        keyboard = InlineKeyboardMarkup(row_width=2)
        buttons = []
        for class_name in CLASSES:
            if class_name in schedule:
                buttons.append(InlineKeyboardButton(
                    f"❌ {class_name}", 
                    callback_data=f"delete_class_{class_name}"
                ))
        if buttons:
            keyboard.add(*buttons)
        else:
            keyboard.add(InlineKeyboardButton("Нет расписаний для удаления", callback_data="none"))
        keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="admin_schedule"))
        
        await callback_query.message.edit_text(
            "📚 Выберите класс для удаления расписания:",
            reply_markup=keyboard
        )
    else:
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="admin_schedule"))
        await callback_query.message.edit_text(
            "📚 Нет добавленных расписаний.",
            reply_markup=keyboard
        )

@dp.callback_query_handler(lambda c: c.data.startswith('delete_class_'), state=AdminStates.admin_panel)
async def delete_class_schedule(callback_query: types.CallbackQuery):
    class_name = callback_query.data.replace('delete_class_', '')
    schedule, _, _, _ = load_data()
    
    if class_name in schedule:
        del schedule[class_name]
        save_data(schedule, 'schedule.json')
        await callback_query.answer(f"✅ Расписание {class_name} класса удалено!", show_alert=True)
    else:
        await callback_query.answer(f"❌ Расписание {class_name} класса не найдено!", show_alert=True)
    
    await callback_query.message.edit_text(
        "📚 Управление расписанием\n\nВыберите действие:",
        reply_markup=get_admin_menu()
    )

@dp.callback_query_handler(lambda c: c.data == 'show_all_schedules', state=AdminStates.admin_panel)
async def show_all_schedules_admin(callback_query: types.CallbackQuery):
    schedule, _, _, _ = load_data()
    
    if schedule:
        schedule_text = "📋 Все добавленные расписания:\n\n"
        for class_name in CLASSES:
            if class_name in schedule:
                schedule_text += f"✅ {class_name} класс\n"
    else:
        schedule_text = "📋 Нет добавленных расписаний."
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="admin_schedule"))
    
    await callback_query.message.edit_text(schedule_text, reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data.startswith('admin_class_'), state=AdminStates.waiting_class_schedule)
async def choose_day_for_schedule(callback_query: types.CallbackQuery, state: FSMContext):
    class_name = callback_query.data.replace('admin_class_', '')
    await state.update_data(schedule_class=class_name)
    
    days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница"]
    keyboard = InlineKeyboardMarkup(row_width=2)
    buttons = []
    for day in days:
        buttons.append(InlineKeyboardButton(day, callback_data=f"admin_day_{day}"))
    keyboard.add(*buttons)
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="admin_schedule"))
    
    await callback_query.message.edit_text(
        f"📚 Класс: {class_name}\n"
        "Выберите день недели:",
        reply_markup=keyboard
    )
    await AdminStates.waiting_day_schedule.set()

@dp.callback_query_handler(lambda c: c.data.startswith('admin_day_'), state=AdminStates.waiting_day_schedule)
async def input_lessons_for_day(callback_query: types.CallbackQuery, state: FSMContext):
    day = callback_query.data.replace('admin_day_', '')
    await state.update_data(schedule_day=day)
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("❌ Отмена", callback_data="admin_schedule"))
    
    await callback_query.message.edit_text(
        f"📚 День: {day}\n\n"
        "Введите расписание уроков в формате:\n"
        "ВРЕМЯ ПРЕДМЕТ КАБИНЕТ\n"
        "Каждый урок с новой строки\n\n"
        "Пример:\n"
        "8:30 Математика 305\n"
        "9:25 Русский_язык 201\n"
        "10:20 Физика 402",
        reply_markup=keyboard
    )
    await AdminStates.waiting_lessons_schedule.set()

@dp.message_handler(state=AdminStates.waiting_lessons_schedule)
async def save_schedule(message: types.Message, state: FSMContext):
    data = await state.get_data()
    class_name = data.get('schedule_class')
    day = data.get('schedule_day')
    
    schedule, _, _, _ = load_data()
    
    if class_name not in schedule:
        schedule[class_name] = {}
    
    lessons = []
    for line in message.text.strip().split('\n'):
        parts = line.strip().split()
        if len(parts) >= 3:
            time = parts[0]
            subject = parts[1].replace('_', ' ')
            room = ' '.join(parts[2:])
            lessons.append({
                "time": time,
                "subject": subject,
                "room": room
            })
    
    schedule[class_name][day] = lessons
    save_data(schedule, 'schedule.json')
    
    await message.answer(
        f"✅ Расписание для {class_name} класса на {day} сохранено!",
        reply_markup=get_admin_menu()
    )
    await AdminStates.admin_panel.set()

@dp.callback_query_handler(lambda c: c.data == 'admin_events', state=AdminStates.admin_panel)
async def admin_events_menu(callback_query: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("➕ Добавить событие", callback_data="add_event"),
        InlineKeyboardButton("❌ Удалить все события", callback_data="delete_all_events"),
        InlineKeyboardButton("📋 Показать события", callback_data="show_events_admin"),
        InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin")
    )
    
    await callback_query.message.edit_text(
        "🎉 Управление событиями\n\n"
        "Выберите действие:",
        reply_markup=keyboard
    )

@dp.callback_query_handler(lambda c: c.data == 'add_event', state=AdminStates.admin_panel)
async def start_add_event(callback_query: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("❌ Отмена", callback_data="admin_events"))
    
    await callback_query.message.edit_text(
        "🎉 Введите название события:",
        reply_markup=keyboard
    )
    await AdminStates.waiting_event_title.set()

@dp.message_handler(state=AdminStates.waiting_event_title)
async def process_event_title(message: types.Message, state: FSMContext):
    await state.update_data(event_title=message.text)
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("❌ Отмена", callback_data="admin_events"))
    
    await message.answer(
        "📅 Введите дату события в формате ДД.ММ.ГГГГ:",
        reply_markup=keyboard
    )
    await AdminStates.waiting_event_date.set()

@dp.message_handler(state=AdminStates.waiting_event_date)
async def process_event_date(message: types.Message, state: FSMContext):
    await state.update_data(event_date=message.text)
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("❌ Отмена", callback_data="admin_events"))
    
    await message.answer(
        "📝 Введите описание события:",
        reply_markup=keyboard
    )
    await AdminStates.waiting_event_description.set()

@dp.message_handler(state=AdminStates.waiting_event_description)
async def process_event_description(message: types.Message, state: FSMContext):
    data = await state.get_data()
    title = data.get('event_title')
    date = data.get('event_date')
    description = message.text
    
    _, events, _, _ = load_data()
    
    new_event = {
        "title": title,
        "date": date,
        "description": description
    }
    
    events["events"].append(new_event)
    save_data(events, 'events.json')
    
    await message.answer(
        "✅ Событие успешно добавлено!",
        reply_markup=get_admin_menu()
    )
    await AdminStates.admin_panel.set()

@dp.callback_query_handler(lambda c: c.data == 'delete_all_events', state=AdminStates.admin_panel)
async def delete_all_events(callback_query: types.CallbackQuery):
    _, events, _, _ = load_data()
    events["events"] = []
    save_data(events, 'events.json')
    
    await callback_query.message.edit_text(
        "✅ Все события удалены!",
        reply_markup=get_admin_menu()
    )

@dp.callback_query_handler(lambda c: c.data == 'show_events_admin', state=AdminStates.admin_panel)
async def show_events_admin(callback_query: types.CallbackQuery):
    _, events, _, _ = load_data()
    
    if events.get("events"):
        events_text = "📋 Текущие события:\n\n"
        for i, event in enumerate(events["events"], 1):
            events_text += f"{i}. {event['title']} - {event['date']}\n"
    else:
        events_text = "📋 Нет добавленных событий."
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="admin_events"))
    
    await callback_query.message.edit_text(events_text, reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data == 'admin_teachers', state=AdminStates.admin_panel)
async def admin_teachers_menu(callback_query: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("➕ Добавить учителя", callback_data="add_teacher"),
        InlineKeyboardButton("❌ Удалить всех учителей", callback_data="delete_all_teachers"),
        InlineKeyboardButton("📋 Список учителей", callback_data="show_teachers_admin"),
        InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin")
    )
    
    await callback_query.message.edit_text(
        "👨‍🏫 Управление списком учителей\n\n"
        "Выберите действие:",
        reply_markup=keyboard
    )

@dp.callback_query_handler(lambda c: c.data == 'add_teacher', state=AdminStates.admin_panel)
async def start_add_teacher(callback_query: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("❌ Отмена", callback_data="admin_teachers"))
    
    await callback_query.message.edit_text(
        "👨‍🏫 Введите имя и фамилию учителя:",
        reply_markup=keyboard
    )
    await AdminStates.waiting_teacher_name.set()

@dp.message_handler(state=AdminStates.waiting_teacher_name)
async def process_teacher_name(message: types.Message, state: FSMContext):
    await state.update_data(teacher_name=message.text)
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("❌ Отмена", callback_data="admin_teachers"))
    
    await message.answer(
        "📚 Введите предмет(ы) учителя:",
        reply_markup=keyboard
    )
    await AdminStates.waiting_teacher_subject.set()

@dp.message_handler(state=AdminStates.waiting_teacher_subject)
async def process_teacher_subject(message: types.Message, state: FSMContext):
    data = await state.get_data()
    name = data.get('teacher_name')
    subject = message.text
    
    _, _, teachers, _ = load_data()
    
    teacher_id = str(len(teachers["teachers"]) + 1)
    
    new_teacher = {
        "id": teacher_id,
        "name": name,
        "subject": subject
    }
    
    teachers["teachers"].append(new_teacher)
    save_data(teachers, 'teachers.json')
    
    await message.answer(
        f"✅ Учитель {name} успешно добавлен!",
        reply_markup=get_admin_menu()
    )
    await AdminStates.admin_panel.set()

@dp.callback_query_handler(lambda c: c.data == 'delete_all_teachers', state=AdminStates.admin_panel)
async def delete_all_teachers(callback_query: types.CallbackQuery):
    _, _, teachers, _ = load_data()
    teachers["teachers"] = []
    save_data(teachers, 'teachers.json')
    
    await callback_query.message.edit_text(
        "✅ Список учителей очищен!",
        reply_markup=get_admin_menu()
    )

@dp.callback_query_handler(lambda c: c.data == 'show_teachers_admin', state=AdminStates.admin_panel)
async def show_teachers_admin(callback_query: types.CallbackQuery):
    _, _, teachers, _ = load_data()
    
    if teachers.get("teachers"):
        teachers_text = "📋 Список учителей:\n\n"
        for teacher in teachers["teachers"]:
            teachers_text += f"👨‍🏫 {teacher['name']} - {teacher['subject']}\n"
    else:
        teachers_text = "📋 Список учителей пуст."
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="admin_teachers"))
    
    await callback_query.message.edit_text(teachers_text, reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data == 'admin_reviews', state=AdminStates.admin_panel)
async def show_reviews_admin(callback_query: types.CallbackQuery):
    _, _, _, reviews = load_data()
    
    if reviews.get("reviews"):
        reviews_text = "📊 Анонимные отзывы:\n\n"
        for i, review in enumerate(reviews["reviews"], 1):
            reviews_text += f"📝 Отзыв #{i}\n"
            reviews_text += f"👨‍🏫 Учитель: {review['teacher_name']}\n"
            reviews_text += f"📅 Дата: {review['date']}\n"
            reviews_text += f"💬 Отзыв: {review['text']}\n"
            reviews_text += "➖➖➖➖➖➖➖➖➖➖\n"
    else:
        reviews_text = "📊 Пока нет анонимных отзывов."
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin"))
    
    await callback_query.message.edit_text(reviews_text, reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data == 'back_to_admin', state='*')
async def back_to_admin_panel(callback_query: types.CallbackQuery):
    await AdminStates.admin_panel.set()
    await callback_query.message.edit_text(
        "Админ-панель:",
        reply_markup=get_admin_menu()
    )

@dp.callback_query_handler(lambda c: c.data == 'exit_admin', state='*')
async def exit_admin(callback_query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await callback_query.message.edit_text(
        "✅ Вы вышли из админ-панели.",
        reply_markup=get_main_menu()
    )

# Создание начальных файлов
def create_initial_files():
    if not os.path.exists('schedule.json'):
        save_data({}, 'schedule.json')
    
    if not os.path.exists('events.json'):
        save_data({"events": []}, 'events.json')
    
    if not os.path.exists('teachers.json'):
        save_data({"teachers": []}, 'teachers.json')
    
    if not os.path.exists('anonymous_reviews.json'):
        save_data({"reviews": []}, 'anonymous_reviews.json')

# Webhook для Render
async def on_startup(dp):
    create_initial_files()
    logging.info("Бот запущен!")
    
    # Для Render с вебхуками
    webhook_url = os.getenv('WEBHOOK_URL')
    if webhook_url:
        await bot.set_webhook(webhook_url)
        logging.info(f"Webhook установлен на {webhook_url}")

async def on_shutdown(dp):
    logging.info("Бот останавливается...")
    await bot.delete_webhook()
    await dp.storage.close()
    await dp.storage.wait_closed()

if __name__ == '__main__':
    create_initial_files()
    
    # Проверяем, используем ли мы вебхуки (Render) или поллинг (локально)
    webhook_url = os.getenv('WEBHOOK_URL')
    
    if webhook_url:
        # Запуск с вебхуками для Render
        from aiogram.utils.executor import start_webhook
        start_webhook(
            dispatcher=dp,
            webhook_path='/webhook',
            on_startup=on_startup,
            on_shutdown=on_shutdown,
            skip_updates=True,
            host='0.0.0.0',
            port=int(os.getenv('PORT', 8080))
        )
    else:
        # Локальный запуск с поллингом
        executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
