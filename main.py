# import logging
import time

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from config import token, chat_id
from pyrogram import Client
import asyncio
import datetime
import itertools
import aiogram.utils.executor
import pytz
from keywords import keywords
from chat_links import chat_links


# Set up logging
# logging.basicConfig(level=logging.DEBUG)

# Create the bot and dispatcher objects
bot = Bot(token=token)
dp = Dispatcher(bot, storage=MemoryStorage())


async def get_author_info(client, user_id):
    try:
        user = await client.get_users(user_id)
        return f"{user.first_name} {user.last_name} ({user.username})", f"https://t.me/{user.username}"
    except:
        return None, None


async def fetch_messages_from_chats_today(chat_links, keywords, max_retries=5, retry_delay=2):
    # Create a new Pyrogram client
    client = Client("my_session")

    # Log in to the client
    async with client:
        parsed_messages = []
        # Initialize start time

        # Get current date
        current_date = datetime.date.today()

        # Iterate over each chat link and fetch messages containing keywords
        for link in chat_links:
            try:
                # Extract the chat username or ID from the link
                chat_identifier = link.split("/")[-1]

                # Fetch the chat information
                try:
                    chat = await client.get_chat(chat_identifier)
                except Exception:
                    print(f"Skipping chat link: {link}. User is not a member of the chat.")
                    continue
                chat_id = chat.id

                # Fetch messages containing the keywords in the chat
                for keyword in keywords:
                    retry_count = 0
                    while retry_count < max_retries:
                        try:
                            async for message in client.search_messages(chat_id, keyword):
                                # Rest of the code to process each message goes here

                                # Write messages to the worksheet
                                # for message in messages:
                                # Check if the message is from today
                                if message.date.date() == current_date:
                                    date_time = message.date.strftime("%Y-%m-%d %H:%M:%S")

                                    # Get author info
                                    author_name, author_link = await get_author_info(client, message.from_user.id)

                                    # Получение ссылки на сообщение
                                    message_link = message.link

                                    parsed_message = {
                                        "chat": chat.title,
                                        "link": message_link,
                                        "author": author_name,
                                        "author_link": author_link,
                                        "date_time": date_time,
                                        "keywords_used": [keyword],
                                        "message_text": message.text,
                                    }
                                    # Проверяем, что текст сообщения не пустой
                                    if parsed_message["message_text"]:
                                        parsed_messages.append(parsed_message)
                            break  # Break out of the retry loop if successful
                        except Exception as db_err:
                            if 'database is locked' in str(db_err):
                                retry_count += 1
                                print(f"Database is locked, retrying {retry_count}/{max_retries}...")
                                await asyncio.sleep(retry_delay)
                            else:
                                raise
                # Sleep for 2 seconds between iterations
                await asyncio.sleep(2)

            except Exception as e:
                print(f"Error processing chat link: {link}")
                print(f"Error message: {str(e)}")
                print()
                continue
    return parsed_messages


async def fetch_messages_from_chats(chat_links, keywords, retry_attempts=5, retry_delay=2):
    # Create a new Pyrogram client
    client = Client("my_session")

    # Log in to the client
    async with client:
        parsed_messages = []

        # Get current time in UTC and time 12 hours ago
        now = datetime.datetime.now(pytz.utc)
        twelve_hours_ago = now - datetime.timedelta(hours=12)

        print(f"Current UTC time: {now}")
        print(f"Time 12 hours ago: {twelve_hours_ago}")

        # Iterate over each chat link and fetch messages containing keywords
        for link in chat_links:
            try:
                # Extract the chat username or ID from the link
                chat_identifier = link.split("/")[-1]

                # Fetch the chat information
                for attempt in range(retry_attempts):
                    try:
                        chat = await client.get_chat(chat_identifier)
                        break
                    except Exception as e:
                        if 'database is locked' in str(e):
                            print(f"Database is locked, retrying in {retry_delay} seconds...")
                            time.sleep(retry_delay)
                        else:
                            raise e
                else:
                    print(f"Skipping chat link: {link}. User is not a member of the chat.")
                    continue

                chat_id = chat.id

                print(f"Processing chat: {chat.title}")

                # Fetch messages containing the keywords in the chat
                for keyword in keywords:
                    async for message in client.search_messages(chat_id, keyword):
                        # Check if the message date is within the last 12 hours
                        if twelve_hours_ago <= message.date <= now:
                            print(f"Found message with keyword '{keyword}' in chat '{chat.title}'")
                            date_time = message.date.strftime("%Y-%m-%d %H:%M:%S")

                            # Get author info
                            author_name, author_link = await get_author_info(client, message.from_user.id)

                            parsed_message = {
                                "chat": chat.title,
                                "link": link,
                                "author": author_name,
                                "author_link": author_link,
                                "date_time": date_time,
                                "keywords_used": [keyword],
                                "message_text": message.text,
                            }
                            # Проверяем, что текст сообщения не пустой
                            if parsed_message["message_text"]:
                                parsed_messages.append(parsed_message)
                            else:
                                print(f"Message text is empty, skipping message.")
                        else:
                            print(f"Message with keyword '{keyword}' is out of the 12-hour range.")

                # Sleep for 2 seconds between iterations
                await asyncio.sleep(2)

            except Exception as e:
                print(f"Error processing chat link: {link}")
                print(f"Error message: {str(e)}")
                print()
                continue
    return parsed_messages


