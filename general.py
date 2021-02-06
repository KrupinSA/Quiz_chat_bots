import logging
import zipfile
import random

class TelegramLogsHandler(logging.Handler):

    def __init__(self, tg_bot, chat_id):
        super().__init__()
        self.chat_id = chat_id
        self.tg_bot = tg_bot

    def emit(self, record):
        log_entry = self.format(record)
        self.tg_bot.send_message(chat_id=self.chat_id, text=log_entry)


def get_file_names_from_archive(zipname):
    with zipfile.ZipFile(zipname, 'r') as zip_file:
        return [a_file.filename for a_file in zip_file.filelist if a_file.filename.endswith('txt')]


def get_text_from_archive(zipname, file_name_in_zip=None):    
    if not file_name_in_zip:
        files_in_archive = get_file_names_from_archive(zipname)
        file_name_in_zip = random.choice(files_in_archive)
    with zipfile.ZipFile(zipname, 'r') as zip_file:
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


def get_current_quiz(zipname) -> list:
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
        } for question, answer in get_question_and_answer(get_text_from_archive(zipname))
    ]
    return questions_and_answers