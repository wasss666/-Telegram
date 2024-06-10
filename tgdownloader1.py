import asyncio
from telethon import TelegramClient, errors
from telethon.errors import SessionPasswordNeededError, AuthRestartError
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import DocumentAttributeSticker
from telegram import Bot, Update
from telegram.ext import CommandHandler, MessageHandler, Filters, CallbackContext, Updater
import aiohttp
import io

# Ваші API ID та HASH
api_id = api_id
api_hash = 'api_hash'
phone_number = 'number'

# Токен бота та ID адміністратора
bot_token = 'token'
admin_id = admin_id

# Створити клієнт Telethon
client = TelegramClient('session_name', api_id, api_hash)

# Створити клієнт бота
bot = Bot(token=bot_token)

# Глобальні змінні для зберігання введених ID
source_chat_id = None
user_id = None

async def send_admin_message(text):
    async with aiohttp.ClientSession() as session:
        data = aiohttp.FormData()
        data.add_field('chat_id', str(admin_id))
        data.add_field('text', text)
        await session.post(f'https://api.telegram.org/bot{bot_token}/sendMessage', data=data)

async def forward_media_from_chat(chat_id, user_id):
    offset_id = 0
    limit = 100
    total_files = 0
    total_messages = 0

    try:
        peer = await client.get_entity(chat_id)
    except ValueError:
        await send_admin_message("Invalid chat ID")
        return
    except errors.RPCError as e:
        await send_admin_message(f"RPC error: {e}")
        return
    except Exception as e:
        await send_admin_message(f"Unexpected error: {e}")
        return

    async def process_message(message):
        nonlocal total_files, total_messages
        try:
            if message.sender_id == user_id:
                total_messages += 1
                tasks = []
                if message.photo:
                    tasks.append(forward_photo(message))
                elif message.document:
                    if any(attr for attr in message.document.attributes if isinstance(attr, DocumentAttributeSticker)):
                        return
                    if message.document.mime_type.startswith("video") and message.document.mime_type != "video/webm":
                        tasks.append(forward_video(message))
                    elif message.document.mime_type.startswith("image") and not message.document.mime_type.startswith("image/webp"):
                        tasks.append(forward_document(message))
                elif message.video:
                    if message.video.duration >= 5:
                        tasks.append(forward_video(message))
                elif message.video_note:
                    if message.video_note.duration >= 5:
                        tasks.append(forward_video_note(message))
                await asyncio.gather(*tasks)
                total_files += len(tasks)
                if tasks:
                    await send_admin_message(f"Найдено медіа-файли у повідомленні {total_messages}: {len(tasks)} файлів пересилається")
        except Exception as e:
            await send_admin_message(f'Error processing message: {e}')

    while True:
        try:
            history = await client(GetHistoryRequest(
                peer=peer,
                offset_id=offset_id,
                offset_date=None,
                add_offset=0,
                limit=limit,
                max_id=0,
                min_id=0,
                hash=0
            ))

            if not history.messages:
                break

            await asyncio.gather(*[process_message(message) for message in history.messages])

            offset_id = history.messages[-1].id
            await send_admin_message(f"Оброблено {len(history.messages)} повідомлень, шукаю далі...")

        except errors.RPCError as e:
            await send_admin_message(f"RPC error while fetching history: {e}")
            break
        except Exception as e:
            await send_admin_message(f"Unexpected error while fetching history: {e}")
            break

    await send_admin_message(f"Знайдено та відправлено {total_files} файлів від користувача {user_id} в чаті {chat_id}")

async def forward_photo(message):
    try:
        file = io.BytesIO()
        await client.download_media(message.photo, file)
        file.seek(0)
        async with aiohttp.ClientSession() as session:
            data = aiohttp.FormData()
            data.add_field('chat_id', str(admin_id))
            data.add_field('photo', file, filename='photo.jpg')
            async with session.post(f'https://api.telegram.org/bot{bot_token}/sendPhoto', data=data) as resp:
                if resp.status != 200:
                    await send_admin_message(f'Failed to forward photo: {await resp.text()}')
    except Exception as e:
        await send_admin_message(f'Failed to forward photo: {e}')

