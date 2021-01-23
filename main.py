import zipfile
import os
import re
import random
import logging
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext



ZIP_FILE_NAME = "quiz-questions.zip"
TELEGRAM_TOKEN = ""
TELEGRAM_CHAT_ID = ""

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

files_in_archive = get_file_names_from_archive()

current_quiz = get_text_from_archive()

def get_question_and_answer(current_quiz):
    question_blocks = current_quiz.split('\n\n')
    print(question_blocks)
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

get_question_and_answer(current_quiz)

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
    } for question, answer in get_question_and_answer(current_quiz)
]

for item in questions_and_answers:
    print(item)

def echo(update: Update, context: CallbackContext) -> None:
    """Echo the user message."""
    update.message.reply_text(update.message.text)

def add_menu(bot):
    custom_keyboard = [['Новый вопрос', 'Сдаться'], 
                   ['Мой счет']]
    reply_markup = ReplyKeyboardMarkup(custom_keyboard)
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, 
                 text="Привет я бот для викторины", 
                 reply_markup=reply_markup)

def main():
    load_dotenv()
    global TELEGRAM_TOKEN
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    global TELEGRAM_CHAT_ID
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

    bot_message_format="%(asctime)s:[%(name)s]%(filename)s.%(funcName)s:%(levelname)s:%(message)s"
    formatter = logging.Formatter(bot_message_format)
    logger.setLevel(logging.WARNING)

    updater = Updater(token=TELEGRAM_TOKEN)
    dispatcher = updater.dispatcher

    telegram_handler = TelegramLogsHandler(dispatcher.bot, TELEGRAM_CHAT_ID)
    telegram_handler.setFormatter(formatter)
    logger.addHandler(telegram_handler)

    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))
    add_menu(updater.bot)
    updater.start_polling()
    updater.idle()

if __name__=="__main__":
    main()