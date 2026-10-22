import asyncio
import hmac
import logging
import os
from contextlib import asynccontextmanager
from uuid import UUID
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.methods import TelegramMethod
from aiogram.types import Update
from aiogram.utils.serialization import deserialize_telegram_object_to_python
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from minio.error import S3Error
from pydantic import ValidationError
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.bot import create_router
from app.config import Settings
from app.models import Product, ProcessedUpdate
from app.services import lock_key
from app.storage import ObjectStorage

logger = logging.getLogger('catalog')


def create_app(settings=None, *, storage=None, bot=None):
    settings = settings or Settings()
    engine = create_async_engine(settings.database_url, pool_pre_ping=True, pool_size=5, max_overflow=5)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    objects = storage or ObjectStorage(settings)
    telegram = bot
    if telegram is None and settings.bot_token:
        telegram = Bot(settings.bot_token, session=AiohttpSession(timeout=20))
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(create_router())

    @asynccontextmanager
    async def lifespan(app):
        await objects.initialize()
        yield
        await engine.dispose()
        if telegram:
            await telegram.session.close()

    app = FastAPI(title='Каталог', lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.sessions = sessions
    app.state.storage = objects
    app.state.engine = engine

    @app.middleware('http')
    async def response_headers(request, call_next):
        try:
            response = await call_next(request)
        except Exception as error:
            # Catch before ServerErrorMiddleware re-raises to Uvicorn's logger.
            # A Bot API exception may otherwise expose its credential-bearing URL.
            logger.error('Request failed: %s', type(error).__name__)
            response = JSONResponse(status_code=503,content={'detail':'Сервис временно недоступен'})
        response.headers['X-Instance-ID'] = os.getenv('HOSTNAME', 'local')
        if request.url.path == '/api/products':
            response.headers['Cache-Control'] = 'no-store'
        return response

    @app.get('/api/ready')
    async def ready():
        async with sessions() as db:
            await db.execute(text('SELECT 1'))
        if not await objects.ready():
            raise HTTPException(503, 'Хранилище недоступно')
        return {'status': 'ok', 'telegram_configured': bool(telegram and settings.public_url and settings.webhook_secret)}

    @app.get('/api/products')
    async def products():
        async with sessions() as db:
            rows = (await db.scalars(select(Product).order_by(Product.created_at.desc(), Product.id.desc()))).all()
            return [{'id': str(row.id), 'name': row.name,
                     'image_url': f'/api/products/{row.id}/image', 'created_at': row.created_at}
                    for row in rows]

    @app.get('/api/products/{product_id}/image')
    async def image(product_id: UUID):
        async with sessions() as db:
            product = await db.get(Product, product_id)
        if product is None:
            raise HTTPException(404, 'Товар не найден')
        try:
            obj = await asyncio.to_thread(objects.open, product.object_key)
        except S3Error as error:
            if error.code in {'NoSuchKey', 'NoSuchObject'}:
                raise HTTPException(404, 'Фотография не найдена') from error
            raise

        def chunks():
            try:
                yield from obj.stream(64 * 1024)
            finally:
                obj.close()
                obj.release_conn()
        return StreamingResponse(chunks(), media_type=product.content_type,
                                 headers={'Cache-Control': 'public, max-age=3600', 'X-Content-Type-Options': 'nosniff'})

    @app.post('/telegram/webhook')
    async def webhook(request: Request):
        if not telegram or not settings.public_url or not settings.webhook_secret:
            raise HTTPException(503, 'Telegram не настроен')
        supplied = request.headers.get('X-Telegram-Bot-Api-Secret-Token', '')
        if not hmac.compare_digest(supplied, settings.webhook_secret):
            raise HTTPException(403, 'Неверный секрет webhook')
        body = await request.body()
        if len(body) > 1024 * 1024:
            raise HTTPException(413, 'Слишком большой запрос')
        try:
            update = Update.model_validate_json(body, context={'bot': telegram})
        except ValidationError as error:
            raise HTTPException(422, 'Некорректный Telegram update') from error
        async with sessions() as db, db.begin():
            await lock_key(db, f'update:{telegram.id}:{update.update_id}')
            previous = await db.get(ProcessedUpdate, (telegram.id, update.update_id))
            if previous:
                return previous.response
            result = await dispatcher.feed_update(telegram, update, settings=settings, db=db, storage=objects)
            payload = deserialize_telegram_object_to_python(result, default=telegram.default) if isinstance(result, TelegramMethod) else {}
            db.add(ProcessedUpdate(bot_id=telegram.id, update_id=update.update_id, response=payload))
        # SQL commit finishes before returning 2xx and the Bot API reply.
        return payload

    return app


app = create_app()
