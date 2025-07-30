import os
import re
import logging
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    CallbackContext,
)

# Загрузка переменных окружения
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Создаем папку для данных, если ее нет
os.makedirs("data", exist_ok=True)

# Состояния разговора
(
    MAIN_MENU,
    SURVEY_NAME,
    SURVEY_EMAIL,
    SURVEY_PHONE,
    MAIN_PROGRAM_NOW,
    CURRENT_LEVEL,
    CURRENT_TRAINER,
    STUDIED_BEFORE,
    STUDIED_LEVELS,
    DESIRED_TRAINER,
    PLAN_STUDY,
    PLANNED_LEVEL,
    PLANNED_TRAINER,
    SPECIALIZATIONS_NOW,
    SPEC_LIST_NOW,
    SPEC_TRAINER_NOW,
    SPECIALIZATIONS_BEFORE,
    SPEC_LIST_BEFORE,
    SPEC_TRAINER_BEFORE,
    EVENTS,
    EVENTS_OTHER,
    FEEDBACK,
    REVIEW_COURSE,
    REVIEW_TRAINER,
    REVIEW_RATING,
    REVIEW_RESULTS,
    PRIVACY_POLICY,
    NOTIFICATION_CONSENT,
    REVIEW_PUBLICATION_CONSENT,
) = range(29) 

# Текстовые блоки для сообщений
BLOCKS = {
    "spec_trainer_now": "13. Кто Ваш тренер?",
    "events": "🔹 Блок 4. Дополнительные мероприятия\n\n15. В каких дополнительных мероприятиях центра Вы участвовали?",
    "spec_list_before": "16. Выберите специализацию(и), которые Вы проходили:\n(Выберите одну или несколько специализаций, затем 'Завершить выбор')",
    "spec_trainer_before": "17. Кто был Ваш тренер?",
    "events_other": "Укажите, пожалуйста, в каких мероприятиях Вы участвовали:",
    "feedback": "🔹 Блок 5. Пожелания\n\n18. Что больше всего Вам понравилось? Что можно улучшить?",
    "next_event": "Выберите следующее мероприятие или нажмите 'Не участвовал'"
}

RESPONSES = {
    "survey_success": "✅ Спасибо, что прошли опрос! До встречи на занятиях!",
    "survey_error": "Спасибо за опрос! Возникли временные трудности с сохранением результатов. Администратор уже уведомлен.",
    "cancel": "Действие отменено. Выберите пункт меню:",  # <- Здесь была пропущена запятая!
    "privacy_policy_required": "Для продолжения необходимо подтвердить согласие с Политикой конфиденциальности.",
    "notification_consent_info": "Вы можете в любое время отозвать согласие на уведомления, обратившись в наш центр.",
}

# Хранение данных пользователя
user_data = {}

