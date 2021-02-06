import zipfile
import os
import re
import random
import logging
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext,  ConversationHandler
import redis
from enum import Enum
from general import TelegramLogsHandler



ZIP_FILE_NAME = "quiz-questions.zip"
TELEGRAM_TOKEN = ""
TELEGRAM_CHAT_ID = ""
REDIS_HOST = ""
REDIS_PORT = ""
REDIS_PASS = ""
REDIS_DB = ""
Marker = Enum('Marker', 'CHOOSING TYPING_ANSWER')

logger = logging.getLogger(__name__)



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


def handle_new_question_request(update: Update, context: CallbackContext) -> int:
    user_id = update.message['from_user']['id']
    context.user_data['account'] = 0
    try:
        stage = next(context.user_data['quiz'])
        update.message.reply_text(stage['question'])
        context.user_data['redis'].set(user_id, stage['answer'])
    except StopIteration:
        update.message.reply_text('Викторина закончена')
        return ConversationHandler.END
    return Marker.TYPING_ANSWER


def handle_solution_attempt(update: Update, context: CallbackContext) -> int:
    user_id = update.message['from_user']['id']
    answer = context.user_data['redis'].get(user_id).decode('UTF-8')
    if answer.split(".")[0] == update.message.text:
        context.user_data['account'] += context.user_data['account']
        update.message.reply_text("Правильно! Поздравляю! Для следующего вопроса нажми 'Новый вопрос'.")
        return Marker.CHOOSING
    update.message.reply_text("Неправильно… Попробуешь ещё раз?")
    return Marker.TYPING_ANSWER


def handle_surrender_choose(update: Update, context: CallbackContext) -> int:
    user_id = update.message['from_user']['id']
    answer = context.user_data['redis'].get(user_id).decode('UTF-8')
    update.message.reply_text(f'Ответ: {answer}')
    update.message.reply_text("Новый вопрос")
    try:
        stage = next(context.user_data['quiz'])
        update.message.reply_text(stage['question'])
        context.user_data['redis'].set(user_id, stage['answer'])
    except StopIteration:
        update.message.reply_text('Викторина закончена')
        return ConversationHandler.END
    return Marker.TYPING_ANSWER


def handle_get_account(update: Update, context: CallbackContext) -> None:
    account = context.user_data['account']
    update.message.reply_text(f"счет {account}")


def handle_get_default_event(update: Update, context: CallbackContext) -> None:
    pass


def start_quiz(update: Update, context: CallbackContext) -> int:
    try:
        context.user_data['redis']
    except KeyError:
        context.user_data['redis'] = redis.Redis(host=REDIS_HOST,port=int(REDIS_PORT), password=REDIS_PASS, db=0)
    context.user_data['quiz'] = iter(get_current_quiz())
    context.user_data['account'] = 0 
    custom_keyboard = [['Новый вопрос', 'Сдаться'], 
                   ['Мой счет', 'Закончить игру']]

    reply_markup = ReplyKeyboardMarkup(custom_keyboard)
    update.message.reply_text(text="Начинаем викторину", reply_markup=reply_markup)
    return Marker.CHOOSING


def clear_menu(bot) -> None:
    reply_markup = ReplyKeyboardRemove()
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text='Привет.', reply_markup=reply_markup)


def handle_close_game(update: Update, context: CallbackContext) -> int:
    reply_markup = ReplyKeyboardRemove()
    update.message.reply_text("Игра окончена.", reply_markup=reply_markup)
    return ConversationHandler.END


def put_error(update: Update, context: CallbackContext) -> None:
    """Log Errors caused by Updates."""
    logger.warning(f'Update {update} caused error {context.error}')


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
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('quiz', start_quiz, pass_user_data=True)],

        states={ 
            Marker.CHOOSING: [
                    MessageHandler(
                        Filters.regex('^(Новый вопрос)$'), handle_new_question_request, pass_user_data=True),
                    MessageHandler(
                        Filters.regex('^(Сдаться|Мой счет)$'), handle_get_default_event, pass_user_data=True),
                    MessageHandler(
                        Filters.regex('^(Закончить игру)$'), handle_close_game, pass_user_data=True),
                       ],
            Marker.TYPING_ANSWER: [                    
                    MessageHandler(
                        Filters.regex('^(Сдаться)$'), handle_surrender_choose, pass_user_data=True),
                    MessageHandler(
                        Filters.regex('^(Мой счет)$'), handle_get_account, pass_user_data=True),
                    MessageHandler(
                        Filters.regex('^(Новый вопрос)$'), handle_get_default_event, pass_user_data=True),
                    MessageHandler(
                        Filters.regex('^(Закончить игру)$'), handle_close_game, pass_user_data=True),
                    MessageHandler(
                        Filters.text, handle_solution_attempt, pass_user_data=True),
                            ],
        },
        fallbacks=[MessageHandler(Filters.regex('^Done$'), handle_close_game)]
    )
    clear_menu(dispatcher.bot)
    dispatcher.add_handler(conv_handler)
    dispatcher.add_error_handler(put_error)
    updater.start_polling()
    updater.idle()

if __name__=="__main__":
    main()