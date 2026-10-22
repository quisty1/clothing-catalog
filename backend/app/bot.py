from io import BytesIO
from aiogram import Router
from aiogram.methods import SendMessage
from aiogram.types import (Message, InlineKeyboardMarkup,
                           InlineKeyboardButton, WebAppInfo)
from app.policy import decide_message
from app.services import create_product, lock_key
from app.models import AdminPrompt

MAX_PHOTO_BYTES = 10 * 1024 * 1024
INSTRUCTIONS = 'Отправьте одну фотографию и название товара в подписи к ней (от 1 до 255 символов). Альбомы не поддерживаются.'


class InvalidPhoto(ValueError):
    pass


class LimitedBuffer(BytesIO):
    def write(self, data):
        if self.tell() + len(data) > MAX_PHOTO_BYTES:
            raise InvalidPhoto('Фотография должна быть не больше 10 МБ.')
        return super().write(data)


def create_router():
    router = Router()

    @router.message()
    async def handle(message: Message, bot, settings, db, storage):
        if message.chat.type != 'private' or message.from_user is None:
            return None
        is_admin = message.from_user.id in settings.administrators
        prompt = None
        if is_admin:
            await lock_key(db, f'admin:{bot.id}:{message.from_user.id}')
            prompt = await db.get(AdminPrompt, (bot.id, message.from_user.id))
        action = decide_message(text=message.text, caption=message.caption,
                                has_photo=bool(message.photo), is_album=bool(message.media_group_id),
                                is_admin=is_admin, awaiting_photo=bool(prompt and prompt.awaiting_photo))
        markup = None
        if action.kind == 'welcome':
            if prompt:
                prompt.awaiting_photo = False
            rows = [[InlineKeyboardButton(text='Открыть каталог', web_app=WebAppInfo(url=settings.public_url))]]
            if is_admin:
                rows.append([InlineKeyboardButton(text='Создать товар', callback_data='create_product')])
            markup = InlineKeyboardMarkup(inline_keyboard=rows)
            reply = 'У меня есть товар'
        elif action.kind in {'instructions', 'invalid'}:
            reply = INSTRUCTIONS
            if action.kind == 'instructions':
                if prompt is None:
                    prompt = AdminPrompt(bot_id=bot.id,user_id=message.from_user.id,awaiting_photo=True)
                    db.add(prompt)
                else:
                    prompt.awaiting_photo = True
        elif action.kind == 'forbidden':
            reply = 'Добавление товаров доступно только администратору.'
        else:
            photo = max(message.photo, key=lambda item: item.width * item.height)

            async def load_photo():
                if photo.file_size and photo.file_size > MAX_PHOTO_BYTES:
                    raise InvalidPhoto('Фотография должна быть не больше 10 МБ.')
                buffer = LimitedBuffer()
                await bot.download(photo, destination=buffer, timeout=20)
                data = buffer.getvalue()
                if not data.startswith(b'\xff\xd8'):
                    raise InvalidPhoto('Отправьте изображение как фотографию, а не как документ.')
                return data

            try:
                product = await create_product(db, storage, title=action.title,
                    source_key=f'tg:{bot.id}:{message.chat.id}:{message.message_id}', load_photo=load_photo)
            except InvalidPhoto as error:
                reply = str(error)
            else:
                reply = f'Товар «{product.name}» добавлен в каталог.'
                if prompt:
                    prompt.awaiting_photo = False
        return SendMessage(chat_id=message.chat.id, text=reply, reply_markup=markup, parse_mode=None)

    @router.callback_query()
    async def create_prompt(callback, bot, settings, db):
        from aiogram.methods import AnswerCallbackQuery
        if callback.data != 'create_product':
            return AnswerCallbackQuery(callback_query_id=callback.id)
        if callback.from_user.id not in settings.administrators:
            return AnswerCallbackQuery(callback_query_id=callback.id,
                text='Добавление товаров доступно только администратору.', show_alert=True)
        await lock_key(db, f'admin:{bot.id}:{callback.from_user.id}')
        prompt=await db.get(AdminPrompt,(bot.id,callback.from_user.id))
        if prompt is None:
            db.add(AdminPrompt(bot_id=bot.id,user_id=callback.from_user.id,awaiting_photo=True))
        else:
            prompt.awaiting_photo=True
        # Pending intent is in PostgreSQL, never an in-process FSM.
        return AnswerCallbackQuery(callback_query_id=callback.id, text=INSTRUCTIONS, show_alert=True)

    return router