# Клавиатуры
main_menu_keyboard = ReplyKeyboardMarkup(
    [
        ["Пройти опрос"],
        ["Ближайшие мероприятия", "Контакты"],
        ["Оплата услуг центра"],
        ["Основная программа обучения в Центре"],
        ["Дополнительные курсы и программы Центра"],
        ["Оставить отзыв"],
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

yes_no_keyboard = ReplyKeyboardMarkup(
    [["Да", "Нет"]],
    resize_keyboard=True,
    one_time_keyboard=True
)

levels_keyboard = ReplyKeyboardMarkup(
    [["1 ступень"], ["2 ступень"], ["3 ступень"], ["Завершить выбор"]],
    resize_keyboard=True,
    one_time_keyboard=True
)

spec_keyboard = ReplyKeyboardMarkup(
    [
        ["Гештальт-подход в терапии психосоматических расстройств"],
        ["Семейная гештальт-терапия"],
        ["Гештальт-подход в сексологии"],
        ["Гештальт-терапия травматического опыта"],
        ["Арт-гештальт: творческая терапия"],
        ["Гештальт-терапия в работе с детьми и подростками"],
        ["Групповая гештальт-терапия"],
        ["Гештальт-терапия в клинической практике"],
        ["Завершить выбор"]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

events_keyboard = ReplyKeyboardMarkup(
    [
        ["Летняя интенсивная программа"],
        ["Онлайн конференция"],
        ["День открытых дверей"],
        ["Другое"],
        ["Не участвовал"]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

rating_keyboard = ReplyKeyboardMarkup(
    [[str(i) for i in range(1, 6)], [str(i) for i in range(6, 11)]],
    resize_keyboard=True,
    one_time_keyboard=True
)

def sanitize_filename(name):
    """Очистка имени файла от недопустимых символов"""
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def save_to_excel(data, filename="data/SurveyResults.xlsx"):
    """Сохранение результатов в Excel с улучшенной обработкой"""
    try:
        # Подготовка данных для сохранения
        prepared_data = {}
        
        # Копируем все поля из data
        for key, value in data.items():
            if isinstance(value, list):
                prepared_data[key] = ", ".join(value)
            else:
                prepared_data[key] = value
        
        # Добавляем дату заполнения
        prepared_data["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        df = pd.DataFrame([prepared_data])
        
        # Проверяем существование файла
        if os.path.exists(filename):
            try:
                existing_df = pd.read_excel(filename)
                updated_df = pd.concat([existing_df, df], ignore_index=True)
            except Exception as e:
                logger.error(f"Error reading existing Excel file: {e}")
                # Если не удалось прочитать существующий файл, создаем новый
                updated_df = df
        else:
            updated_df = df
        
        # Сохраняем файл
        updated_df.to_excel(filename, index=False)
        logger.info(f"Data successfully saved to {filename}")
        return True
    except Exception as e:
        logger.error(f"Error saving to Excel: {e}")
        return False

async def start(update: Update, context: CallbackContext) -> int:
    """Начало разговора и главное меню"""
    user = update.message.from_user
    user_data[user.id] = {
        "telegram_id": user.id, 
        "username": user.username,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    await update.message.reply_text(
        "Добро пожаловать в Центр практической психологии 'Феномены'! "
        "Выберите нужный пункт меню:",
        reply_markup=main_menu_keyboard
    )
    return MAIN_MENU

async def main_menu(update: Update, context: CallbackContext) -> int:
    """Обработка выбора в главном меню"""
    user = update.message.from_user
    choice = update.message.text
    
    if choice == "Пройти опрос":
        await update.message.reply_text(
            "🔹 Блок 1. Общие данные\n\n1. Как Вас зовут?\n"
            "(Введите имя и фамилию)",
            reply_markup=ReplyKeyboardRemove()
        )
        return SURVEY_NAME
    
    elif choice == "Ближайшие мероприятия":
        await update.message.reply_text(
            "Ближайшие мероприятия центра:\nhttps://phenomeny.by/intensiv_2025",
            reply_markup=main_menu_keyboard
        )
        return MAIN_MENU
    
    elif choice == "Контакты":
        await update.message.reply_text(
            "ООО 'Центр практической психологии 'Феномены'\n"
            "Юридический адрес: 220114, г. Минск, ул. Макаенка, 12е, пом. 298.\n"
            "Телефон: +375291292429",
            reply_markup=main_menu_keyboard
        )
        return MAIN_MENU
    
    elif choice == "Оплата услуг центра":
        await update.message.reply_text(
            "Оплата услуг центра:\nhttps://phenomeny.by/payment",
            reply_markup=main_menu_keyboard
        )
        return MAIN_MENU
    
    elif choice == "Основная программа обучения в Центре":
        await update.message.reply_text(
            "Основная программа обучения:\nhttps://phenomeny.by/education",
            reply_markup=main_menu_keyboard
        )
        return MAIN_MENU
    
    elif choice == "Дополнительные курсы и программы Центра":
        await update.message.reply_text(
            "Дополнительные курсы и программы:\nhttps://phenomeny.by/specializations",
            reply_markup=main_menu_keyboard
        )
        return MAIN_MENU
    
    elif choice == "Оставить отзыв":
        await update.message.reply_text(
            "Спасибо за желание оставить отзыв!\n\n"
            "1. Какой курс вы проходили и почему выбрали именно его?",
            reply_markup=ReplyKeyboardRemove()
        )
        return REVIEW_COURSE
    
    else:
        await update.message.reply_text(
            "Пожалуйста, выберите один из вариантов меню.",
            reply_markup=main_menu_keyboard
        )
        return MAIN_MENU

async def survey_name(update: Update, context: CallbackContext) -> int:
    """Получение имени пользователя"""
    user = update.message.from_user
    user_data[user.id]["name"] = update.message.text
    
    await update.message.reply_text(
        "2. Укажите, пожалуйста Ваш email:",
        reply_markup=ReplyKeyboardRemove()
    )
    return SURVEY_EMAIL

async def survey_email(update: Update, context: CallbackContext) -> int:
    """Получение email пользователя"""
    user = update.message.from_user
    user_data[user.id]["email"] = update.message.text
    
    await update.message.reply_text(
        "3. Укажите, пожалуйста ваш номер телефона:",
        reply_markup=ReplyKeyboardRemove()
    )
    return SURVEY_PHONE

async def survey_phone(update: Update, context: CallbackContext) -> int:
    """Получение телефона пользователя"""
    user = update.message.from_user
    user_data[user.id]["phone"] = update.message.text
    
    await update.message.reply_text(
        "🔹 Блок 2. Обучение по основной программе\n\n"
        "4. Вы сейчас обучаетесь у нас по основной программе (1–3 ступень)?",
        reply_markup=yes_no_keyboard
    )
    return MAIN_PROGRAM_NOW

async def main_program_now(update: Update, context: CallbackContext) -> int:
    """Обучается ли пользователь по основной программе"""
    user = update.message.from_user
    answer = update.message.text.lower()
    user_data[user.id]["main_program_now"] = answer
    
    if answer == "да":
        await update.message.reply_text(
            "5. На какой ступени Вы обучаетесь?\n"
            "(Выберите одну или несколько ступеней, затем 'Завершить выбор')",
            reply_markup=levels_keyboard
        )
        return CURRENT_LEVEL
    else:
        await update.message.reply_text(
            "6. Ранее Вы обучались в нашем центре по основной программе?",
            reply_markup=yes_no_keyboard
        )
        return STUDIED_BEFORE

async def current_level(update: Update, context: CallbackContext) -> int:
    """Текущая ступень обучения"""
    user = update.message.from_user
    text = update.message.text
    
    if "current_level" not in user_data[user.id]:
        user_data[user.id]["current_level"] = []
    
    if text == "Завершить выбор":
        if not user_data[user.id]["current_level"]:
            await update.message.reply_text(
                "Пожалуйста, выберите хотя бы одну ступень.",
                reply_markup=levels_keyboard
            )
            return CURRENT_LEVEL
        
        await update.message.reply_text(
            "6. Кто Ваш тренер?",
            reply_markup=ReplyKeyboardRemove()
        )
        return CURRENT_TRAINER
    else:
        if text not in user_data[user.id]["current_level"]:
            user_data[user.id]["current_level"].append(text)
        
        await update.message.reply_text(
            "Выберите следующую ступень или нажмите 'Завершить выбор'",
            reply_markup=levels_keyboard
        )
        return CURRENT_LEVEL

async def current_trainer(update: Update, context: CallbackContext) -> int:
    """Текущий тренер"""
    user = update.message.from_user
    user_data[user.id]["current_trainer"] = update.message.text
    
    await update.message.reply_text(
        "🔹 Блок 3. Обучение по специализациям\n\n"
        "11. Вы обучаетесь в нашем центре по специализациям?",
        reply_markup=yes_no_keyboard
    )
    return SPECIALIZATIONS_NOW

async def studied_before(update: Update, context: CallbackContext) -> int:
    """Обучался ли ранее"""
    user = update.message.from_user
    answer = update.message.text.lower()
    user_data[user.id]["studied_before"] = answer
    
    if answer == "да":
        await update.message.reply_text(
            "На какой ступени Вы обучались?\n"
            "(Выберите одну или несколько ступеней, затем 'Завершить выбор')",
            reply_markup=levels_keyboard
        )
        return STUDIED_LEVELS
    else:
        await update.message.reply_text(
            "8. Планируете ли начать обучение по основной программе?",
            reply_markup=yes_no_keyboard
        )
        return PLAN_STUDY

async def studied_levels(update: Update, context: CallbackContext) -> int:
    """Пройденные ступени обучения"""
    user = update.message.from_user
    text = update.message.text
    
    if "studied_levels" not in user_data[user.id]:
        user_data[user.id]["studied_levels"] = []
    
    if text == "Завершить выбор":
        if not user_data[user.id]["studied_levels"]:
            await update.message.reply_text(
                "Пожалуйста, выберите хотя бы одну ступень.",
                reply_markup=levels_keyboard
            )
            return STUDIED_LEVELS
        
        await update.message.reply_text(
            "7. К какому тренеру Вы хотели бы попасть?",
            reply_markup=ReplyKeyboardRemove()
        )
        return DESIRED_TRAINER
    else:
        if text not in user_data[user.id]["studied_levels"]:
            user_data[user.id]["studied_levels"].append(text)
        
        await update.message.reply_text(
            "Выберите следующую ступень или нажмите 'Завершить выбор'",
            reply_markup=levels_keyboard
        )
        return STUDIED_LEVELS

async def desired_trainer(update: Update, context: CallbackContext) -> int:
    """Желаемый тренер"""
    user = update.message.from_user
    user_data[user.id]["desired_trainer"] = update.message.text
    
    await update.message.reply_text(
        "🔹 Блок 3. Обучение по специализациям\n\n"
        "11. Вы обучаетесь в нашем центре по специализациям?",
        reply_markup=yes_no_keyboard
    )
    return SPECIALIZATIONS_NOW

async def plan_study(update: Update, context: CallbackContext) -> int:
    """Планирует ли обучение"""
    user = update.message.from_user
    answer = update.message.text.lower()
    user_data[user.id]["plan_study"] = answer
    
    if answer == "да":
        await update.message.reply_text(
            "9. Какую ступень планируете начать?",
            reply_markup=levels_keyboard
        )
        return PLANNED_LEVEL
    else:
        await update.message.reply_text(
            "🔹 Блок 3. Обучение по специализациям\n\n"
            "11. Вы обучаетесь в нашем центре по специализациям?",
            reply_markup=yes_no_keyboard
        )
        return SPECIALIZATIONS_NOW

async def planned_level(update: Update, context: CallbackContext) -> int:
    """Планируемая ступень"""
    user = update.message.from_user
    user_data[user.id]["planned_level"] = update.message.text
    
    await update.message.reply_text(
        "10. К какому тренеру Вы хотели бы попасть?",
        reply_markup=ReplyKeyboardRemove()
    )
    return PLANNED_TRAINER

async def planned_trainer(update: Update, context: CallbackContext) -> int:
    """Желаемый тренер для планируемого обучения"""
    user = update.message.from_user
    user_data[user.id]["planned_trainer"] = update.message.text
    
    await update.message.reply_text(
        "🔹 Блок 3. Обучение по специализациям\n\n"
        "11. Вы обучаетесь в нашем центре по специализациям?",
        reply_markup=yes_no_keyboard
    )
    return SPECIALIZATIONS_NOW

async def specializations_now(update: Update, context: CallbackContext) -> int:
    """Обучается ли по специализациям сейчас"""
    user = update.message.from_user
    answer = update.message.text.lower()
    user_data[user.id]["specializations_now"] = answer
    
    if answer == "да":
        await update.message.reply_text(
            "12. Выберите специализацию(и):\n"
            "(Выберите одну или несколько специализаций, затем 'Завершить выбор')",
            reply_markup=spec_keyboard
        )
        return SPEC_LIST_NOW
    else:
        await update.message.reply_text(
            "14. Проходили ли Вы ранее обучение по специализациям в нашем центре?",
            reply_markup=yes_no_keyboard
        )
        return SPECIALIZATIONS_BEFORE

async def spec_list_now(update: Update, context: CallbackContext) -> int:
    """Список текущих специализаций"""
    user = update.message.from_user
    text = update.message.text
    
    if "spec_list_now" not in user_data[user.id]:
        user_data[user.id]["spec_list_now"] = []
    
    if text == "Завершить выбор":
        if not user_data[user.id]["spec_list_now"]:
            await update.message.reply_text(
                "Пожалуйста, выберите хотя бы одну специализацию.",
                reply_markup=spec_keyboard
            )
            return SPEC_LIST_NOW
        
        await update.message.reply_text(BLOCKS["spec_trainer_now"], reply_markup=ReplyKeyboardRemove())
        return SPEC_TRAINER_NOW
    else:
        if text not in user_data[user.id]["spec_list_now"]:
            user_data[user.id]["spec_list_now"].append(text)
        
        await update.message.reply_text("Выберите следующую специализацию или нажмите 'Завершить выбор'",
                                      reply_markup=spec_keyboard)
        return SPEC_LIST_NOW

async def spec_trainer_now(update: Update, context: CallbackContext) -> int:
    """Тренер по специализации"""
    user = update.message.from_user
    user_data[user.id]["spec_trainer_now"] = update.message.text
    await update.message.reply_text(BLOCKS["events"], reply_markup=events_keyboard)
    return EVENTS

async def specializations_before(update: Update, context: CallbackContext) -> int:
    """Обучался ли по специализациям ранее"""
    user = update.message.from_user
    answer = update.message.text.lower()
    user_data[user.id]["specializations_before"] = answer
    
    if answer == "да":
        await update.message.reply_text(BLOCKS["spec_list_before"], reply_markup=spec_keyboard)
        return SPEC_LIST_BEFORE
    else:
        await update.message.reply_text(BLOCKS["events"], reply_markup=events_keyboard)
        return EVENTS

async def spec_list_before(update: Update, context: CallbackContext) -> int:
    """Список пройденных специализаций"""
    user = update.message.from_user
    text = update.message.text
    
    if "spec_list_before" not in user_data[user.id]:
        user_data[user.id]["spec_list_before"] = []
    
    if text == "Завершить выбор":
        if not user_data[user.id]["spec_list_before"]:
            await update.message.reply_text("Пожалуйста, выберите хотя бы одну специализацию.",
                                          reply_markup=spec_keyboard)
            return SPEC_LIST_BEFORE
        
        await update.message.reply_text(BLOCKS["spec_trainer_before"], reply_markup=ReplyKeyboardRemove())
        return SPEC_TRAINER_BEFORE
    else:
        if text not in user_data[user.id]["spec_list_before"]:
            user_data[user.id]["spec_list_before"].append(text)
        
        await update.message.reply_text("Выберите следующую специализацию или нажмите 'Завершить выбор'",
                                      reply_markup=spec_keyboard)
        return SPEC_LIST_BEFORE

async def spec_trainer_before(update: Update, context: CallbackContext) -> int:
    """Тренер по специализации ранее"""
    user = update.message.from_user
    user_data[user.id]["spec_trainer_before"] = update.message.text
    await update.message.reply_text(BLOCKS["events"], reply_markup=events_keyboard)
    return EVENTS

async def events(update: Update, context: CallbackContext) -> int:
    """Участие в мероприятиях"""
    user = update.message.from_user
    text = update.message.text
    
    if "events" not in user_data[user.id]:
        user_data[user.id]["events"] = []
    
    if text == "Другое":
        await update.message.reply_text(BLOCKS["events_other"], reply_markup=ReplyKeyboardRemove())
        return EVENTS_OTHER
    elif text == "Не участвовал":
        user_data[user.id]["events"] = ["Не участвовал"]
        await update.message.reply_text(BLOCKS["feedback"], reply_markup=ReplyKeyboardRemove())
        return FEEDBACK
    else:
        user_data[user.id]["events"].append(text)
        await update.message.reply_text(BLOCKS["next_event"], reply_markup=events_keyboard)
        return EVENTS

async def events_other(update: Update, context: CallbackContext) -> int:
    """Другие мероприятия"""
    user = update.message.from_user
    user_data[user.id]["events"].append(f"Другое: {update.message.text}")
    await update.message.reply_text(BLOCKS["feedback"], reply_markup=ReplyKeyboardRemove())
    return FEEDBACK

async def feedback(update: Update, context: CallbackContext) -> int:
    """Обратная связь"""
    user = update.message.from_user
    user_data[user.id]["feedback"] = update.message.text
    
    # Добавляем клавиатуру для согласия с политикой конфиденциальности
    privacy_keyboard = ReplyKeyboardMarkup(
        [["✅ Подтверждаю", "❌ Не подтверждаю"]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await update.message.reply_text(
        "Пожалуйста, подтвердите:\n\n"
        "Я подтверждаю, что ознакомлен(а) с Политикой конфиденциальности сайта, "
        "даю согласие на сбор и обработку моих персональных данных в соответствии с "
        "Законом Республики Беларусь от 7 мая 2021 года № 99-З «О защите персональных данных».\n"
        "Подробнее: https://phenomeny.by/privacy_policy",
        reply_markup=privacy_keyboard
    )
    return PRIVACY_POLICY

async def privacy_policy(update: Update, context: CallbackContext) -> int:
    """Обработка согласия с политикой конфиденциальности"""
    user = update.message.from_user
    choice = update.message.text
    
    if choice == "✅ Подтверждаю":
        user_data[user.id]["privacy_policy_consent"] = True
    else:
        user_data[user.id]["privacy_policy_consent"] = False
    
    # Добавляем клавиатуру для согласия на уведомления
    notification_keyboard = ReplyKeyboardMarkup(
        [["✅ Согласен(-на)", "❌ Не согласен(-на)"]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await update.message.reply_text(
        "Я согласен(-на) на получение уведомлений по электронной почте и SMS, "
        "связанных с участием в обучающих курсах.",
        reply_markup=notification_keyboard
    )
    return NOTIFICATION_CONSENT

async def notification_consent(update: Update, context: CallbackContext) -> int:
    """Обработка согласия на уведомления"""
    user = update.message.from_user
    choice = update.message.text
    
    if choice == "✅ Согласен(-на)":
        user_data[user.id]["notification_consent"] = True
    else:
        user_data[user.id]["notification_consent"] = False
    
    # Сохраняем данные
    filename = f"data/SurveyResults_{datetime.now().strftime('%Y%m')}.xlsx"
    if save_to_excel(user_data[user.id], filename):
        await update.message.reply_text(RESPONSES["survey_success"], reply_markup=main_menu_keyboard)
    else:
        await update.message.reply_text(RESPONSES["survey_error"], reply_markup=main_menu_keyboard)
    
    return MAIN_MENU

async def review_course(update: Update, context: CallbackContext) -> int:
    """Какой курс проходил пользователь"""
    user = update.message.from_user
    
    # Инициализируем структуру для отзыва, если ее еще нет
    if "review" not in user_data[user.id]:
        user_data[user.id]["review"] = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "telegram_id": user.id,
            "telegram_username": user.username
        }
    
    user_data[user.id]["review"]["course"] = update.message.text
    
    await update.message.reply_text(
        "2. Кто был вашим тренером?",
        reply_markup=ReplyKeyboardRemove()
    )
    return REVIEW_TRAINER

async def review_trainer(update: Update, context: CallbackContext) -> int:
    """Тренер пользователя"""
    user = update.message.from_user
    user_data[user.id]["review"]["trainer"] = update.message.text
    
    await update.message.reply_text(
        "3. Оцените уровень преподавателей и их подход (по шкале от 1 до 10):",
        reply_markup=rating_keyboard
    )
    return REVIEW_RATING

async def review_rating(update: Update, context: CallbackContext) -> int:
    """Оценка пользователя"""
    user = update.message.from_user
    rating = update.message.text
    
    if not rating.isdigit() or int(rating) < 1 or int(rating) > 10:
        await update.message.reply_text(
            "Пожалуйста, введите число от 1 до 10:",
            reply_markup=rating_keyboard
        )
        return REVIEW_RATING
    
    user_data[user.id]["review"]["rating"] = int(rating)
    
    await update.message.reply_text(
        "4. Поделитесь своими эмоциями и личными результатами от курса:",
        reply_markup=ReplyKeyboardRemove()
    )
    return REVIEW_RESULTS

async def review_results(update: Update, context: CallbackContext) -> int:
    """Результаты от курса"""
    user = update.message.from_user
    user_data[user.id]["review"]["results"] = update.message.text
    
    # Добавляем клавиатуру для согласия на публикацию отзыва
    publication_keyboard = ReplyKeyboardMarkup(
        [["✅ Согласен(-на)", "❌ Не согласен(-на)"]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await update.message.reply_text(
        "Я согласен(-на) на размещение моего отзыва на сайте https://phenomeny.by/",
        reply_markup=publication_keyboard
    )
    return REVIEW_PUBLICATION_CONSENT

async def review_publication_consent(update: Update, context: CallbackContext) -> int:
    """Обработка согласия на публикацию отзыва"""
    user = update.message.from_user
    choice = update.message.text
    
    if choice == "✅ Согласен(-на)":
        user_data[user.id]["review"]["publication_consent"] = True
    else:
        user_data[user.id]["review"]["publication_consent"] = False
    
    # Сохранение отзыва
    filename = f"data/Reviews_{datetime.now().strftime('%Y%m')}.xlsx"
    if save_to_excel(user_data[user.id]["review"], filename):
        await update.message.reply_text(
            "✅ Спасибо за оставленный отзыв! До встречи на занятиях!",
            reply_markup=main_menu_keyboard
        )
    else:
        await update.message.reply_text(
            "Спасибо за отзыв! Возникли временные трудности с сохранением. "
            "Администратор уже уведомлен.",
            reply_markup=main_menu_keyboard
        )
    
    # Очищаем данные отзыва
    if "review" in user_data[user.id]:
        del user_data[user.id]["review"]
    
    return MAIN_MENU

async def cancel(update: Update, context: CallbackContext) -> int:
    """Отмена текущего действия"""
    user = update.message.from_user
    logger.info(f"User {user.id} canceled the conversation.")
    
    await update.message.reply_text(
        RESPONSES["cancel"],
        reply_markup=main_menu_keyboard
    )
    
    if user.id in user_data:
        del user_data[user.id]
    
    return MAIN_MENU

def main() -> None:
    """Запуск бота"""
    application = Application.builder().token(TOKEN).build()
    
    # Обработчик главного меню
    application.add_handler(CommandHandler("start", start))
    
    # Обработчик опроса
    survey_conv = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^Пройти опрос$"), main_menu)],
    states={
        SURVEY_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, survey_name)],
        SURVEY_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, survey_email)],
        SURVEY_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, survey_phone)],
        MAIN_PROGRAM_NOW: [MessageHandler(filters.TEXT & ~filters.COMMAND, main_program_now)],
        CURRENT_LEVEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, current_level)],
        CURRENT_TRAINER: [MessageHandler(filters.TEXT & ~filters.COMMAND, current_trainer)],
        STUDIED_BEFORE: [MessageHandler(filters.TEXT & ~filters.COMMAND, studied_before)],
        STUDIED_LEVELS: [MessageHandler(filters.TEXT & ~filters.COMMAND, studied_levels)],
        DESIRED_TRAINER: [MessageHandler(filters.TEXT & ~filters.COMMAND, desired_trainer)],
        PLAN_STUDY: [MessageHandler(filters.TEXT & ~filters.COMMAND, plan_study)],
        PLANNED_LEVEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, planned_level)],
        PLANNED_TRAINER: [MessageHandler(filters.TEXT & ~filters.COMMAND, planned_trainer)],
        SPECIALIZATIONS_NOW: [MessageHandler(filters.TEXT & ~filters.COMMAND, specializations_now)],
        SPEC_LIST_NOW: [MessageHandler(filters.TEXT & ~filters.COMMAND, spec_list_now)],
        SPEC_TRAINER_NOW: [MessageHandler(filters.TEXT & ~filters.COMMAND, spec_trainer_now)],
        SPECIALIZATIONS_BEFORE: [MessageHandler(filters.TEXT & ~filters.COMMAND, specializations_before)],
        SPEC_LIST_BEFORE: [MessageHandler(filters.TEXT & ~filters.COMMAND, spec_list_before)],
        SPEC_TRAINER_BEFORE: [MessageHandler(filters.TEXT & ~filters.COMMAND, spec_trainer_before)],
        EVENTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, events)],
        EVENTS_OTHER: [MessageHandler(filters.TEXT & ~filters.COMMAND, events_other)],
        FEEDBACK: [MessageHandler(filters.TEXT & ~filters.COMMAND, feedback)],
        PRIVACY_POLICY: [MessageHandler(filters.TEXT & ~filters.COMMAND, privacy_policy)],
        NOTIFICATION_CONSENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, notification_consent)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    map_to_parent={MAIN_MENU: MAIN_MENU}
)
    
    # Обработчик отзывов
    review_conv = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^Оставить отзыв$"), main_menu)],
    states={
        REVIEW_COURSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, review_course)],
        REVIEW_TRAINER: [MessageHandler(filters.TEXT & ~filters.COMMAND, review_trainer)],
        REVIEW_RATING: [MessageHandler(filters.TEXT & ~filters.COMMAND, review_rating)],
        REVIEW_RESULTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, review_results)],
        REVIEW_PUBLICATION_CONSENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, review_publication_consent)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    map_to_parent={MAIN_MENU: MAIN_MENU}
)
    
    # Добавление обработчиков
    application.add_handler(survey_conv)
    application.add_handler(review_conv)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu))
    
    # Запуск бота
    application.run_polling()

if __name__ == "__main__":
    main()