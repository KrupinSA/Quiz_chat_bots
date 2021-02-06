import random
import logging
import vk_api as vk
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id
from dotenv import load_dotenv
import os
from general import TelegramLogsHandler


def echo(event, vk_api):
    vk_api.messages.send(
        user_id=event.user_id,
        message=f'{event.text} {event.user_id}',
        random_id=random.randint(1,1000)
    )


def create_keyboard():
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button('Новый вопрос', color=VkKeyboardColor.SECONDARY)
    keyboard.add_button('Сдаться', color=VkKeyboardColor.POSITIVE)

    keyboard.add_line()
    keyboard.add_button('Мой счет', color=VkKeyboardColor.NEGATIVE)
    keyboard.add_button('Закончить счет', color=VkKeyboardColor.PRIMARY)
    return keyboard


def main():
    load_dotenv()
    vk_id = os.getenv("VK_ID")
    vk_session = vk.VkApi(token=vk_id)
    
    vk_api = vk_session.get_api()
    vk_api.messages.send(
        peer_id=605732974,
        random_id=get_random_id(),
        keyboard=keyboard.get_keyboard(),
        message='Пример клавиатуры'
    )
    
    longpoll = VkLongPoll(vk_session)
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            echo(event, vk_api)

if __name__ == "__main__":
    main()