# Основная функция для извлечения сообщений из чатов за последние n часов
async def fetch_messages_from_chats_n(chat_links, keywords, hours, user_timezone='UTC', retry_attempts=5, retry_delay=2):
    # Создание нового клиента Pyrogram
    client = Client("my_session")

    # Вход в систему с использованием клиента
    async with client:
        parsed_messages = []

        # Учет временной зоны пользователя
        user_tz = pytz.timezone(user_timezone)
        now = datetime.datetime.now(pytz.utc).astimezone(user_tz)
        # Добавление 8 часов к текущему времени пользователя
        now = now + datetime.timedelta(hours=8)
        time_ago = now - datetime.timedelta(hours=hours)

        print(f"Current time (User TZ): {now}")
        print(f"Time {hours} hours ago (User TZ): {time_ago}")

        # Итерация по каждой ссылке чата и извлечение сообщений, содержащих ключевые слова
        for link in chat_links:
            for attempt in range(retry_attempts):
                try:
                    # Извлечение имени пользователя или ID чата из ссылки
                    chat_identifier = link.split("/")[-1]

                    # Получение информации о чате
                    try:
                        chat = await client.get_chat(chat_identifier)
                    except Exception as e:
                        if 'database is locked' in str(e):
                            print(
                                f"База данных заблокирована, повторная попытка через {retry_delay} секунд... (Попытка {attempt + 1}/{retry_attempts})")
                            await asyncio.sleep(retry_delay)
                            continue
                        else:
                            print(f"Пропуск ссылки на чат: {link}. Пользователь не является участником чата.")
                            break  # Выход из цикла повторных попыток для этой ссылки чата
                    chat_id = chat.id

                    # Поиск сообщений, содержащих ключевые слова в чате
                    for keyword in keywords:
                        async for message in client.search_messages(chat_id, keyword):
                            # Проверка, является ли дата сообщения в указанном диапазоне
                            message_date = message.date.astimezone(pytz.utc)  # Преобразование в offset-aware дату в UTC

                            if time_ago <= message_date <= now:
                                date_time = message_date.strftime("%Y-%m-%d %H:%M:%S")

                                # Получение информации об авторе
                                author_name, author_link = await get_author_info(client, message.from_user.id)

                                # Получение ссылки на сообщение
                                message_link = message.link

                                parsed_message = {
                                    "chat": chat.title,
                                    "link": message_link,
                                    "author": author_name,
                                    "author_link": author_link,
                                    "date_time": date_time,
                                    "keywords_used": [keyword],
                                    "message_text": message.text,
                                }
                                # Проверка, что текст сообщения не пустой
                                if parsed_message["message_text"]:
                                    parsed_messages.append(parsed_message)

                    # Ожидание 2 секунды между итерациями
                    await asyncio.sleep(2)

                except Exception as e:
                    if 'database is locked' in str(e):
                        print(
                            f"База данных заблокирована, повторная попытка через {retry_delay} секунд... (Попытка {attempt + 1}/{retry_attempts})")
                        await asyncio.sleep(retry_delay)
                    else:
                        print(f"Ошибка при обработке ссылки на чат: {link}")
                        print(f"Сообщение об ошибке: {str(e)}")
                    continue
                break  # Выход из цикла повторных попыток в случае успеха
            else:
                print(
                    f"Не удалось обработать ссылку на чат {link} после {retry_attempts} попыток из-за блокировки базы данных.")
    return parsed_messages


async def schedule_fetch_and_forward():
    chat_id = '6885411740'
    while True:
        # Получение текущего времени в часовом поясе пользователя (при необходимости можно изменить часовой пояс)
        tz = pytz.timezone('Asia/Bangkok')  # Замените 'Asia/Bangkok' на нужный часовой пояс
        current_time = datetime.datetime.now(tz)

        # Определение времени для извлечения и пересылки сообщений (при необходимости измените время)
        fetch_times = [datetime.time(8, 0), datetime.time(13, 0), datetime.time(16, 0), datetime.time(18, 0)]

        if current_time.time() in fetch_times:
            try:
                # Вызов функции fetch_messages_from_chats с использованием await
                parsed_messages = await fetch_messages_from_chats(chat_links, keywords)

                # Отправка результата пользователю
                await send_message_to_user(chat_id, parsed_messages)
            except Exception as e:
                print(f"Ошибка во время запланированного извлечения и пересылки: {str(e)}")

        # Ожидание 1 минуту для предотвращения непрерывной проверки
        await asyncio.sleep(60)