async def forward_document(message):
    try:
        file = io.BytesIO()
        await client.download_media(message.document, file)
        file.seek(0)
        async with aiohttp.ClientSession() as session:
            data = aiohttp.FormData()
            data.add_field('chat_id', str(admin_id))
            data.add_field('document', file, filename='document')
            async with session.post(f'https://api.telegram.org/bot{bot_token}/sendDocument', data=data) as resp:
                if resp.status != 200:
                    await send_admin_message(f'Failed to forward document: {await resp.text()}')
    except Exception as e:
        await send_admin_message(f'Failed to forward document: {e}')

async def forward_video(message):
    try:
        file = io.BytesIO()
        await client.download_media(message.video, file)
        file.seek(0)
        async with aiohttp.ClientSession() as session:
            data = aiohttp.FormData()
            data.add_field('chat_id', str(admin_id))
            data.add_field('video', file, filename='video.mp4')
            async with session.post(f'https://api.telegram.org/bot{bot_token}/sendVideo', data=data) as resp:
                if resp.status != 200:
                    await send_admin_message(f'Failed to forward video: {await resp.text()}')
    except Exception as e:
        await send_admin_message(f'Failed to forward video: {e}')

async def forward_video_note(message):
    try:
        file = io.BytesIO()
        await client.download_media(message.video_note, file)
        file.seek(0)
        async with aiohttp.ClientSession() as session:
            data = aiohttp.FormData()
            data.add_field('chat_id', str(admin_id))
            data.add_field('video', file, filename='video_note.mp4')
            async with session.post(f'https://api.telegram.org/bot{bot_token}/sendVideo', data=data) as resp:
                if resp.status != 200:
                    await send_admin_message(f'Failed to forward video note: {await resp.text()}')
    except Exception as e:
        await send_admin_message(f'Failed to forward video note: {e}')

async def start_client():
    try:
        print("Starting client...")
        await send_admin_message("Starting client...")
        await client.start(phone_number)
        print("Client started successfully!")
        await send_admin_message("Client started successfully!")
    except AuthRestartError:
        print("Telegram is having internal issues. Restarting authorization process.")
        await send_admin_message("Telegram is having internal issues. Restarting authorization process.")
        return False
    except SessionPasswordNeededError:
        password = input("Two-step verification is enabled. Please enter your password: ")
        await client.sign_in(password=password)
    except Exception as e:
        print(f"Failed to start client: {e}")
        await send_admin_message(f"Failed to start client: {e}")
        return False
    return True

def start(update: Update, context: CallbackContext) -> None:
    if update.message.chat_id == admin_id:
        update.message.reply_text('Вітаю! Введіть ID чату:')
        context.user_data['expecting_chat_id'] = True
        context.user_data['expecting_user_id'] = False
        return

def handle_message(update: Update, context: CallbackContext) -> None:
    if update.message.chat_id == admin_id:
        if context.user_data.get('expecting_chat_id'):
            global source_chat_id
            source_chat_id = int(update.message.text)
            update.message.reply_text('Тепер введіть ID користувача:')
            context.user_data['expecting_chat_id'] = False
            context.user_data['expecting_user_id'] = True
        elif context.user_data.get('expecting_user_id'):
            global user_id
            user_id = int(update.message.text)
            update.message.reply_text('Дякую! Починаю пересилання медіа.')
            context.user_data['expecting_user_id'] = False
            asyncio.run(main())
        return

async def main():
    if not await start_client():
        return
    await forward_media_from_chat(source_chat_id, user_id)
    await send_admin_message("Bot has finished forwarding media.")
    print("Bot has finished forwarding media.")

def main_bot():
    updater = Updater(bot_token)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main_bot()