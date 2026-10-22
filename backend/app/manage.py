"""Explicit one-shot tasks; never configure Telegram on every replica startup."""
import argparse
import asyncio
import json
from pathlib import Path
from aiogram import Bot
from aiogram.types import BotCommand, MenuButtonWebApp, WebAppInfo
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.config import Settings
from app.services import create_product
from app.storage import ObjectStorage

DEMO = [('coat','Пальто прямого кроя'),('shirt','Классическая рубашка'),
        ('sweater','Свитер с круглым вырезом'),('trousers','Брюки со стрелками'),
        ('dress','Платье без рукавов'),('jacket','Укороченная куртка')]


async def run(command):
    settings = Settings()
    if command == 'seed':
        engine = create_async_engine(settings.database_url)
        sessions = async_sessionmaker(engine,expire_on_commit=False)
        storage = ObjectStorage(settings)
        await storage.initialize()
        folder = Path('/demo-assets')
        if not folder.exists():
            folder = Path(__file__).resolve().parents[2] / 'dist/assets'
        try:
            for key,name in DEMO:
                async def load_photo(key=key):
                    return (folder / (key+'.jpg')).read_bytes()
                async with sessions() as db, db.begin():
                    await create_product(db, storage, title=name,source_key='demo:'+key,load_photo=load_photo)
            print('Демонстрационные товары добавлены. Повторный запуск не создаёт дубли.')
        finally:
            await engine.dispose()
        return
    if not settings.bot_token:
        raise SystemExit('Заполните BOT_TOKEN в локальном .env. Не публикуйте токен.')
    async with Bot(settings.bot_token) as bot:
        if command == 'configure':
            if not settings.public_url or not settings.webhook_secret or not settings.administrators:
                raise SystemExit('Заполните PUBLIC_URL (HTTPS), WEBHOOK_SECRET и ADMIN_IDS в .env.')
            await bot.set_webhook(settings.public_url+'/telegram/webhook',
                secret_token=settings.webhook_secret,allowed_updates=['message','callback_query'],drop_pending_updates=False)
            await bot.set_chat_menu_button(menu_button=MenuButtonWebApp(text='Каталог',web_app=WebAppInfo(url=settings.public_url)))
            await bot.set_my_commands([BotCommand(command='start',description='Открыть каталог')])
            for user in settings.administrators:
                from aiogram.types import BotCommandScopeChat
                await bot.set_my_commands([BotCommand(command='start',description='Открыть каталог'),
                    BotCommand(command='create_product',description='Создать товар')],scope=BotCommandScopeChat(chat_id=user))
            me = await bot.get_me()
            print(f'Настроен @{me.username}. Каталог: {settings.public_url}')
        elif command == 'webhook-info':
            info=await bot.get_webhook_info()
            print(json.dumps({'url':info.url,'pending_updates':info.pending_update_count,
                'last_error':info.last_error_message},ensure_ascii=False,indent=2))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description='Управление каталогом и Telegram')
    parser.add_argument('command',choices=['seed','configure','webhook-info'])
    args=parser.parse_args()
    asyncio.run(run(args.command))