# Function to send messages to the user using the bot
async def send_message_to_user(chat_id, messages):
    if not messages:
        await bot.send_message(chat_id, "No messages found.")
        return

    message_chunk_size = 4096  # Maximum message size limit for Telegram

    message_to_send = "Messages found:\n\n"
    for message in messages:
        # Форматирование текста ключевых слов
        formatted_keywords = ", ".join([f"<b>{kw}</b>" for kw in message.get("keywords_used", [])])

        message_info = (
            f"Chat: {message['chat']}\n"
            f"Chat_link: {message['link']}\n"
            f"Author: {message['author']} ({message['author_link']})\n"
            f"Date: {message['date_time']}\n"
            f"Message: {message['message_text']}\n"
            f"Keywords: {formatted_keywords}\n\n"
        )

        # Check if the chunk size exceeds the limit and split the message if necessary
        if len(message_to_send) + len(message_info) <= message_chunk_size:
            message_to_send += message_info
        else:
            # Send the current chunk
            await bot.send_message(chat_id, message_to_send, parse_mode="HTML")

            # Start a new chunk
            message_to_send = message_info

    # Send any remaining messages in the last chunk
    await bot.send_message(chat_id, message_to_send, parse_mode="HTML")


# Handler for the /start command
@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    keyboard_markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    buttons = [
        # types.KeyboardButton(text="/fetch_messages"),
        types.KeyboardButton(text="/fetch_messages_today"),
        types.KeyboardButton(text="Last 1 hour"),
        types.KeyboardButton(text="Last 2 hours"),
        types.KeyboardButton(text="Last 3 hours"),
        types.KeyboardButton(text="Last 6 hours"),
        types.KeyboardButton(text="Last 12 hours"),
        types.KeyboardButton(text="Last 24 hours"),
        types.KeyboardButton(text="Help"),
    ]
    keyboard_markup.add(*buttons)
    welcome_message = "Welcome to the telegram bot. For help, press the Help command."
    await bot.send_message(message.from_user.id, welcome_message, reply_markup=keyboard_markup)


# Handler for the /fetch_messages command
@dp.message_handler(commands=['fetch_messages'])
async def fetch_messages_command(message: types.Message):
    try:
        # Add the "Request in progress. Please wait" message here
        await bot.send_message(message.from_user.id, "Request in progress. Please wait...")

        # Call the fetch_messages_from_chats function using await
        parsed_messages = await fetch_messages_from_chats(chat_links, keywords)
        # Send the result to the user
        await send_message_to_user(message.from_user.id, parsed_messages)
    except Exception as e:
        await bot.send_message(message.from_user.id, f"Error occurred: {str(e)}")


# Handler for the fetch_messages_today command
@dp.message_handler(commands=['fetch_messages_today'])
async def fetch_messages_today_command(message: types.Message):
    try:
        # Add the "Request in progress. Please wait" message here
        await bot.send_message(message.from_user.id, "Request in progress. Please wait...")

        # Call the fetch_messages_from_chats function using await
        parsed_messages = await fetch_messages_from_chats_today(chat_links, keywords)
        # Send the result to the user
        await send_message_to_user(message.from_user.id, parsed_messages)
    except Exception as e:
        await bot.send_message(message.from_user.id, f"Error occurred: {str(e)}")


@dp.message_handler(lambda message: message.text.startswith("Last "))
async def fetch_messages_by_time_command(message: types.Message):
    time_range_map = {
        "Last 1 hour": 1,
        "Last 2 hours": 2,
        "Last 3 hours": 3,
        "Last 6 hours": 6,
        "Last 12 hours": 12,
        "Last 24 hours": 24,
    }
    time_range = time_range_map.get(message.text, 12)
    await fetch_and_send_messages(message.from_user.id, time_range)


async def fetch_and_send_messages(chat_id, hours):
    try:
        # Add the "Request in progress. Please wait" message here
        await bot.send_message(chat_id, "Request in progress. Please wait...")

        # Call the fetch_messages_from_chats function using await
        parsed_messages = await fetch_messages_from_chats_n(chat_links, keywords, hours)
        # Send the result to the user
        await send_message_to_user(chat_id, parsed_messages)
    except Exception as e:
        await bot.send_message(chat_id, f"Error occurred: {str(e)}")


# Handler for the "Help" button
@dp.message_handler(lambda message: message.text == "Help")
async def help(message: types.Message):
    await message.answer("Help using the bot:\n"
                         "1. /start command - start the bot\n"
                         "2. '/fetch_messages' button - receive messages from chats\n"
                         "3. 'Help' button - displaying help information")


@dp.message_handler()
async def handle_unknown_command(message: types.Message):
    await message.answer("The bot does not know this command. See the help team")


if __name__ == '__main__':
    # Start the scheduling task
    asyncio.ensure_future(schedule_fetch_and_forward())

    # Start the bot
    from aiogram import executor
    executor.start_polling(dp)
