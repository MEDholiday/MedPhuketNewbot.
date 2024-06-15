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


async def fetch_messages_from_chats_n(chat_links, keywords, hours):
    # Create a new Pyrogram client
    client = Client("my_session")

    # Log in to the client
    async with client:

        parsed_messages = []
        # Get current time and time "hours" ago
        now = datetime.datetime.now(pytz.utc)
        time_ago = now - datetime.timedelta(hours=hours)

        # Iterate over each chat link and fetch messages containing keywords
        for link in chat_links:
            try:
                # Extract the chat username or ID from the link
                chat_identifier = link.split("/")[-1]

                # Fetch the chat information
                try:
                    chat = await client.get_chat(chat_identifier)
                except:
                    print(f"Skipping chat link: {link}. User is not a member of the chat.")
                    continue
                chat_id = chat.id

                # Fetch messages containing the keywords in the chat
                for keyword in keywords:
                    async for message in client.search_messages(chat_id, keyword):
                        # Check if the message date is within the given range
                        if time_ago <= message.date <= now:
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

                # Sleep for 2 seconds between iterations
                await asyncio.sleep(2)

            except Exception as e:
                print(f"Error processing chat link: {link}")
                print(f"Error message: {str(e)}")
                print()
                continue
    return parsed_messages


async def schedule_fetch_and_forward():
    chat_id = '6885411740'
    while True:
        # Get the current time in the user's timezone (you can adjust the timezone as needed)
        tz = pytz.timezone('Asia/Bangkok')  # Replace 'Your_Timezone_Here' with the desired timezone
        current_time = datetime.datetime.now(tz)

        # Define the times for message fetching and forwarding (adjust the times as needed)
        fetch_times = [datetime.time(8, 0), datetime.time(13, 0), datetime.time(16, 0), datetime.time(18, 0)]

        if current_time.time() in fetch_times:
            try:
                # Call the fetch_messages_from_chats function using await
                parsed_messages = await fetch_messages_from_chats(chat_links, keywords)

                # Send the result to the user
                await send_message_to_user(chat_id, parsed_messages)
            except Exception as e:
                print(f"Error occurred during scheduled fetch and forward: {str(e)}")

        # Sleep for 1 minute to avoid continuous checking
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
        types.KeyboardButton(text="/fetch_messages"),
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
        await bot.send_message(message.from_user.id, "Request in progress. Please wait")

        # Call the fetch_messages_from_chats function using await
        parsed_messages = await fetch_messages_from_chats(chat_links, keywords)
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
        await bot.send_message(chat_id, "Request in progress. Please wait")

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
