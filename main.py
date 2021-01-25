import zipfile
import os
import re
import random
import logging
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler
import redis



ZIP_FILE_NAME = "quiz-questions.zip"
TELEGRAM_TOKEN = ""
TELEGRAM_CHAT_ID = ""
REDIS_HOST = ""
REDIS_PORT = ""
REDIS_PASS = ""
REDIS_DB = ""

logger = logging.getLogger(__name__)

class TelegramLogsHandler(logging.Handler):

    def __init__(self, tg_bot, chat_id):
        super().__init__()
        self.chat_id = chat_id
        self.tg_bot = tg_bot

    def emit(self, record):
        log_entry = self.format(record)
        self.tg_bot.send_message(chat_id=self.chat_id, text=log_entry)

def get_file_names_from_archive():
    with zipfile.ZipFile(ZIP_FILE_NAME, 'r') as zip_file:
        return [a_file.filename for a_file in zip_file.filelist if a_file.filename.endswith('txt')]

def get_text_from_archive(file_name_in_zip=None):    
    if not file_name_in_zip:
        files_in_archive = get_file_names_from_archive()
        file_name_in_zip = random.choice(files_in_archive)
    with zipfile.ZipFile(ZIP_FILE_NAME, 'r') as zip_file:
        return zip_file.read(file_name_in_zip).decode('KOI8-R')

def get_question_and_answer(quiz_text):
    question_blocks = quiz_text.split('\n\n')
    quiz_iterator = iter(question_blocks)
    try:
        while True:
            item_value = next(quiz_iterator)
            if item_value.startswith('Вопрос '):
                question = item_value.split(':', 1)[1]
                item_value = next(quiz_iterator)
                if item_value.startswith('Ответ:'):
                    answer = item_value.split(':', 1)[1]
                    yield question, answer
    except StopIteration:
        return

def get_current_quiz() -> list:
    """
    questions_and_answers = [
        {
            "question": "This example question ...",
            "answer": "This example answer ..."
        },
        {
            ...
        }
    ]
    """
    questions_and_answers = [
        {
            'question': question,
            'answer': answer
        } for question, answer in get_question_and_answer(get_text_from_archive())
    ]
    return questions_and_answers

def send_message() -> None:
    def send_wrapped_message(update: Update, context: CallbackContext) -> None:
        user_id = update.message['from_user']['id']
        answer = send_wrapped_message.redis_db.get(user_id).decode('UTF-8')
        if answer.split(".")[0] == update.message.text:
            update.message.reply_text("Правильно! Поздравляю! Для следующего вопроса нажми 'Новый вопрос'.")
        elif update.message.text == "Новый вопрос":
            if send_wrapped_message.current_quiz:
                try:
                    stage = next(send_wrapped_message.current_quiz)
                    update.message.reply_text(stage['question'])
                    send_wrapped_message.redis_db.set(user_id, stage['answer'])
                except StopIteration:
                    update.message.reply_text('Викторина закончена')
        elif update.message.text == "Новая викторина":
            send_wrapped_message.current_quiz = iter(get_current_quiz()) 
            try:
                stage = next(send_wrapped_message.current_quiz)
                update.message.reply_text(stage['question'])
            except StopIteration:
                update.message.reply_text('Викторина закончена')
        else: 
            update.message.reply_text("Неправильно… Попробуешь ещё раз?")
    send_wrapped_message.redis_db = redis.Redis(host=REDIS_HOST,port=int(REDIS_PORT), password=REDIS_PASS, db=0)
    send_wrapped_message.current_quiz = iter(get_current_quiz()) 
    return send_wrapped_message

def add_menu(update: Update, context: CallbackContext) -> None:
    custom_keyboard = [['Новый вопрос', 'Сдаться'], 
                   ['Мой счет']]

    reply_markup = ReplyKeyboardMarkup(custom_keyboard)
    update.message.reply_text(text="Начинаем викторину", reply_markup=reply_markup)


def clear_menu(bot) -> None:
    reply_markup = ReplyKeyboardRemove()
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text='Привет.', reply_markup=reply_markup)

def main():
    load_dotenv()
    global TELEGRAM_TOKEN
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    global TELEGRAM_CHAT_ID
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
    global REDIS_HOST
    REDIS_HOST = os.getenv("REDIS_HOST")
    global REDIS_PORT
    REDIS_PORT = os.getenv('REDIS_PORT')
    global REDIS_DB
    REDIS_DB = os.getenv('REDIS_DB')
    global REDIS_PASS
    REDIS_PASS = os.getenv('REDIS_PASS')

    bot_message_format="%(asctime)s:[%(name)s]%(filename)s.%(funcName)s:%(levelname)s:%(message)s"
    formatter = logging.Formatter(bot_message_format)
    logger.setLevel(logging.WARNING)

    updater = Updater(token=TELEGRAM_TOKEN)
    dispatcher = updater.dispatcher

    telegram_handler = TelegramLogsHandler(dispatcher.bot, TELEGRAM_CHAT_ID)
    telegram_handler.setFormatter(formatter)
    logger.addHandler(telegram_handler)

    dispatcher.add_handler(CommandHandler('quiz', add_menu))
    messages = send_message()
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, messages))
    clear_menu(dispatcher.bot)
    updater.start_polling()
    updater.idle()

if __name__=="__main__":
    main()